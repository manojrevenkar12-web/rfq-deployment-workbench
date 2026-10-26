# Research: what the role and the market ask for

Written before the code, to decide what to build. Public sources only; checked October 2026.

## The company and the role

Atira (Munich, founded November 2024) builds agents for industrial sales engineering: companies that sell
complex, built-to-order products and answer requests for quotation (RFQs) with specifications that run to
thousands of pages. It raised $17.5M ($15M seed led by Accel, $2.5M pre-seed; UVC, Fortino, BOOOM and
angels including Celonis co-CEO Bastian Nominacher and Whirlpool CEO Marc Bitzer). The founders come from
Palantir (Florian Diegruber, commercial lead) and Google (August DuMont Schütte, ML engineer). Commercial
launch November 2025; more than 15 customers, named ones including ABB E-Mobility, Chiron Group,
Rema Tip Top and Robel.

Its site names the agents: requirement extraction, red-flag detection, technical questionnaire,
bid/no-bid, norms and standards, commercial feasibility, CPQ, technical documentation and system
writeback, on the customer's CRM, ERP and CPQ. Customer results it publishes: Robel saves 95 hours of sales
and engineering time per RFQ; Chiron 80 % faster inbound processing; AGO Energie handles 2,500 pages per
tender. A Robel team lead says it was working productively within a week. ISO 27001.

The Deployment Strategist role (Munich, on-site, go-to-market) is the Palantir-style forward-deployed
role: scope deployments with customers, configure the agents to their products and processes, run pilots,
prove value to management, and bring what the field learns back into the product; customer-facing up to
C-level, technical enough to build, comfortable with AI tooling (skills and context), 20–40 % travel,
German and English.

## What other applicants will build

An "RFQ parser" or "chat with your tender" demo: the product itself, rebuilt thinner. That shows they can
call a model; it does not show they can deploy one. Nobody hiring a deployment strategist is short of
extraction demos.

## What this project builds instead

The strategist's own tool. The questions it answers are the ones a deployment is judged on:

| The job | In the workbench |
| --- | --- |
| Scope with the customer | Process mining of the CRM export: where tenders wait, internal or external, who is busy |
| Configure to the customer | Capability and norm profiles per customer; misses split into deployment fixes and platform fixes |
| Run the pilot honestly | Agents scored on the customer's past tenders with Wilson lower bounds; a held-out set nobody tuned to |
| Prove value to management | Replay of the same tenders with the agents' readiness; hours, people, lead time with intervals, payback |
| Keep the deployment on track | KPIs with their basis, milestones, adoption since go-live, next steps, SteerCo pack |
| Feed the product | Misses that recur across customers, shared against customer-specific requirement kinds, playbook |
| AI tooling | Claude skills for strategists on an MCP server over the same numbers |

## Sources

- [Pulse 2.0: Atira raises $17.5 million to build AI orchestration platform for industrial sales engineering](https://pulse2.com/atira-raises-17-5-million-to-build-ai-orchestration-platform-for-industrial-sales-engineering/)
- [Accel: our seed investment in Atira](https://accel.com/news/our-seed-investment-in-atira-the-ai-orchestration-layer-for-industrial-sales-engineering)
- [Runtime Wire: Atira raises $17.5M after landing industrial customers without a sales team](https://runtimewire.com/article/atira-raises-17-5m-industrial-sales-ai)
- [Munich Startup: AI company Atira raises 13 million euros](https://www.munich-startup.de/en/news/ai-company-atira-raises-13-million-euros)
- [Dealroom: Atira raises $15M seed to automate industrial sales engineering](https://dealroom.co/news/148649-atira-raises-15m-seed-to-automate-industrial-sales-engineering/)
- [atira.ai](https://atira.ai)

The customers in this repository (Gleiswerk, Voltaro, Brandt) are invented; any resemblance to the
published customer stories is limited to the industries.
