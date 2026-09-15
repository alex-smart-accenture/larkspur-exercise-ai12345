# PITCH.md

Built: Larkspur disruption-care agent — handles cancelled and delayed flights end to end without a human in the loop for standard cases.
Does: Looks up the booking, checks live flight status, applies policy, finds alternatives, issues vouchers, and escalates groups and refunds to a human — without the customer asking twice.
Number: 5/5 disruption shapes resolved; 19 tools on the wire (9 given, 8 pod-written, 2 over MCP); 3–5 turns per contact.
Guardrail: Rebooking requires a token only the customer's own Confirm click can produce — the agent cannot generate it, and "the customer said yes in chat" does not substitute.
Next: Build 3 evals to prove correctness on edge cases; Build 4 intelligence lane for tone and out-of-scope signals.
Still broken: Abusive message (R8KD3F) gets a calm, helpful response with no tone flag — Build 4 closes that gap.
Lever: intelligence

## Priya asked

Costs: Every tool schema is sent on every turn whether Claude calls it or not — the full 19-tool list is 4,357 tokens of pure schema overhead, before any reasoning or output, on every single turn.
Wrong: The agent resolves an abusive ticket helpfully and correctly, with no signal the message was abusive — a human agent would have escalated it.
Runs it: The loop in run_agent() — one API call per turn, tool results fed back as user messages, exits on end_turn or the 8-turn cap.
Left out: Refund processing (escalated), hotel for weather cancellations, and anything involving a group, partner segment, or unaccompanied minor.
