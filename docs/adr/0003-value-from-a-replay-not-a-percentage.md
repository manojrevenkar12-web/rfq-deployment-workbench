# 3. Value comes from replaying the customer's own process

"Saves 40 % of the time" cannot be checked. The workbench replays the customer's CRM export: same
arrivals, same people, same buyer delays, with each activity's work scaled by the agents in scope at their
readiness (`config/agents.yaml`). Queues then shrink or not on their own. The replay without agents must
reproduce the observed median lead time (shown next to every lead-time claim); a bootstrap over tenders
gives the interval. Hours by role times the customer's agreed hourly cost gives the value.
