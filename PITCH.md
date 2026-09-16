# PITCH.md

Built: Larkspur disruption-care agent — handles cancelled and delayed flights end to end without a human in the loop for standard cases.
Does: Looks up the booking, checks live flight status, applies policy, finds alternatives, issues vouchers, and escalates groups and refunds to a human — without the customer asking twice.
Number: Model cost per resolved contact cut 71%, $0.0918 to $0.0262, with all 15 of 15 benched conversations still closing the loop; 3 of 5 eval cases pass; 13 tools on the wire, down from 19; 3–5 turns per contact.
Guardrail: Rebooking requires a token only the customer's own Confirm click can produce — the agent cannot generate it, and "the customer said yes in chat" does not substitute.
Next: Make the tone rules hold — 1 in 5 is not a control — then give the agent sight of every segment on a booking, not just one. Run every case 5 times, not once, because one green run is what hid this.
Still broken: On an abusive contact the agent escalates but then goes silent on the facts — it drops the delay, the meal credit and the refund the customer is owed. Measured at 1 pass in 5 runs, and 0 in 5 before the tone rules were written, so the rules are not holding reliably. A hard gate fails on it today.
Lever: cost

## Priya asked

Costs: $0.0262 of model cost per resolved contact against the $6.90 a human contact costs, or $359 a week against $94,530 at 13,700 chats. Down 71% from $0.0918, benched 3 runs across all 5 shapes on a cold cache, so it is a discount production actually gets rather than one borrowed from the previous sweep. Model cost only: Larkspur's own loaded figure runs roughly 40% above it once infrastructure and evals are counted, so do not read this as all-in.
Wrong: Twice, in ways we can point at. On an abusive contact it escalates and then says nothing about the $15 meal credit or the refund the customer is owed — 1 pass in 5 runs. And told "we're going to miss our connection," it agrees, because lookup_booking hands it one segment and the inbound flight is invisible to every tool it has. Neither breaks a booking, because it still asks before it books. Both are answers a human would not have given.
Runs it: The loop in run_agent() — one API call per turn, tool results fed back as user messages, exits on end_turn or the 8-turn cap.
Left out: Of the 5 booking shapes we test, 2 are handed to a human outright — the 12-passenger group (G2HL9V, Group Desk queue GRP1) and anything abusive or carrying a legal threat (R8KD3F). Refund execution is human on all 14 policy rows; the agent only ever names it. Also out: hotel on weather cancellations (not owed, by policy, not by choice), partner segments and unaccompanied minors.
