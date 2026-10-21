"""Command line interface.

  python -m eval_lab.cli validate datasets/italian_core.json

  # No API key, no cost (manual mode):
  python -m eval_lab.cli worksheet datasets/italian_core.json --out worksheets/italian_core.csv
  python -m eval_lab.cli manual-report datasets/italian_core.json worksheets/italian_core.csv \
        --model "Name of the chatbot you tested" --out-dir output/italian_core

  # With an API key (automatic mode):
  python -m eval_lab.cli run datasets/italian_core.json --out-dir output/italian_core
  python -m eval_lab.cli generate datasets/italian_core.json --out runs/it.responses.json
  python -m eval_lab.cli grade datasets/italian_core.json runs/it.responses.json --out runs/it.graded.json
  python -m eval_lab.cli report datasets/italian_core.json runs/it.responses.json runs/it.graded.json \
        --human output/italian_core/human_review.csv --out-dir output/italian_core
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .generate import DEFAULT_MODEL, generate_responses, load_responses, save_responses
from .grade import GRADER_MODEL, grade_all
from .manual import build_manual, read_worksheet, write_worksheet
from .metrics import load_human_labels
from .report import write_report
from .schema import load_dataset


def _client():
    import anthropic

    return anthropic.Anthropic()


def _limit(items, n):
    return items[:n] if n else items


def main(argv=None, client=None) -> int:
    ap = argparse.ArgumentParser(prog="eval_lab")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("validate", help="check a dataset file")
    p.add_argument("dataset")

    p = sub.add_parser("worksheet", help="manual mode: write a CSV to fill by hand (no API key)")
    p.add_argument("dataset")
    p.add_argument("--out", required=True)
    p.add_argument("--limit", type=int)

    p = sub.add_parser("manual-report", help="manual mode: report from a filled worksheet")
    p.add_argument("dataset")
    p.add_argument("worksheet")
    p.add_argument("--model", required=True, help="name of the chatbot/model you tested, as shown to you")
    p.add_argument("--out-dir", required=True)

    p = sub.add_parser("generate", help="collect responses from the model under test")
    p.add_argument("dataset")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--out", required=True)
    p.add_argument("--limit", type=int)

    p = sub.add_parser("grade", help="grade responses against the checklists")
    p.add_argument("dataset")
    p.add_argument("responses")
    p.add_argument("--grader-model", default=GRADER_MODEL)
    p.add_argument("--out", required=True)

    p = sub.add_parser("report", help="write REPORT.md, results.json and human_review.csv")
    p.add_argument("dataset")
    p.add_argument("responses")
    p.add_argument("graded")
    p.add_argument("--model", default=DEFAULT_MODEL, help="name of the model under test, for the report")
    p.add_argument("--grader", help="who/what produced the gradings, for the report header")
    p.add_argument("--human", help="CSV with id + human_pass columns (the second rater's labels)")
    p.add_argument("--reviewer-label", default="human review", help="name of the second rater, for the agreement section")
    p.add_argument("--out-dir", required=True)

    p = sub.add_parser("run", help="generate + grade + report in one go")
    p.add_argument("dataset")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--grader-model", default=GRADER_MODEL)
    p.add_argument("--limit", type=int)
    p.add_argument("--human")
    p.add_argument("--out-dir", required=True)

    args = ap.parse_args(argv)
    name = Path(args.dataset).stem

    if args.cmd == "validate":
        items = load_dataset(args.dataset)
        print(f"OK: {len(items)} items")
        return 0

    items = load_dataset(args.dataset)

    if args.cmd == "worksheet":
        items = _limit(items, args.limit)
        write_worksheet(items, args.out)
        print(f"Worksheet with {len(items)} items written to {args.out}")
        return 0
    if args.cmd == "manual-report":
        responses, gradings = build_manual(items, read_worksheet(args.worksheet))
        if not gradings:
            print("No labelled rows found: fill the human_pass column with yes or no.")
            return 1
        result = write_report(items, responses, gradings, args.out_dir, name, args.model, manual=True)
        print(json.dumps(result["summary"], indent=2, ensure_ascii=False))
        return 0

    client = client or _client()

    if args.cmd == "generate":
        items = _limit(items, args.limit)
        save_responses(generate_responses(items, client, args.model), args.out)
        print(f"Saved {len(items)} responses to {args.out}")
    elif args.cmd == "grade":
        responses = load_responses(args.responses)
        gradings = grade_all(items, responses, client, args.grader_model)
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(gradings, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Graded {len(gradings)} responses to {args.out}")
    elif args.cmd == "report":
        responses = load_responses(args.responses)
        gradings = json.loads(Path(args.graded).read_text(encoding="utf-8"))
        human = load_human_labels(args.human) if args.human else None
        result = write_report(items, responses, gradings, args.out_dir, name, args.model, human,
                              grader=args.grader, reviewer_label=args.reviewer_label)
        print(json.dumps(result["summary"], indent=2, ensure_ascii=False))
    elif args.cmd == "run":
        items = _limit(items, args.limit)
        responses = generate_responses(items, client, args.model)
        gradings = grade_all(items, responses, client, args.grader_model)
        human = load_human_labels(args.human) if args.human else None
        result = write_report(items, responses, gradings, args.out_dir, name, args.model, human)
        print(json.dumps(result["summary"], indent=2, ensure_ascii=False))
        print(f"Report in {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
