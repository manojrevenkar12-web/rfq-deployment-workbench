---
name: steerco-prep
description: Prepare a customer SteerCo or quarterly business review from the workbench; use when a strategist asks for a SteerCo pack, a QBR, a status update for a customer's management, or "what do I tell <customer> on Thursday".
---

# SteerCo prep

A SteerCo is where the customer's management decides whether the deployment continues, grows or stops.
The pack has to be true, short and end in decisions. Everything comes from the workbench MCP server
(`rdw-workbench`); never invent a number, and say where each number comes from.

## Steps

1. `customer_brief(customer)`: stage, health, the agreed KPIs with their basis, milestones, risks, the
   stakeholders and what each one cares about. Read the executive's note first: it decides what to lead with
   (bids per head, hours, lead time, risk).
2. `steerco_pack(customer)`: the generated pack. Use it as the skeleton, not as the final text.
3. If the customer is live, `adoption_since_go_live(customer)`: activities whose effort did not fall as
   planned. These are adoption problems, not model problems; name the team and propose the session that
   fixes it.
4. `readiness(customer)` for any agent the pack calls ready; `heldout_results()` for the honest scores.
   Quote held-out numbers when someone asks "how good is it"; the customer's own past tenders were used to
   build the agents and look better than they are.
5. Write the pack:
   - One sentence on where we are, in the executive's terms.
   - KPIs: target, now, before, and the basis ("measured since go-live", "projected from the replay",
     "scored on 40 past tenders"). A projected number is never presented as measured.
   - Two or three asks, each with an owner and a date. Overdue milestones are either re-dated or dropped:
     ask for that decision explicitly.
   - Risks with their mitigation and owner.
6. After the meeting, record each decision with `record_decision(customer, decision, by)` so the next
   pack starts from it.

## Don'ts

- Do not round red KPIs into amber prose.
- Do not promise lead-time gains on waits outside the company (buyer answers); say what the agents change
  there (fewer clarification rounds), not faster buyers.
