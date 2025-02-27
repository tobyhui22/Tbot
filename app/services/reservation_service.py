from openai import OpenAI
import json
import os
from datetime import datetime, time
import logging
from app.models.chat_history import ChatHistory
from typing import Tuple

class ReservationHandler:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.chat_history = ChatHistory()
        self.MAX_RETRIES = 2
        
        # 定義營業時間
        self.BUSINESS_HOURS = {
            'lunch': {'start': time(11, 30), 'end': time(15, 00)},
            'dinner': {'start': time(18, 00), 'end': time(22, 00)}
        }
        self.MAX_PARTY_SIZE = 8
        self.MAX_CONCURRENT_BOOKINGS = 3

    def extract_reservation_info(self, message: str, conversation_history: list = None) -> dict:
        """使用 OpenAI 提取訂枱相關信息"""
        try:
            # 檢查是否是對特別要求的回應
            if conversation_history and message.strip() in ['無', '没有', '不用', '不需要']:
                # 檢查上一條消息是否是關於特別要求的詢問
                last_bot_message = next(
                    (msg['content'] for msg in reversed(conversation_history) 
                     if not msg['is_user'] and '特別要求' in msg['content']),
                    None
                )
                
                if last_bot_message:
                    logging.info("檢測到對特別要求的否定回應")
                    # 從歷史記錄中提取已有信息
                    existing_info = self._extract_from_history(conversation_history)
                    return {
                        "has_complete_info": True,
                        "needs_human": False,
                        "extracted_info": {
                            **existing_info,
                            "special_requests": None  # 明確設置為無特別要求
                        },
                        "missing_info": [],
                        "follow_up_question": None,
                        "previous_info": {
                            "found": True,
                            "items": list(existing_info.keys())
                        }
                    }

            messages = [
                {
                    "role": "system",
                    "content": """你是一個專門處理餐廳訂位的AI助手。
                    請從用戶訊息和對話歷史中提取訂位相關信息，並返回 JSON 格式的回應。
                    
                    特別注意：
                    1. 當用戶回答「無」、「没有」、「不用」等否定詞時，如果是回應特別要求的提問，
                       應該將其理解為「無特別要求」而不是無法理解的回應。
                    2. 要考慮對話上下文，特別是之前的問題。
                    
                    需要提取的信息並以 JSON 格式返回：
                    {
                        "has_complete_info": false,
                        "needs_human": false,
                        "extracted_info": {
                            "reservation_date": "YYYY-MM-DD",
                            "reservation_time": "HH:MM",
                            "number_of_people": 0,
                            "special_requests": null
                        },
                        "missing_info": ["缺少的信息項目"],
                        "follow_up_question": "追問問題",
                        "previous_info": {
                            "found": false,
                            "items": []
                        }
                    }
                    """
                }
            ]

            # 添加對話歷史
            if conversation_history:
                history_context = "對話歷史：\n"
                for msg in conversation_history:
                    role = "用戶" if msg["is_user"] else "助手"
                    history_context += f"{role}: {msg['content']}\n"
                messages.append({
                    "role": "system",
                    "content": history_context
                })

            messages.append({
                "role": "user",
                "content": f"當前用戶訊息: {message}"
            })

            response = self.client.chat.completions.create(
                model="gpt-4-1106-preview",
                response_format={ "type": "json_object" },
                messages=messages,
                temperature=0.7  # 增加一些靈活性
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # 記錄處理結果
            logging.info(f"訂位信息提取結果（包含歷史）: {result}")
            if result.get("previous_info", {}).get("found"):
                logging.info(f"從歷史中找到的信息: {result['previous_info']['items']}")
            
            return result
            
        except Exception as e:
            logging.error(f"提取訂位信息時出錯: {str(e)}")
            return {
                "has_complete_info": False,
                "needs_human": True,
                "follow_up_question": "我處理緊你嘅訂位請求，請稍後，我們將儘快有專人聯絡你。",
                "extracted_info": {},
                "previous_info": {"found": False, "items": []}
            }

    def _extract_from_history(self, conversation_history: list) -> dict:
        """從對話歷史中提取已確認的訂位信息"""
        info = {}
        for msg in conversation_history:
            if not msg['is_user'] and '已收到您的訂位請求' in msg['content']:
                # 從確認消息中提取信息
                lines = msg['content'].split('\n')
                for line in lines:
                    if '日期：' in line:
                        info['reservation_date'] = line.split('：')[1].strip()
                    elif '時間：' in line:
                        info['reservation_time'] = line.split('：')[1].strip()
                    elif '人數：' in line:
                        info['number_of_people'] = int(line.split('：')[1].replace('人', '').strip())
                break
        return info

    def validate_reservation(self, date: str, time_str: str, party_size: int) -> Tuple[bool, str]:
        """驗證訂位請求是否符合規則"""
        try:
            # 解析時間
            booking_time = datetime.strptime(time_str, '%H:%M').time()
            
            # 檢查營業時間
            is_business_hours = False
            for period, hours in self.BUSINESS_HOURS.items():
                if hours['start'] <= booking_time <= hours['end']:
                    is_business_hours = True
                    break
            
            if not is_business_hours:
                return False, (
                    "非常抱歉，您選擇的時間不在我們的營業時間內。\n"
                    "我們的營業時間是：\n"
                    "午市：11:30-15:00\n"
                    "晚市：18:00-22:00\n"
                    "請選擇其他時間，或需要我為您安排其他時段嗎？"
                )
            
            # 檢查人數限制
            if party_size > self.MAX_PARTY_SIZE:
                return False, (
                    f"非常抱歉，{party_size}人的訂位需要特別安排。"
                    "為了better服務您，我們的客服人員會盡快與您聯繫確認細節。"
                )
            
            # 檢查同時段訂位數量
            time_slot_start = datetime.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M")
            concurrent_bookings = self._check_concurrent_bookings(date, time_str)
            
            if concurrent_bookings >= self.MAX_CONCURRENT_BOOKINGS:
                return False, (
                    "非常抱歉，您選擇的時段訂位較多。"
                    "為了確保為您提供最好的服務，"
                    "我們的客服人員會盡快與您聯繫確認可行的安排。"
                )
            
            return True, "驗證通過"
            
        except Exception as e:
            logging.error(f"驗證訂位時出錯: {str(e)}")
            return False, "驗證訂位時出現錯誤，請稍後再試"

    def _check_concurrent_bookings(self, date: str, time_str: str) -> int:
        """檢查指定時段的訂位數量"""
        try:
            # 獲取指定時間前後30分鐘的訂位
            booking_time = datetime.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M")
            
            with self.chat_history.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT COUNT(*) 
                FROM table_reservations 
                WHERE reservation_date = ? 
                AND ABS(strftime('%s', reservation_time) - strftime('%s', ?)) < 1800
                AND status != '已取消'
                ''', (date, time_str))
                
                return cursor.fetchone()[0]
                
        except Exception as e:
            logging.error(f"檢查同時段訂位時出錯: {str(e)}")
            return 0

    def process_reservation_request(self, wa_id: str, user_name: str, message: str, retry_count: int = 0) -> tuple:
        """處理訂位請求"""
        try:
            conversation_history = self.chat_history.get_recent_chat_history(wa_id, hours=1)
            reservation_info = self.extract_reservation_info(message, conversation_history)
            
            if reservation_info["has_complete_info"]:
                info = reservation_info["extracted_info"]
                
                # 驗證訂位
                is_valid, validation_message = self.validate_reservation(
                    info["reservation_date"],
                    info["reservation_time"],
                    info["number_of_people"]
                )
                
                if not is_valid:
                    # 如果是人數超限或同時段訂位過多，添加人工支援請求
                    if "客服人員會盡快與您聯繫" in validation_message:
                        self.chat_history.add_human_support_request(
                            wa_id=wa_id,
                            user_name=user_name,
                            request_type="reservation_special",
                            message=f"特殊訂位請求 - 日期：{info['reservation_date']}, "
                                   f"時間：{info['reservation_time']}, "
                                   f"人數：{info['number_of_people']}"
                        )
                    return validation_message, False
                
                # 如果驗證通過，繼續處理訂位
                success = self.chat_history.add_reservation(
                    wa_id=wa_id,
                    user_name=user_name,
                    reservation_date=info["reservation_date"],
                    reservation_time=info["reservation_time"],
                    number_of_people=info["number_of_people"],
                    special_requests=info.get("special_requests")
                )
                
                if success:
                    response = (
                        f"好的，已收到您的訂位請求：\n"
                        f"日期：{info['reservation_date']}\n"
                        f"時間：{info['reservation_time']}\n"
                        f"人數：{info['number_of_people']}人\n"
                        f"特別要求：{info.get('special_requests', '無')}\n\n"
                        f"我們會盡快確認訂位，請稍候。"
                    )
                else:
                    response = "抱歉，保存訂位記錄時出現錯誤，請稍後再試。"
            else:
                response = reservation_info["follow_up_question"]
            
            return response, reservation_info["has_complete_info"]
            
        except Exception as e:
            logging.error(f"處理訂位請求時出錯: {str(e)}")
            return "抱歉，處理訂位時出現錯誤，請稍後再試。", False

    def check_reservation_status(self, wa_id: str) -> str:
        """查詢用戶的訂位狀態"""
        reservations = self.chat_history.get_user_reservations(wa_id)
        
        if not reservations:
            return "您目前沒有任何訂位記錄。"
            
        response = "您的訂位記錄：\n\n"
        for res in reservations:
            date, time, people, table, status, requests, created = res
            response += (
                f"日期：{date}\n"
                f"時間：{time}\n"
                f"人數：{people}人\n"
                f"狀態：{status}\n"
                f"特別要求：{requests or '無'}\n"
                f"訂位時間：{created}\n"
                f"{'=' * 20}\n"
            )
        
        return response