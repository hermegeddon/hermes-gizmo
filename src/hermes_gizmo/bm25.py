from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass
class BM25:
    documents: Sequence[Sequence[str]]
    k1: float = 1.5
    b: float = 0.75

    def __post_init__(self) -> None:
        self._doc_count = len(self.documents)
        self._avgdl = sum(len(doc) for doc in self.documents) / self._doc_count if self._doc_count else 0.0
        self._freqs = [Counter(doc) for doc in self.documents]
        doc_freq: Counter[str] = Counter()
        for doc in self.documents:
            doc_freq.update(set(doc))
        self._idf = {
            term: math.log(1 + (self._doc_count - freq + 0.5) / (freq + 0.5))
            for term, freq in doc_freq.items()
        }

    def score(self, query_tokens: Iterable[str], index: int) -> float:
        if not self._doc_count or index >= self._doc_count:
            return 0.0
        freqs = self._freqs[index]
        doc_len = len(self.documents[index]) or 1
        score = 0.0
        for term in query_tokens:
            tf = freqs.get(term, 0)
            if not tf:
                continue
            denom = tf + self.k1 * (1 - self.b + self.b * doc_len / (self._avgdl or 1))
            score += self._idf.get(term, 0.0) * (tf * (self.k1 + 1)) / denom
        return score

    def scores(self, query_tokens: Iterable[str]) -> list[float]:
        query = list(dict.fromkeys(query_tokens))
        return [self.score(query, idx) for idx in range(self._doc_count)]
