import chromadb
import os
from dotenv import load_dotenv

class VectorStore:
    def __init__(self):
        load_dotenv()
        vector_db_path = os.getenv('VECTOR_DB_PATH', './vector_db')
        
        # 使用新的客戶端配置方式
        self.client = chromadb.PersistentClient(path=vector_db_path)
    
    def store_embeddings(self, collection_name, documents, embeddings):
        """
        存儲文檔和對應的嵌入向量
        """
        # 獲取或創建集合
        collection = self.client.get_or_create_collection(name=collection_name)
        
        # 準備數據
        ids = [str(i) for i in range(len(documents))]
        texts = [doc.page_content for doc in documents]
        
        # 添加數據到集合
        collection.add(
            documents=texts,
            embeddings=embeddings,
            ids=ids
        )
        
    def search(self, query_embedding, k=3):
        """
        搜索最相似的文檔
        """
        collection = self.client.get_collection("airbnb_faq")
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=k
        )
        return results