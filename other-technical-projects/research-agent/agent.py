"""Research agent with verifiable citations.

Uses the web search tool of the Claude API. Every text block of the answer that
carries citations becomes a "claim" with its sources; text without citations is
kept apart, so the share of unsupported statements can be measured.

Usage:
    python agent.py "What is the capital of Australia?"
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

MODEL = os.getenv("MODEL", "claude-sonnet-5-5")
MAX_SEARCHES = int(os.getenv("MAX_SEARCHES", "5"))
MAX_CONTINUATIONS = 3
MIN_UNCITED_CHARS = 40  # shorter fragments are treated as connective text

SYSTEM_PROMPT = """You are a research agent. Answer the question using web search.
Rules:
- Every factual statement must come from a source found with the search tool and must be cited.
- If the sources you found are not enough to answer, say so explicitly ("I could not find sufficient sources for ...") instead of filling the gap from memory.
- Write concisely, in your own words. Do not copy sentences from the sources.
- No statement without a source."""


@dataclass
class Claim:
    text: str
    sources: list[dict]  # each source: {"url", "title", "cited_text"}


@dataclass
class ResearchResult:
    question: str
    answer: str
    claims: list[Claim] = field(default_factory=list)
    uncited_text: list[str] = field(default_factory=list)
    searches: list[str] = field(default_factory=list)


def parse_content(question: str, content_blocks: list) -> ResearchResult:
    """Turn the API response blocks into a ResearchResult.

    Pure function (no network): testable with fake blocks.
    """
    claims: list[Claim] = []
    uncited: list[str] = []
    searches: list[str] = []
    answer_parts: list[str] = []

    for block in content_blocks:
        btype = getattr(block, "type", None)

        if btype == "server_tool_use" and getattr(block, "name", "") == "web_search":
            query = (getattr(block, "input", None) or {}).get("query")
            if query:
                searches.append(query)

        elif btype == "text":
            text = getattr(block, "text", "") or ""
            answer_parts.append(text)
            stripped = text.strip()
            if not stripped:
                continue
            citations = getattr(block, "citations", None) or []
            if citations:
                sources, seen = [], set()
                for c in citations:
                    url = getattr(c, "url", None)
                    cited = getattr(c, "cited_text", "") or ""
                    key = (url, cited)
                    if url and key not in seen:
                        seen.add(key)
                        sources.append(
                            {"url": url, "title": getattr(c, "title", "") or "", "cited_text": cited}
                        )
                if sources:
                    claims.append(Claim(text=stripped, sources=sources))
                    continue
            if len(stripped) >= MIN_UNCITED_CHARS:
                uncited.append(stripped)

    return ResearchResult(
        question=question,
        answer="".join(answer_parts).strip(),
        claims=claims,
        uncited_text=uncited,
        searches=searches,
    )


def run_research(question: str, client=None) -> ResearchResult:
    """Run the research. Handles 'pause_turn' by continuing the turn."""
    if client is None:
        import anthropic

        client = anthropic.Anthropic()

    tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": MAX_SEARCHES}]
    messages = [{"role": "user", "content": question}]
    all_blocks: list = []

    for _ in range(MAX_CONTINUATIONS + 1):
        response = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )
        all_blocks.extend(response.content)
        if response.stop_reason != "pause_turn":
            break
        messages.append({"role": "assistant", "content": response.content})

    return parse_content(question, all_blocks)


def format_result(result: ResearchResult) -> str:
    """Readable answer with numbered notes and a source list."""
    lines = [result.question, "", "ANSWER"]
    source_index: dict[str, int] = {}
    for claim in result.claims:
        refs = []
        for s in claim.sources:
            n = source_index.setdefault(s["url"], len(source_index) + 1)
            if n not in refs:
                refs.append(n)
        lines.append(f"{claim.text} [{', '.join(map(str, refs))}]")
    for text in result.uncited_text:
        lines.append(f"{text} [NO SOURCE]")
    lines += ["", "SOURCES"]
    titles = {s["url"]: s["title"] for c in result.claims for s in c.sources}
    for url, n in source_index.items():
        lines.append(f"[{n}] {titles.get(url) or url} - {url}")
    lines += ["", f"Searches run: {len(result.searches)}"]
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('Usage: python agent.py "your question"')
    print(format_result(run_research(" ".join(sys.argv[1:]))))
