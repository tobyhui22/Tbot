import pdfplumber
import os
from typing import List
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
import logging

class DocumentProcessor:
    def __init__(self):
        load_dotenv()
        # 使用 ChromaDB 的內建 embedding 函數
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name='sentence-transformers/all-MiniLM-L6-v2'
        )
        self.client = chromadb.PersistentClient(path=os.getenv('VECTOR_DB_PATH'))
        
        # 獲取或創建集合
        try:
            self.collection = self.client.get_or_create_collection(
                name="restaurant_info",
                embedding_function=self.embedding_function
            )
        except Exception as e:
            logging.error(f"創建集合時出錯: {str(e)}")
            raise
    
    def extract_text_from_pdf(self, pdf_path: str) -> List[str]:
        """
        從PDF文件中提取文本，並按段落分割
        """
        try:
            paragraphs = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        # 按段落分割文本
                        page_paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
                        paragraphs.extend(page_paragraphs)
            return paragraphs
        except Exception as e:
            logging.error(f"PDF處理錯誤: {str(e)}")
            return []

    def create_or_update_collection(self, collection_name: str, documents: List[str]) -> bool:
        """
        創建或更新向量數據庫集合
        """
        try:
            # 刪除現有集合（如果存在）
            try:
                self.client.delete_collection(collection_name)
            except:
                pass

            # 創建新集合
            collection = self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )

            # 添加文檔到集合
            collection.add(
                documents=documents,
                ids=[f"doc_{i}" for i in range(len(documents))]
            )
            
            logging.info(f"成功創建集合 {collection_name} 包含 {len(documents)} 個文檔")
            return True
            
        except Exception as e:
            logging.error(f"創建集合時出錯: {str(e)}")
            return False

    def query_documents(self, query_text, n_results=3):
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            return results
        except Exception as e:
            logging.error(f"查詢文檔時出錯: {str(e)}")
            return None