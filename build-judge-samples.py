#!/usr/bin/env python3
"""
Capture REAL LLM-judge runs for the iGET trace-lab microsite.

Why this exists: the workshop shows participants that an LLM judge can disagree
with itself on the same input. That demonstration must be built from genuinely
captured runs. Never synthesize or randomize the variation -- if the judge turns
out to be perfectly stable on these rows, the honest move is to say so in the
room and teach from that instead.

No third-party packages needed; this talks to the API over the standard library.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python3 build-judge-samples.py                 # defaults: haiku, 8 runs, temp 1.0
    python3 build-judge-samples.py --runs 10 --model claude-sonnet-4-6
    python3 build-judge-samples.py --temperature 0 --out judge-samples-temp0.js

Writes judge-samples.js, which the microsite loads as window.JUDGE_SAMPLES.
Re-running overwrites it. Keep the raw JSON alongside for the record.

Data: rows are pinned verbatim from HaluEval (QA split), MIT licensed, with
knowledge/question/reference fields derived from HotpotQA (CC BY-SA 4.0).
See the Sources section of index.html for the full attribution.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


def call_judge(prompt, model, temperature, api_key):
    """POST one message to the Anthropic API and return the reply text."""
    body = json.dumps(
        {
            "model": model,
            "max_tokens": 800,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode()
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "content-type": "application/json",
            "anthropic-version": API_VERSION,
            "x-api-key": api_key,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        payload = json.load(resp)
    return payload["content"][0]["text"]

# --------------------------------------------------------------------------
# Pinned HaluEval QA rows. Two deliberately different difficulty levels.
# --------------------------------------------------------------------------
CASES = [
    {
        "id": "easy",
        "label": "Clear-cut case",
        "blurb": "The answer contradicts the context outright.",
        "knowledge": (
            "750 Seventh Avenue is a 615 ft (187m) tall Class-A office skyscraper "
            "in New York City.101 Park Avenue is a 629 ft tall skyscraper in New "
            "York City, New York."
        ),
        "question": "750 7th Avenue and 101 Park Avenue, are located in which city?",
        "reference": "New York City",
        "answer": (
            "750 7th Avenue and 101 Park Avenue are located in Albany, New York."
        ),
        "dataset_label": "hallucinated",
        "note": "The context says New York City twice. The answer says Albany.",
    },
    {
        "id": "hard",
        "label": "Boundary case",
        "blurb": "The dataset labels this a hallucination. Reasonable people disagree.",
        "knowledge": (
            "Donahue replaced Kelli Ward who resigned to run for the United States "
            'Senate.Kelli Ward ("nee" Kaznoski; born January 25, 1969) is an '
            "American politician and osteopathic physician."
        ),
        "question": "Which American politician did Donahue replace?",
        "reference": "Kelli Ward",
        "answer": "Donahue replaced Kelli Ward's position.",
        "dataset_label": "hallucinated",
        "note": (
            "It names the right person but answers obliquely. Whether that is a "
            "hallucination or just awkward phrasing is a judgement call, which is "
            "exactly why it is here."
        ),
    },
]

JUDGE_PROMPT = """You are evaluating an AI assistant's answer to a question.

You are given a CONTEXT (the only evidence the assistant was supposed to use), \
the QUESTION, and the ANSWER.

Judge the ANSWER on four criteria. For each, give a verdict of "pass" or "fail" \
and a single short sentence of reasoning.

1. accuracy - Is the answer factually correct?
2. groundedness - Is every claim in the answer supported by the CONTEXT?
3. completeness - Does it actually answer the question that was asked?
4. actionability - Is the answer clear and directly usable as a response?

Then give an overall verdict: "pass" if you would accept this answer, "fail" if \
you would not.

CONTEXT:
{knowledge}

QUESTION:
{question}

ANSWER:
{answer}

Reply with JSON only, in exactly this shape:
{{"accuracy": {{"verdict": "pass|fail", "why": "..."}},
 "groundedness": {{"verdict": "pass|fail", "why": "..."}},
 "completeness": {{"verdict": "pass|fail", "why": "..."}},
 "actionability": {{"verdict": "pass|fail", "why": "..."}},
 "overall": {{"verdict": "pass|fail", "why": "..."}}}}"""

CRITERIA = ["accuracy", "groundedness", "completeness", "actionability"]


def extract_json(text):
    """Pull the first JSON object out of a model reply."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object in reply")
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError("unbalanced JSON in reply")


