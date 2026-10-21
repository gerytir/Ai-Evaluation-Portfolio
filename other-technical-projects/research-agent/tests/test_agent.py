"""Unit tests: no network, no API key. Run with `pytest`."""
import sys
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import format_result, parse_content  # noqa: E402
from metrics import is_refusal, keyword_coverage, summarize  # noqa: E402
from verify import parse_verdict  # noqa: E402


def cite(url="https://example.org/a", title="Source A", text="passage"):
    return NS(url=url, title=title, cited_text=text)


def blocks():
    return [
        NS(type="server_tool_use", name="web_search", input={"query": "capital of australia"}),
        NS(type="web_search_tool_result", content=[]),
        NS(type="text", text="According to sources, ", citations=None),
        NS(
            type="text",
            text="The capital of Australia is Canberra, chosen as a compromise between Sydney and Melbourne.",
            citations=[
                cite(text="Canberra was chosen as a compromise"),
                cite(text="Canberra was chosen as a compromise"),
            ],
        ),
        NS(
            type="text",
            text="This long sentence carries no citation at all and must therefore be flagged as unsourced.",
            citations=None,
        ),
    ]


def test_parse_separates_cited_and_uncited():
    r = parse_content("question", blocks())
    assert len(r.claims) == 1
    assert len(r.uncited_text) == 1  # the short connective "According to sources," is ignored
    assert r.searches == ["capital of australia"]


def test_parse_deduplicates_sources():
    r = parse_content("question", blocks())
    assert len(r.claims[0].sources) == 1


def test_format_marks_uncited_text():
    out = format_result(parse_content("question", blocks()))
    assert "[1]" in out
    assert "[NO SOURCE]" in out


def test_parse_verdict_valid_and_wrapped():
    assert parse_verdict('{"verdict": "supported", "reason": "ok"}')["verdict"] == "supported"
    wrapped = 'Here:\n```json\n{"verdict": "Partial", "reason": "x"}\n```'
    assert parse_verdict(wrapped)["verdict"] == "partial"


def test_parse_verdict_invalid_defaults_to_unsupported():
    assert parse_verdict("no idea")["verdict"] == "unsupported"
    assert parse_verdict('{"verdict": "maybe"}')["verdict"] == "unsupported"
    assert parse_verdict("")["verdict"] == "unsupported"


def test_keyword_coverage():
    assert keyword_coverage("Canberra and Sydney", ["canberra", "Sydney", "Melbourne"]) == 2 / 3
    assert keyword_coverage("anything", []) is None


def test_is_refusal():
    assert is_refusal("I could not find sufficient sources to answer this.")
    assert not is_refusal("Revenue was 100 billion dollars.")


def test_summarize():
    rows = [
        {"verdicts": ["supported", "supported", "unsupported"], "n_uncited": 1, "coverage": 1.0,
         "expect_refusal": False, "refused": False, "n_searches": 2},
        {"verdicts": [], "n_uncited": 0, "coverage": None,
         "expect_refusal": True, "refused": True, "n_searches": 1},
    ]
    s = summarize(rows)
    assert s["cited_claims"] == 3
    assert s["uncited_claims"] == 1
    assert s["citation_rate"] == 0.75
    assert s["supported_rate"] == round(2 / 3, 3)
    assert s["traps_handled"] == 1.0
    assert s["avg_searches"] == 1.5
