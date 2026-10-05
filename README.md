# Trace Lab

A hands-on lab in **trace-based agent evaluation**, from the IEEE iGET 2026 workshop
*The Green Checkmark Is Not Enough* (Irvine, CA · 23 October 2026).

An AI agent can pass a benchmark and still get there in a way you would not ship. A passing score
tells you the output met the check that was run. It does not tell you how the agent got there,
whether the evidence it used was sound, or whether what it changed should ship. This lab is about
reading the thing that can tell you: the trace.

**[Open the lab →](https://agnitrip.github.io/trace-lab/)** · **[Ship-readiness checklist →](https://agnitrip.github.io/trace-lab/checklist.html)**

Nothing to install. Works on a phone.

## What's here

| File | What it is |
|---|---|
| `index.html` | The lab. Two real agent runs from a public benchmark — read what each agent did, decide ship or no-ship. Plus a panel that replays real LLM-judge runs so you can watch a judge agree, then disagree, with itself on the same input. |
| `checklist.html` | A one-page ship-readiness checklist to mark up and take to your next release review. Prints to a single page. |
| `build-judge-samples.py` | Regenerates the judge runs against your own key and model. Standard library only, no dependencies. |
| `judge-samples.json` | The captured runs behind the panel, as a record. |

## About the judge panel

The verdicts in the panel are **real captured runs, replayed in the order they happened** — never
synthesized and never randomized. The generator deliberately refuses to help you manufacture a
disagreement: if a judge turns out to be stable, it says so and tells you to teach that instead.

The run shipped here used `claude-haiku-4-5`, temperature 1.0, 8 repeats per case. What it found:
accuracy and groundedness never moved across 16 runs; completeness and actionability flipped on both
cases. The split that predicted stability was not reference-based versus reference-free — it was
whether a criterion can be settled by pointing at the evidence, or whether it asks "is this *enough*?"
Questions of sufficiency are judgement calls, and judgement calls move.

That is one model, one prompt, one temperature, a handful of repeats. It is illustrative of that
configuration, not a general claim about LLM judges. Run `build-judge-samples.py` yourself and you
will get different sequences.

## Practice the method

[`shipready`](https://github.com/agnitrip/shipready) grades agent readiness from execution traces.

## Sources and licences

The lab describes two agent submissions from
[SWE-bench-Live](https://github.com/microsoft/SWE-bench-Live) (© Microsoft Corporation, MIT). The
step timelines and schematics are **original descriptions written for this workshop** — they
summarise what each agent did and do not reproduce the submitted patches, which live in the
[submission repository](https://github.com/SWE-bench-Live/submission) and carry no blanket licence.
Factual outcomes (which files a patch touched, resolved status, test counts) are reported as facts
with the source linked. The projects under test are [Conan](https://github.com/conan-io/conan)
(© 2019 JFrog Ltd) and [beets](https://github.com/beetbox/beets) (© 2010–2016 Adrian Sampson), each MIT.

The judge examples use [HaluEval](https://github.com/RUCAIBox/HaluEval) (Li et al., 2023, © 2020
RUCAIBox, MIT). HaluEval's knowledge, question and reference fields were collected from
[HotpotQA](https://github.com/hotpotqa/hotpot) (Yang et al., 2018), licensed
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/); its hallucinated answers were
generated for HaluEval. Examples here are selected, reformatted and annotated for teaching.
Copyrightable adaptations of HotpotQA-derived fields are offered under **CC BY-SA 4.0**. Those terms
attach to that material and adaptations of it, not to this collection as a whole.

Original workshop text, code and page design in this repository are released under the
**MIT Licence**, © 2026 Agni Tripathi. No endorsement by any dataset author is implied.
