"""Geração de embeddings com sentence-transformers."""
from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: list[str], batch_size: int = 32, show_progress: bool = True):
        return self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
        )

    @property
    def dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()
