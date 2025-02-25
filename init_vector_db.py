import os
from dotenv import load_dotenv
from document_processor.pdf_loader import DocumentProcessor
from document_processor.embeddings import EmbeddingGenerator
from vector_store.chroma_db import VectorStore
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_vector_database():
    # 加載環境變量
    load_dotenv()
    
    try:
        # 初始化處理器
        doc_processor = DocumentProcessor()
        embedding_gen = EmbeddingGenerator()
        vector_store = VectorStore()
        
        # 獲取PDF路徑
        pdf_path = os.getenv('PDF_SOURCE_PATH')
        
        logger.info(f"開始處理PDF文件: {pdf_path}")
        
        # 加載和分割文檔
        documents = doc_processor.load_pdf(pdf_path)
        logger.info(f"文檔分割完成，共 {len(documents)} 個片段")
        
        # 生成嵌入
        texts = [doc.page_content for doc in documents]
        embeddings = embedding_gen.generate_embeddings(texts)
        logger.info("嵌入向量生成完成")
        
        # 存儲到向量數據庫
        vector_store.store_embeddings(
            collection_name="airbnb_faq",
            documents=documents,
            embeddings=embeddings
        )
        logger.info("向量數據庫創建成功")
        
    except Exception as e:
        logger.error(f"初始化過程出錯: {str(e)}")
        raise

if __name__ == "__main__":
    init_vector_database() 