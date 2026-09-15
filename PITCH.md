# PITCH.md

Six lines and a lever. Your words. The last two are scored.

Built: Larkspur disruption-care agent — a multi-tool loop over the Claude Messages API that handles cancelled and delayed flights end to end.
Does: Looks up the booking, checks live flight status, applies policy, finds alternatives, issues vouchers, and escalates groups and refunds to a human — without the customer asking twice.
Number: 5/5 disruption shapes resolved; 3–5 API turns per contact; next_available_day and fare_rules running over MCP.
Guardrail: confirm_rebooking requires a token only the customer's own Confirm click can produce — the agent cannot supply it, and "the customer said yes in chat" does not substitute for it.
Next: Build 3 evals to prove correctness on edge cases; Build 4 intelligence lane for tone and out-of-scope signals.
Still broken: R8KD3F (abusive message) gets a calm, policy-correct response with no tone gate — that gap is what Build 4 exists to close.
Lever: intelligence

## Priya asked

Costs: Schema tokens alone are 2,868 per turn — every tool you add is paid on every turn, whether Claude calls it or not.
Wrong: The agent resolves the abusive-message ticket helpfully and correctly, with no signal that the message was abusive — a human agent would have flagged it.
Runs it: The loop in run_agent() — one Messages API call per turn, tool results fed back as user messages, exits on end_turn or the 8-turn cap.
Left out: Refund processing (escalated to a specialist), hotel coverage for weather cancellations, and any case involving a group, partner segment, or unaccompanied minor.
