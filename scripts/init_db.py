import sys
import os
import logging
from dotenv import load_dotenv

# 添加項目根目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.chat_history import ChatHistory

def init_database():
    load_dotenv()
    
    try:
        # 設置數據庫路徑
        db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'db',
            'chat_history.db'
        )
        
        # 確保數據庫目錄存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # 設置環境變量
        os.environ['DB_PATH'] = db_path
        
        # 初始化 ChatHistory 類
        logging.info(f"正在初始化數據庫: {db_path}")
        chat_history = ChatHistory(db_path=db_path)
        
        # 初始化數據庫表
        chat_history.init_db()
        
        # 添加測試數據
        chat_history.add_chat_record(
            wa_id="test_user",
            user_name="測試用戶",
            message="你好",
            response="你好！我是 CookingPapa！",
            category="others",
            context="測試上下文",
            metadata={"test": True}
        )
        
        logging.info("數據庫初始化成功！")
        return True
        
    except Exception as e:
        logging.error(f"數據庫初始化失敗: {str(e)}")
        return False

if __name__ == "__main__":
    # 設置日誌
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 執行初始化
    success = init_database()
    if success:
        print("✅ 數據庫初始化完成")
        
        # 驗證數據庫是否正確創建
        db_path = os.environ.get('DB_PATH')
        if os.path.exists(db_path):
            print(f"✅ 數據庫文件已創建: {db_path}")
            
            # 測試讀取數據
            chat_history = ChatHistory(db_path=db_path)
            results = chat_history.get_user_history("test_user")
            if results:
                print("\n測試數據:")
                for msg, resp, timestamp in results:
                    print(f"時間: {timestamp}")
                    print(f"用戶: {msg}")
                    print(f"機器人: {resp}")
                    print("-" * 50)
        else:
            print(f"❌ 數據庫文件未找到: {db_path}")
    else:
        print("❌ 數據庫初始化失敗")