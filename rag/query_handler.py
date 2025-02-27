import chromadb
from chromadb.utils import embedding_functions
import os
from dotenv import load_dotenv
import logging

class QueryHandler:
    def __init__(self):
        load_dotenv()
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name='sentence-transformers/all-MiniLM-L6-v2'
        )
        self.client = chromadb.PersistentClient(path=os.getenv('VECTOR_DB_PATH'))
        self.collection = self.client.get_collection(
            name="restaurant_info",
            embedding_function=self.embedding_function
        )
    
    def process_query(self, query_text: str, k: int = 3) -> str:
        """
        處理用戶查詢
        :param query_text: 用戶的問題
        :param k: 返回的相關文檔數量
        :return: 相關回答
        """
        try:
            # 搜索相關文檔
            results = self.collection.query(
                query_texts=[query_text],
                n_results=k
            )
            
            if not results['documents'][0]:
                return "沒有找到相關資訊。"
            
            return "\n\n".join(results['documents'][0])
            
        except Exception as e:
            logging.error(f"查詢處理出錯: {str(e)}")
            return "抱歉，處理您的問題時出現錯誤。" 