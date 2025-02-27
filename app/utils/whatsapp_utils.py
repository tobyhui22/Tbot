import logging
from flask import current_app, jsonify
import json
import requests
from rag.query_handler import QueryHandler
import re
from app.services.openai_service import generate_response as openai_generate_response, client
from document_processor.embeddings import EmbeddingGenerator
from app.models.chat_history import ChatHistory
from app.services.classification_service import MessageClassifier
from app.services.reservation_service import ReservationHandler


def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )


def clean_text(text: str) -> str:
    """深度清理和格式化文本"""
    # 移除特殊字符
    text = text.replace("⁠", " ")
    
    # 修復單詞之間的空格
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # 在小寫後面跟大寫的地方加空格
    text = re.sub(r'([a-zA-Z])([0-9])', r'\1 \2', text)  # 在字母後面跟數字的地方加空格
    text = re.sub(r'([0-9])([a-zA-Z])', r'\1 \2', text)  # 在數字後面跟字母的地方加空格
    
    # 修復問答格式
    text = re.sub(r'([0-9]+)\s*Q:', r'\n\nQ:', text)  # 修復問題編號
    text = re.sub(r'Q:', r'\nQ: ', text)  # 確保問題換行
    text = re.sub(r'A:', r'\nA: ', text)  # 確保答案換行
    
    # 修復標點符號周圍的空格
    text = re.sub(r'\s*([,.!?])\s*', r'\1 ', text)
    text = re.sub(r'\s+', ' ', text)  # 移除多餘空格
    
    # 修復常見的單詞
    common_words = ['is', 'are', 'the', 'and', 'in', 'on', 'at', 'to', 'of', 'for', 'with']
    for word in common_words:
        text = re.sub(f'(?<=[a-zA-Z]){word}(?=[a-zA-Z])', f' {word} ', text)
    
    # 修復列表格式
    text = re.sub(r'(?<=[^-])-(?=[a-zA-Z])', r'\n- ', text)
    
    # 修復段落格式
    text = re.sub(r'\n{3,}', '\n\n', text)  # 移除過多的空行
    
    # 特殊處理地址格式
    text = re.sub(r'([0-9]+)([A-Za-z])', r'\1 \2', text)  # 修復地址格式
    
    # 最終清理
    text = text.replace("  ", " ")  # 移除重複空格
    text = text.strip()
    
    # 格式化段落
    paragraphs = text.split('\n\n')
    formatted_paragraphs = []
    for p in paragraphs:
        if p.strip():
            # 如果段落以數字開頭，添加額外的換行
            if re.match(r'^[0-9]', p.strip()):
                formatted_paragraphs.append('\n' + p.strip())
            else:
                formatted_paragraphs.append(p.strip())
    
    return '\n\n'.join(formatted_paragraphs)


def generate_response(message_body, wa_id, name):
    """
    使用 OpenAI 生成回應，並使用 RAG 系統提供上下文
    """
    try:
        # 使用 QueryHandler 獲取相關文檔內容
        query_handler = QueryHandler()
        relevant_docs = query_handler.process_query(message_body)
        
        # 修正：將檢索到的文檔內容正確插入到提示中
        system_content = f"""你是 CookingPapa，一個餐廳接待員。
                
        以下是相關的餐廳資訊，請根據這些資訊回答：
        {relevant_docs}

        身份設定：
        - 名字：CookingPapa
        - 角色：餐廳待應
        - 語言：主要使用粵語回應
        - 性格：友善、專業、有耐性、熱心幫助客人
        """
        
        messages = [
            {
                "role": "system",
                "content": system_content
            },
            {
                "role": "user",
                "content": message_body
            }
        ]
        
        # 使用 OpenAI 生成回應
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logging.error(f"生成回應時出錯: {str(e)}")
        logging.error(f"錯誤類型: {type(e)}")
        logging.error(f"完整錯誤信息: {str(e)}")
        return "唔好意思，我而家暫時回應唔到，請稍後再試。"


def send_message(data):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        response = requests.post(
            url, data=data, headers=headers, timeout=10
        )  # 10 seconds timeout as an example
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except (
        requests.RequestException
    ) as e:  # This will catch any general request exception
        logging.error(f"Request failed due to: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500
    else:
        # Process the response as normal
        log_http_response(response)
        return response


def process_text_for_whatsapp(text: str) -> str:
    """處理文本以適應 WhatsApp 格式"""
    # 確保不超過 WhatsApp 的消息長度限制
    if len(text) > 4096:
        text = text[:4093] + "..."
    
    return text


def process_whatsapp_message(body):
    try:
        # 獲取消息內容
        message = body["entry"][0]["changes"][0]["value"]["messages"][0]
        wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
        user_name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]
        message_body = message["text"]["body"]
        
        # 對訊息進行分類
        classifier = MessageClassifier()
        classification = classifier.classify_message(message_body)
        logging.info(f"訊息分類結果: {classification}")
        
        # 如果是訂枱相關的類別
        if classification.get('category') in ['reservation', 'table_service']:
            logging.info("檢測到訂枱請求，啟動訂枱處理流程")
            reservation_handler = ReservationHandler()
            response, is_complete = reservation_handler.process_reservation_request(
                wa_id, user_name, message_body
            )
            context = "訂枱服務處理"
        else:
            # 使用一般的回應生成流程
            query_handler = QueryHandler()
            context = query_handler.process_query(message_body)
            response = openai_generate_response(message_body, wa_id, user_name)
        
        # 記錄對話
        chat_history = ChatHistory()
        success = chat_history.add_chat_record(
            wa_id=wa_id,
            user_name=user_name,
            message=message_body,
            response=response,
            category=classification.get('category', 'others'),
            context=context,
            metadata={
                "message_id": message.get("id"),
                "timestamp": message.get("timestamp"),
                "classification": classification,
                "is_reservation_complete": is_complete if 'is_complete' in locals() else None
            }
        )
        
        if not success:
            logging.error("對話記錄保存失敗")
            
        logging.info(f"準備發送回應: {response}")
        
        # 發送回應
        data = get_text_message_input(recipient=wa_id, text=response)
        return send_message(data)
        
    except Exception as e:
        logging.error(f"處理 WhatsApp 消息時出錯: {str(e)}")
        return None


def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )
