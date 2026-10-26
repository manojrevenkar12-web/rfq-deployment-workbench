---
name: scope-deployment
description: Scope a new or growing deployment from the customer's own data; use when a strategist asks which agents to switch on first, what a deployment is worth, or how to answer a prospect's "what will this do for us".
---

# Scope a deployment

Scope comes from where the customer's quote process loses time and from what the agents can already do on
the customer's own past tenders, not from the product's feature list.

## Steps

1. `process_bottleneck(customer)`: where tenders wait, whether the wait is internal (a queue in front of a
   team) or external (the buyer), and how busy each role is. An internal queue in front of a busy team is
   where agents shorten lead time; external waits only shrink by asking better questions once.
2. `readiness(customer)`: per agent, the lower bound of its score on the customer's past tenders and the
   level it reaches (works on its own, assists a person, not yet, too few tenders). An agent that is not
   ready changes nothing in the value case; fix its misses or leave it out.
3. `value_case(customer, scope=[...])` for two or three candidate scopes. Compare hours by role, people
   freed, lead time with its bootstrap interval, payback against the fee. Pick the smallest scope that
   reaches most of the value: it goes live sooner and is easier to adopt.
4. Check misses with `readiness`: misses owned by the deployment (capability or norm profile) are fixed
   in the customer's profile before go-live; misses owned by the platform go to the product team
   (see the product-feedback skill).
5. Write the scope: agents in, agents out with the reason, the KPIs to agree (target, baseline, basis),
   milestones from the playbook in `platform_signals()` (median days from kickoff to a scored pilot and
   to go-live, and the steps that usually slip).

## Rules

- State the replay's model check ("the replay reproduces the observed median") next to any lead-time
  claim. If it does not reproduce, do not quote lead time.
- Use the customer's hourly costs once they are agreed (`value_case` with `assumptions`); until then say
  the rates are defaults.
