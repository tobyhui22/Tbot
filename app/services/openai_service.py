from openai import OpenAI
import shelve
from dotenv import load_dotenv
import os
import time
import logging

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")
client = OpenAI(api_key=OPENAI_API_KEY)


def upload_file(path):
    # Upload a file with an "assistants" purpose
    file = client.files.create(
        file=open("../../data/airbnb-faq.pdf", "rb"), purpose="assistants"
    )


def create_assistant(file):
    """
    Create a CookingPapa assistant with specific personality and knowledge.
    """
    assistant = client.beta.assistants.create(
        name="CookingPapa WhatsApp Assistant",
        instructions="""你是 CookingPapa，一個專業的廚藝助手機器人。

        身份設定：
        - 名字：CookingPapa
        - 角色：廚藝助手
        - 語言：主要使用粵語回應
        - 性格：友善、專業、有耐性、熱愛烹飪

        回應準則：
        1. 自稱「我」或「CookingPapa」
        2. 保持友善和專業態度
        3. 專注於提供烹飪相關的建議和幫助
        4. 使用粵語對話

        標準回應：
        - 初次見面：「你好！我係 CookingPapa，您嘅智能廚藝助手！有咩可以幫到你？」
        - 身份詢問：「我係 CookingPapa，專門為大家提供廚藝指導嘅智能助手！」
        - 不懂回答：「唔好意思，呢個問題我可能冇辦法答到，不如問下我煮嘢食嘅問題啦！」
        - 收到讚美：「多謝讚賞！為您提供廚藝支援係我嘅榮幸！」

        專業範疇：
        - 食譜分享和教學
        - 烹飪技巧指導
        - 食材知識解答
        - 廚具使用建議
        - 餐單規劃建議

        如果遇到非廚藝相關問題，應該禮貌地表示這不是專業範圍，並引導用戶詢問烹飪相關問題。""",
        tools=[{"type": "retrieval"}],
        model="gpt-4-1106-preview",
        file_ids=[file.id] if file else []
    )
    return assistant


# Use context manager to ensure the shelf file is closed properly
def check_if_thread_exists(wa_id):
    with shelve.open("threads_db") as threads_shelf:
        return threads_shelf.get(wa_id, None)


def store_thread(wa_id, thread_id):
    with shelve.open("threads_db", writeback=True) as threads_shelf:
        threads_shelf[wa_id] = thread_id


def run_assistant(thread, name):
    try:
        # Retrieve the Assistant
        assistant = client.beta.assistants.retrieve(OPENAI_ASSISTANT_ID)

        # Run the assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id,
        )

        # Wait for completion
        while True:
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if run.status == "completed":
                break
            elif run.status == "failed":
                logging.error(f"Assistant run failed: {run.last_error}")
                return "唔好意思，我暫時回應唔到，請稍後再試。"
            elif run.status == "expired":
                logging.error("Assistant run expired")
                return "唔好意思，回應時間過長，請重新發送你嘅問題。"
            time.sleep(1)

        # Retrieve the Messages
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        if messages.data:
            new_message = messages.data[0].content[0].text.value
            logging.info(f"Generated message: {new_message}")
            return new_message
        else:
            return "唔好意思，我暫時回應唔到，請稍後再試。"
            
    except Exception as e:
        logging.error(f"Error in run_assistant: {str(e)}")
        return "唔好意思，系統發生錯誤，請稍後再試。"


def generate_response(message_body, wa_id, name):
    # Check if there is already a thread_id for the wa_id
    thread_id = check_if_thread_exists(wa_id)

    # If a thread doesn't exist, create one and store it
    if thread_id is None:
        logging.info(f"Creating new thread for {name} with wa_id {wa_id}")
        thread = client.beta.threads.create()
        store_thread(wa_id, thread.id)
        thread_id = thread.id

    # Otherwise, retrieve the existing thread
    else:
        logging.info(f"Retrieving existing thread for {name} with wa_id {wa_id}")
        thread = client.beta.threads.retrieve(thread_id)

    # Add message to thread
    message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message_body,
    )

    # Run the assistant and get the new message
    new_message = run_assistant(thread, name)

    return new_message
