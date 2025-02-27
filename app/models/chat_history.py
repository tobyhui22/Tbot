from datetime import datetime
import sqlite3
import logging
from typing import Optional, Dict, Any
import os
import json
import time
from contextlib import contextmanager

class ChatHistory:
    def __init__(self, db_path="db/chat_history.db"):
        """初始化 ChatHistory 類
        Args:
            db_path (str): 數據庫文件路徑，默認為 'db/chat_history.db'
        """
        self.db_path = db_path
        self.timeout = 20
        self.max_retries = 3
        logging.info(f"初始化 ChatHistory，使用數據庫路徑: {self.db_path}")

    @contextmanager
    def get_db_connection(self):
        """創建數據庫連接的上下文管理器"""
        retries = 0
        while retries < self.max_retries:
            try:
                conn = sqlite3.connect(self.db_path, timeout=self.timeout)
                conn.execute('PRAGMA journal_mode=WAL')
                conn.execute('PRAGMA busy_timeout=5000')
                yield conn
                conn.close()
                break
            except sqlite3.OperationalError as e:
                retries += 1
                if retries == self.max_retries:
                    raise e
                time.sleep(1)
            except Exception as e:
                raise e

    def init_db(self):
        """初始化數據庫表"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                # 創建用戶表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    wa_id TEXT PRIMARY KEY,
                    name TEXT,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    conversation_count INTEGER DEFAULT 0
                )
                ''')
                
                # 創建消息分類表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS message_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT
                )
                ''')
                
                # 創建對話歷史表（確保不會被重寫）
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wa_id TEXT NOT NULL,
                    user_name TEXT,
                    message TEXT,
                    response TEXT,
                    category_id INTEGER,
                    context TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES message_categories(id),
                    FOREIGN KEY (wa_id) REFERENCES users(wa_id)
                )
                ''')
                
                # 創建訂位表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS table_reservations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wa_id TEXT NOT NULL,
                    user_name TEXT,
                    reservation_date DATE NOT NULL,
                    reservation_time TIME NOT NULL,
                    number_of_people INTEGER NOT NULL,
                    special_requests TEXT,
                    status TEXT NOT NULL DEFAULT '待確認',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (wa_id) REFERENCES users(wa_id)
                )
                ''')
                
                # 創建人工支援請求表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS human_support_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wa_id TEXT NOT NULL,
                    user_name TEXT,
                    request_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP,
                    resolved_by TEXT,
                    notes TEXT,
                    FOREIGN KEY (wa_id) REFERENCES users(wa_id)
                )
                ''')
                
                # 插入預設分類
                cursor.execute('''
                INSERT OR IGNORE INTO message_categories (name, description) VALUES 
                    ('restaurant_info', '餐廳資料詢問'),
                    ('food_info', '食物資料詢問'),
                    ('reservation', '訂位相關'),
                    ('service', '其他服務'),
                    ('others', '其他查詢')
                ''')
                
                conn.commit()
                logging.info("數據庫表格初始化成功")
                return True
                
        except Exception as e:
            logging.error(f"初始化數據庫時出錯: {str(e)}")
            return False

    def add_chat_record(self, wa_id: str, user_name: str, message: str, response: str, 
                        category: str = None, context: str = None, metadata: dict = None) -> bool:
        """添加新的對話記錄"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                # 確保用戶存在
                cursor.execute('''
                INSERT OR IGNORE INTO users (wa_id, name, conversation_count)
                VALUES (?, ?, 0)
                ''', (wa_id, user_name))
                
                # 更新用戶信息
                cursor.execute('''
                UPDATE users 
                SET last_seen = CURRENT_TIMESTAMP,
                    conversation_count = conversation_count + 1,
                    name = COALESCE(NULLIF(?, ''), name)
                WHERE wa_id = ?
                ''', (user_name, wa_id))
                
                # 獲取分類ID
                category_id = None
                if category:
                    cursor.execute('SELECT id FROM message_categories WHERE name = ?', (category,))
                    result = cursor.fetchone()
                    category_id = result[0] if result else None
                
                # 插入新的對話記錄（使用 INSERT，確保是追加）
                cursor.execute('''
                INSERT INTO chat_history 
                (wa_id, user_name, message, response, category_id, context, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    wa_id, 
                    user_name, 
                    message, 
                    response, 
                    category_id, 
                    context, 
                    json.dumps(metadata) if metadata else None
                ))
                
                # 獲取新插入記錄的ID
                new_record_id = cursor.lastrowid
                
                conn.commit()
                logging.info(f"成功添加新對話記錄 ID: {new_record_id} 用戶: {wa_id}")
                return True
                
        except Exception as e:
            logging.error(f"添加對話記錄時出錯: {str(e)}")
            return False

    def get_user_history(self, wa_id: str, limit: int = 10) -> list:
        """獲取用戶的對話歷史"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT message, response, created_at 
                FROM chat_history 
                WHERE wa_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
                ''', (wa_id, limit))
                return cursor.fetchall()
        except Exception as e:
            logging.error(f"獲取用戶歷史記錄時出錯: {str(e)}")
            return []

    def get_recent_chat_history(self, wa_id: str, hours: int = 1) -> list:
        """獲取用戶最近幾小時內的對話歷史"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                # 首先驗證 wa_id 是否存在
                cursor.execute('SELECT wa_id FROM users WHERE wa_id = ?', (wa_id,))
                if not cursor.fetchone():
                    logging.info(f"找不到用戶記錄: {wa_id}")
                    return []
                
                # 獲取指定用戶的最近對話記錄
                cursor.execute('''
                SELECT 
                    ch.message,
                    ch.response,
                    ch.created_at,
                    ch.category_id,
                    mc.name as category_name,
                    1 as is_user
                FROM chat_history ch
                LEFT JOIN message_categories mc ON ch.category_id = mc.id
                WHERE ch.wa_id = ?  -- 嚴格匹配 WhatsApp ID
                AND ch.created_at >= datetime('now', ?)
                AND ch.message IS NOT NULL
                ORDER BY ch.created_at ASC
                ''', (wa_id, f'-{hours} hours'))
                
                history = []
                for msg, resp, timestamp, cat_id, cat_name, is_user in cursor.fetchall():
                    if msg and msg.strip():
                        history.append({
                            "content": msg,
                            "is_user": True,
                            "timestamp": timestamp,
                            "category": cat_name,
                            "wa_id": wa_id  # 添加 WhatsApp ID 以便追踪
                        })
                    if resp and resp.strip():
                        history.append({
                            "content": resp,
                            "is_user": False,
                            "timestamp": timestamp,
                            "category": cat_name,
                            "wa_id": wa_id
                        })
                
                # 記錄詳細日誌
                logging.info(f"用戶 {wa_id} 的最近 {hours} 小時對話記錄：{len(history)} 條")
                for item in history:
                    logging.debug(
                        f"歷史記錄 - "
                        f"用戶ID: {item['wa_id']}, "
                        f"類型: {'用戶' if item['is_user'] else '機器人'}, "
                        f"分類: {item.get('category', 'N/A')}, "
                        f"時間: {item['timestamp']}, "
                        f"內容: {item['content'][:50]}..."
                    )
                
                return history
                
        except Exception as e:
            logging.error(f"獲取用戶 {wa_id} 的對話歷史時出錯: {str(e)}")
            return []

    def add_human_support_request(self, wa_id: str, user_name: str, request_type: str, message: str) -> bool:
        """記錄需要人工客服處理的請求"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                # 添加請求記錄
                cursor.execute('''
                INSERT INTO human_support_requests 
                (wa_id, user_name, request_type, message)
                VALUES (?, ?, ?, ?)
                ''', (wa_id, user_name, request_type, message))
                
                conn.commit()
                return True
                
        except Exception as e:
            logging.error(f"添加人工客服請求時出錯: {str(e)}")
            return False

    def add_reservation(self, 
                       wa_id: str,
                       user_name: str,
                       reservation_date: str,
                       reservation_time: str,
                       number_of_people: int,
                       special_requests: str = None) -> bool:
        """添加新的訂枱記錄（移除 table_type 參數）"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                # 添加訂位記錄（移除 table_type）
                cursor.execute('''
                INSERT INTO table_reservations 
                (wa_id, user_name, reservation_date, reservation_time, 
                 number_of_people, special_requests)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (wa_id, user_name, reservation_date, reservation_time, 
                     number_of_people, special_requests))
                
                conn.commit()
                return True
                
        except Exception as e:
            logging.error(f"添加訂位記錄時出錯: {str(e)}")
            return False

    def get_reservations_by_date(self, date: str) -> list:
        """獲取指定日期的所有訂位"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT 
                    id,
                    wa_id,
                    user_name,
                    reservation_time,
                    number_of_people,
                    special_requests,
                    status
                FROM table_reservations 
                WHERE reservation_date = ?
                ORDER BY reservation_time
                ''', (date,))
                return cursor.fetchall()
        except Exception as e:
            logging.error(f"獲取訂位記錄時出錯: {str(e)}")
            return []

    def update_reservation_status(self, reservation_id: int, status: str) -> bool:
        """更新訂位狀態"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                UPDATE table_reservations 
                SET status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                ''', (status, reservation_id))
                
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"更新訂位狀態時出錯: {str(e)}")
            return False