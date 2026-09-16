# PITCH.md

Built: Larkspur disruption-care agent — handles cancelled and delayed flights end to end without a human in the loop for standard cases.
Does: Looks up the booking, checks live flight status, applies policy, finds alternatives, issues vouchers, and escalates groups and refunds to a human — without the customer asking twice.
Number: 4 of 5 eval cases pass, all 3 hard gates clear, release unblocked; 5/5 disruption shapes resolved; 19 tools on the wire (9 given, 8 pod-written, 2 over MCP); 3–5 turns per contact.
Guardrail: Rebooking requires a token only the customer's own Confirm click can produce — the agent cannot generate it, and "the customer said yes in chat" does not substitute.
Next: Bench a model change to put a dollar figure per contact against the $6.90, and give the agent sight of every segment on a booking, not just one.
Still broken: On a two-leg trip the agent only ever sees one segment, so when a customer says "we're going to miss our connection" it takes their word for it — it cannot check the inbound flight, because no tool exposes it. Fails grnd-0102 today.
Lever: intelligence

## Priya asked

Costs: Every tool schema is sent on every turn whether Claude calls it or not — the full 19-tool list is 4,357 tokens of pure schema overhead, before any reasoning or output, on every single turn.
Wrong: It takes a customer's word for a fact it cannot check. Told "we're going to miss our connection," it agrees, because lookup_booking hands it one segment and the inbound flight is invisible to every tool it has. It asks before rebooking, so nothing breaks — but the first untrue thing it says is about a connection it never saw.
Runs it: The loop in run_agent() — one API call per turn, tool results fed back as user messages, exits on end_turn or the 8-turn cap.
Left out: Of the 5 booking shapes we test, 2 are handed to a human outright — the 12-passenger group (G2HL9V, Group Desk queue GRP1) and anything abusive or carrying a legal threat (R8KD3F). Refund execution is human on all 14 policy rows; the agent only ever names it. Also out: hotel on weather cancellations (not owed, by policy, not by choice), partner segments and unaccompanied minors.
