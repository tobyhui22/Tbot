import os
from dotenv import load_dotenv
from rag.document_processor import DocumentProcessor
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_vector_database():
    # 加載環境變量
    load_dotenv()
    
    try:
        # 初始化文檔處理器
        doc_processor = DocumentProcessor()
        
        # 獲取PDF路徑
        pdf_path = os.getenv('PDF_SOURCE_PATH')
        if not pdf_path:
            logger.error("PDF_SOURCE_PATH 未在 .env 中設置")
            return
            
        logger.info(f"開始處理PDF文件: {pdf_path}")
        
        # 提取文本
        paragraphs = doc_processor.extract_text_from_pdf(pdf_path)
        if not paragraphs:
            logger.error("無法從PDF中提取文本")
            return
            
        logger.info(f"成功提取 {len(paragraphs)} 個段落")
        
        # 創建向量數據庫
        success = doc_processor.create_or_update_collection(
            collection_name="restaurant_info",
            documents=paragraphs
        )
        
        if success:
            logger.info("向量數據庫創建成功")
        else:
            logger.error("向量數據庫創建失敗")
        
    except Exception as e:
        logger.error(f"初始化過程出錯: {str(e)}")
        raise

if __name__ == "__main__":
    init_vector_database() 