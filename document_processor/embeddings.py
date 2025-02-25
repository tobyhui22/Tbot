from sentence_transformers import SentenceTransformer
import torch

class EmbeddingGenerator:
    def __init__(self):
        # 檢查是否可用 CUDA
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device=self.device)
    
    def generate_embeddings(self, texts):
        """
        為文本生成嵌入向量
        :param texts: 文本列表
        :return: 嵌入向量列表
        """
        try:
            embeddings = self.model.encode(texts, convert_to_tensor=True)
            return embeddings.cpu().numpy() if self.device == "cuda" else embeddings.numpy()
        except Exception as e:
            print(f"生成嵌入向量時出錯: {str(e)}")
            raise