from document_processor.pdf_loader import DocumentProcessor
from document_processor.embeddings import EmbeddingGenerator
from vector_store.chroma_db import VectorStore
from rag.retriever import RAGRetriever
from rag.query_handler import QueryHandler

class WebhookHandler:
    def __init__(self):
        self.doc_processor = DocumentProcessor()
        self.embedding_gen = EmbeddingGenerator()
        self.vector_store = VectorStore()
        self.rag = RAGRetriever(self.vector_store)
        self.query_handler = QueryHandler()
    
    def handle_message(self, message_text):
        """
        處理接收到的WhatsApp消息
        """
        try:
            # 使用RAG處理查詢
            response = self.query_handler.process_query(message_text)
            return response
        except Exception as e:
            print(f"消息處理出錯: {str(e)}")
            return "抱歉，我現在無法回答這個問題。"

    def process_message(self, message):
        # 使用RAG處理用戶查詢
        relevant_docs = self.rag.retrieve(message)
        # 生成回應 