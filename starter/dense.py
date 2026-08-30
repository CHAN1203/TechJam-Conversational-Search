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
        # An empty collection (some tests use a trivial catalog fixture
        # that only exercises conversation-state logic, not retrieval) has
        # no vocabulary to fit at all -- degrade to a no-op index rather
        # than let TfidfVectorizer raise, same principle as
        # `_load_gazetteer`'s "the scored path must never fail because a
        # derived asset is degenerate."
        self._empty = not texts
        if self._empty:
            self._vectorizer = None
            self._svd = None
            self._doc_vectors = None
            self._index_by_asin: dict[str, int] = {}
            return
        self._vectorizer = TfidfVectorizer(max_features=max_features, stop_words="english")
        tfidf = self._vectorizer.fit_transform(texts)
        # n_components must stay below both the vocabulary size and the
        # document count for TruncatedSVD to be solvable at all -- matters
        # for small test fixtures, never for the real 50,000-item catalog.
        safe_components = max(1, min(n_components, tfidf.shape[1] - 1, len(texts) - 1))
        self._svd = TruncatedSVD(n_components=safe_components, random_state=0)
        doc_vectors = self._svd.fit_transform(tfidf)
        self._doc_vectors = self._normalize(doc_vectors)
        self._index_by_asin = {asin: i for i, asin in enumerate(parent_asins)}

    @staticmethod
    def _normalize(vectors: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        return vectors / norms

    def project(self, query_text: str) -> np.ndarray | None:
        """Project text into the fitted vector space, L2-normalized so a
        dot product with another normalized vector is cosine similarity.
        `None` when there is nothing meaningful to project (empty text, or
        zero overlap with the fitted vocabulary) -- the caller decides what
        "no signal" means for its purpose, rather than this guessing.
        """
        if self._empty or not query_text.strip():
            return None
        query_tfidf = self._vectorizer.transform([query_text])
        query_vector = self._svd.transform(query_tfidf)[0]
        norm = np.linalg.norm(query_vector)
        if norm == 0.0:
            return None
        return query_vector / norm

    def vector_for(self, parent_asin: str) -> np.ndarray | None:
        index = self._index_by_asin.get(parent_asin)
        return None if index is None else self._doc_vectors[index]

    def search(self, query_text: str, top_k: int) -> list[str]:
        query_vector = self.project(query_text)
        if query_vector is None:
            return []
        scores = self._doc_vectors @ query_vector
        top_indices = np.argsort(-scores)[:top_k]
        return [self.parent_asins[i] for i in top_indices]
