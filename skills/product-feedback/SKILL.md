---
name: product-feedback
description: Turn what deployments show into product feedback; use when a strategist or product manager asks what the platform should fix next, which customer requests are core, or for the monthly field report.
---

# Product feedback from the field

A deployment team that only fixes things per customer becomes a services business. This skill separates
what the platform should fix once from what each deployment fixes in its own profile.

## Steps

1. `platform_signals()`: misses the platform owns (vocabulary, value parsing, rules), each with the
   customers it appears at, plus the requirement kinds every customer shares, reviewers' corrections by
   kind, and the onboarding playbook.
2. `heldout_results()`: misses on tenders nobody who built the agents has seen, counted by agent, cause
   and owner. This is the honest backlog; the customers' past tenders were used to build the agents and
   hide most platform misses.
3. Rank: a miss at two or more customers before a miss at one; a red-flag miss (an unsafe answer) before
   a precision miss (extra work); a shared requirement kind before a customer-specific one.
4. For each item write: what fails, at which customers, how many tenders, which agent, and the cause.
   Never paste held-out sentences into the report: whoever reads them can no longer write held-out tests.
5. List customer-specific kinds separately as deployment work (profiles and vocabularies), not as
   product requests.

## Output

A short report: top five platform fixes with evidence, the share of misses each would remove, and what
stays deployment work. Link the held-out set and its first-run date.
