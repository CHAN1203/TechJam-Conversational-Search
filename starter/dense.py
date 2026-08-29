from __future__ import annotations

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer


class DenseIndex:
    """Latent Semantic Analysis (TF-IDF + Truncated SVD) over a fixed
    document collection, built once. Not a neural embedding: it captures
    term co-occurrence structure, a weaker but far cheaper approximation of
    "closeness in meaning" than a pretrained sentence model, with no
    downloaded weights and no per-query model inference.
    """

    def __init__(
        self,
        parent_asins: list[str],
        texts: list[str],
        n_components: int = 200,
        max_features: int = 20000,
    ) -> None:
        self.parent_asins = parent_asins
        self._vectorizer = TfidfVectorizer(max_features=max_features, stop_words="english")
        tfidf = self._vectorizer.fit_transform(texts)
        # n_components must stay below both the vocabulary size and the
        # document count for TruncatedSVD to be solvable at all -- matters
        # for small test fixtures, never for the real 50,000-item catalog.
        safe_components = max(1, min(n_components, tfidf.shape[1] - 1, len(texts) - 1))
        self._svd = TruncatedSVD(n_components=safe_components, random_state=0)
        doc_vectors = self._svd.fit_transform(tfidf)
        self._doc_vectors = self._normalize(doc_vectors)

    @staticmethod
    def _normalize(vectors: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        return vectors / norms

    def search(self, query_text: str, top_k: int) -> list[str]:
        if not query_text.strip():
            return []
        query_tfidf = self._vectorizer.transform([query_text])
        query_vector = self._svd.transform(query_tfidf)[0]
        norm = np.linalg.norm(query_vector)
        if norm == 0.0:
            return []
        query_vector = query_vector / norm
        scores = self._doc_vectors @ query_vector
        top_indices = np.argsort(-scores)[:top_k]
        return [self.parent_asins[i] for i in top_indices]
