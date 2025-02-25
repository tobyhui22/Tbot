from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

class DocumentProcessor:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
    def load_pdf(self, pdf_path):
        loader = PyPDFLoader(pdf_path)
        pages = loader.load()
        return self.text_splitter.split_documents(pages) 