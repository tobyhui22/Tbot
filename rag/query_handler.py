from sentence_transformers import SentenceTransformer
import chromadb
import os
from dotenv import load_dotenv

class QueryHandler:
    def __init__(self):
        load_dotenv()
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.client = chromadb.PersistentClient(path=os.getenv('VECTOR_DB_PATH'))
        self.collection = self.client.get_collection("airbnb_faq")
    
    def process_query(self, query_text, k=3):
        """
        處理用戶查詢
        :param query_text: 用戶的問題
        :param k: 返回的相關文檔數量
        :return: 相關回答
        """
        try:
            # 生成查詢的嵌入向量
            query_embedding = self.model.encode(query_text)
            
            # 搜索相關文檔
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=k
            )
            
            # 格式化回應
            response = "根據文檔，以下是相關信息：\n\n"
            for i, doc in enumerate(results['documents'][0], 1):
                response += f"{i}. {doc}\n\n"
            
            return response
            
        except Exception as e:
            print(f"查詢處理出錯: {str(e)}")
            return "抱歉，處理您的問題時出現錯誤。" 