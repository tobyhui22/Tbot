from openai import OpenAI
from dotenv import load_dotenv
import os
import sys

load_dotenv()

def reset_assistant():
    # 檢查 API KEY 是否存在
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("錯誤：未找到 OPENAI_API_KEY 環境變量")
        return None
    
    print("正在初始化 OpenAI 客戶端...")
    client = OpenAI(api_key=api_key)
    
    try:
        # 1. 檢查並刪除現有的 Assistant
        current_assistant_id = os.getenv("OPENAI_ASSISTANT_ID")
        if current_assistant_id:
            try:
                print(f"正在刪除現有的 Assistant (ID: {current_assistant_id})...")
                client.beta.assistants.delete(current_assistant_id)
                print("成功刪除舊的 Assistant")
            except Exception as e:
                print(f"刪除舊 Assistant 時發生錯誤: {str(e)}")
        else:
            print("未找到現有的 Assistant ID")
        
        # 2. 創建新的 Assistant
        print("正在創建新的 Assistant...")
        new_assistant = client.beta.assistants.create(
            name="CookingPapa WhatsApp Assistant",
            instructions="""你是 CookingPapa，一個餐廳待應機器人。

            身份設定：
            - 名字：CookingPapa
            - 角色：餐廳待應
            - 語言：主要使用粵語回應
            - 性格：友善、專業、有耐性、熱心幫助客人

            回應準則：
            1. 自稱「我」或「CookingPapa」
            2. 保持友善和專業態度
            3. 專注於提供餐廳相關的建議和幫助
            4. 使用粵語對話

            標準回應：
            - 初次見面：「你好！我係 CookingPapa，您嘅餐廳待應！有咩可以幫到你？」
            - 身份詢問：「我係 CookingPapa，專門為大家提供餐廳服務！」
            - 不懂回答：「唔好意思，呢個問題我可能冇辦法答到，不如問下我餐廳嘅問題啦！」
            - 收到讚美：「多謝讚賞！為您提供廚藝支援係我嘅榮幸！」

            專業範疇：
            - 餐廳服務
            - 餐廳訂座
            - 餐廳查詢
            - 餐廳推薦
            - 餐廳訂座

            如果遇到非餐廳相關問題，應該禮貌地表示這不是專業範圍，並引導用戶詢問餐廳相關問題。""",
            tools=[{"type": "code_interpreter"}, {"type": "file_search"}],
            model="gpt-4-1106-preview"
        )
        
        print("\n=== Assistant 創建成功 ===")
        print(f"新的 Assistant ID: {new_assistant.id}")
        print("\n請將以下內容更新到 .env 文件：")
        print(f"OPENAI_ASSISTANT_ID={new_assistant.id}")
        
        return new_assistant.id
        
    except Exception as e:
        print(f"發生錯誤: {str(e)}")
        print(f"錯誤類型: {type(e).__name__}")
        return None

if __name__ == "__main__":
    print("開始執行 Assistant 重置程序...")
    result = reset_assistant()
    if result:
        print("程序執行成功！")
    else:
        print("程序執行失敗！")
        sys.exit(1)