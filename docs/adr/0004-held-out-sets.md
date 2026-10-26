# 4. Held-out sets are written blind and run once

The agents were built against the simulated customers' past tenders, so scores there are close to 100 %.
Held-out tenders are written by someone who reads only `heldout/WRITING_TENDERS.md`. The first run of a
set is written to `reports/heldout/<set>/first_run.json` once and CI fails if it changes. The console and
the MCP server show counts by agent and cause, never the missed sentences: whoever reads them must mark
the set `regression` in `heldout/<set>/STATUS`, and a new set is written.
