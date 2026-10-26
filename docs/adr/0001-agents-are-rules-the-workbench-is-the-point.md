# 1. The agents are rules; the workbench is the point

The project is about deploying RFQ agents, not about building them. The agents (extraction, red flags,
norms, bid/no-bid, configuration, documentation) are deterministic rules over a vocabulary per domain, so
that every number in the workbench is reproducible in CI and every miss has a cause that can be named.
A model-based extractor would slot into `extract.py` behind the same `Requirement` model; the scoring,
replay and deployment views would not change.
