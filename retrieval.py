"""Text search used by the Ask, Match and Listing agents.

Default: TF-IDF (fast, no downloads, works offline).
Optional: set USE_EMBEDDINGS=1 and `pip install sentence-transformers` to use
real sentence embeddings instead. Same interface either way.
"""
import os

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_model = None


def _embedder():
    global _model
    if os.environ.get("USE_EMBEDDINGS") != "1":
        return None
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            _model = False
    return _model or None


class Retriever:
    """Index a list of texts once, then find the most similar ones to a query."""

    def __init__(self, texts):
        self.texts = [str(t) for t in texts]
        self.model = _embedder()
        self.method = "embeddings" if self.model else "tf-idf"
        if not self.texts:
            self.matrix = None
            return
        if self.model:
            self.matrix = self.model.encode(self.texts, normalize_embeddings=True)
        else:
            self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True)
            self.matrix = self.vectorizer.fit_transform(self.texts)

    def scores(self, query):
        """Similarity (0 to 1) between the query and every indexed text."""
        if self.matrix is None:
            return np.array([])
        if self.model:
            q = self.model.encode([query], normalize_embeddings=True)
            return (self.matrix @ q.T).ravel()
        q = self.vectorizer.transform([query])
        return cosine_similarity(q, self.matrix).ravel()

    def search(self, query, k=3):
        """Top-k results as a list of (index, score), best first."""
        s = self.scores(query)
        if s.size == 0:
            return []
        order = np.argsort(-s)[:k]
        return [(int(i), float(s[i])) for i in order]
