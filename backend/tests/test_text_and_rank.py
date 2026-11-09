import json
from pathlib import Path

import pytest

from dijitalvatan.indexing.text_normalizer import normalize_search_text, tokenize
from dijitalvatan.ranking.pagerank import compute_ranks

FIXTURES = Path(__file__).parent / "fixtures"


def test_turkish_text_and_queries_share_whole_word_normalization():
    assert normalize_search_text("İSTANBUL IŞIK Türkçe ŞĞÜÖÇ") == "istanbul isik turkce sguoc"
    assert normalize_search_text("İ̇stanbul  --  2026") == "istanbul 2026"
    assert tokenize("Güncel\nDuyurular, TSK!") == ["guncel", "duyurular", "tsk"]
    assert tokenize("") == []
    assert tokenize("a" * 81 + " kisa") == ["kisa"]


def test_pagerank_matches_the_original_implementation_on_the_sample_graph():
    # Output of the original TypeScript computeRanks(SAMPLE_DATASET.graph, 0.8, 10).
    expected = json.loads((FIXTURES / "sample_ranks_from_original.json").read_text())
    ranks = compute_ranks(expected["graph"], 0.8, 10)
    assert ranks.keys() == expected["ranks"].keys()
    for url, rank in expected["ranks"].items():
        assert ranks[url] == pytest.approx(rank, rel=1e-12)


def test_pagerank_of_empty_graph():
    assert compute_ranks({}, 0.8, 10) == {}