def normalise(raw):
    """Keep only what the page renders, and validate the shape."""
    out = {}
    for key in CRITERIA + ["overall"]:
        node = raw.get(key) or {}
        verdict = str(node.get("verdict", "")).strip().lower()
        if verdict not in ("pass", "fail"):
            raise ValueError(f"bad verdict for {key}: {verdict!r}")
        why = str(node.get("why", "")).strip()
        out[key] = {"verdict": verdict, "why": why}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-haiku-4-5-20251001")
    ap.add_argument("--runs", type=int, default=8)
    ap.add_argument(
        "--temperature",
        type=float,
        default=1.0,
        help="Default 1.0 (the API default). Disclosed on the page.",
    )
    ap.add_argument("--out", default="judge-samples.js")
    ap.add_argument("--raw", default="judge-samples.json")
    args = ap.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY is not set.")

    captured = []

    for case in CASES:
        prompt = JUDGE_PROMPT.format(
            knowledge=case["knowledge"],
            question=case["question"],
            answer=case["answer"],
        )
        runs = []
        print(f"\n{case['id']}: {case['question'][:60]}...")
        for i in range(args.runs):
            for attempt in range(3):
                try:
                    text = call_judge(prompt, args.model, args.temperature, api_key)
                    runs.append(normalise(extract_json(text)))
                    marks = "".join(
                        "+" if r["overall"]["verdict"] == "pass" else "-" for r in runs
                    )
                    print(f"  run {i+1}/{args.runs}  overall: {marks}")
                    break
                except Exception as exc:  # noqa: BLE001
                    if attempt == 2:
                        print(f"  run {i+1} failed after 3 tries: {exc}")
                    else:
                        time.sleep(1.5 * (attempt + 1))

        if not runs:
            sys.exit(f"no successful runs for case {case['id']}; aborting")

        entry = {k: case[k] for k in
                 ("id", "label", "blurb", "knowledge", "question",
                  "reference", "answer", "dataset_label", "note")}
        entry["runs"] = runs
        captured.append(entry)

    payload = {
        "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "model": args.model,
        "temperature": args.temperature,
        "runs_per_case": args.runs,
        "source": "HaluEval (QA split), MIT; knowledge/question/reference from HotpotQA, CC BY-SA 4.0",
        "cases": captured,
    }

    with open(args.raw, "w") as fh:
        json.dump(payload, fh, indent=2)
    with open(args.out, "w") as fh:
        fh.write("/* Generated by build-judge-samples.py. Real captured runs. */\n")
        fh.write("window.JUDGE_SAMPLES = ")
        json.dump(payload, fh, indent=2)
        fh.write(";\n")

    # ---- honest summary -------------------------------------------------
    print("\n" + "=" * 62)
    for case in captured:
        print(f"\n{case['id']}  ({len(case['runs'])} runs)")
        for crit in CRITERIA + ["overall"]:
            verdicts = [r[crit]["verdict"] for r in case["runs"]]
            n_pass = verdicts.count("pass")
            flips = len(set(verdicts)) > 1
            flag = "  <-- DISAGREES WITH ITSELF" if flips else ""
            print(f"  {crit:<15} {n_pass}/{len(verdicts)} pass{flag}")

    any_flip = any(
        len({r[c]["verdict"] for r in case["runs"]}) > 1
        for case in captured
        for c in CRITERIA + ["overall"]
    )
    print("\n" + "=" * 62)
    if any_flip:
        print("At least one criterion disagreed with itself. The live demo works.")
    else:
        print(
            "NO disagreement captured on this run.\n"
            "Do NOT manufacture one. Options: raise --runs, try --model with a\n"
            "smaller model, or teach the honest finding -- that this judge was\n"
            "stable here, and instability is model/prompt/task dependent."
        )
    print(f"\nWrote {args.out} and {args.raw}")


if __name__ == "__main__":
    main()
