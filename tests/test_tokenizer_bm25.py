from hermes_gizmo.bm25 import BM25
from hermes_gizmo.tokenizer import tokenize


def test_tokenizer_splits_snake_and_kebab_case():
    assert tokenize("github_search-code readFile") == ["github", "search", "code", "read", "file"]


def test_bm25_exact_tool_name_boost_via_identifier_tokens():
    docs = [["github_search_code", "github", "search", "code"] * 4, ["read", "file"]]
    scores = BM25(docs).scores(["github_search_code"])
    assert scores[0] > scores[1]
