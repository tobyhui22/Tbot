from openai import OpenAI
import json
import os
from typing import Dict, Any
import logging

class MessageClassifier:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
    def classify_message(self, message: str) -> Dict[str, Any]:
        """使用 OpenAI 對訊息進行分類"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-1106-preview",
                response_format={ "type": "json_object" },
                messages=[
                    {
                        "role": "system",
                        "content": """你是一個專門分類餐廳客服對話的AI。
                        請將用戶訊息分類為以下類別之一：
                        - restaurant_info: 餐廳資料詢問（如：營業時間、地址、環境等）
                        - food_info: 食物資料詢問（如：菜單、食材、價格等）
                        - reservation: 訂位相關（如：訂位、更改訂位、取消訂位等）
                        - service: 其他服務（如：外賣、包場、特別要求等）
                        - others: 其他查詢
                        
                        請返回 JSON 格式，包含：
                        - category: 分類名稱
                        - confidence: 信心指數（0-1）
                        - reason: 分類原因
                        """
                    },
                    {
                        "role": "user",
                        "content": message
                    }
                ]
            )
            
            # 解析回應
            result = json.loads(response.choices[0].message.content)
            logging.info(f"訊息分類結果: {result}")
            return result
            
        except Exception as e:
            logging.error(f"訊息分類出錯: {str(e)}")
            return {
                "category": "others",
                "confidence": 0,
                "reason": "分類過程出錯"
            } 