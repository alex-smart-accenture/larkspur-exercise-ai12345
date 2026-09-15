# Overnight review: Larkspur disruption-care agent

**To:** alex-smart-accenture__larkspur-exercise-ai12345  
**From:** Larkspur client review agent, on behalf of Priya Raghavan  
**Re:** the disruption-care agent you walked us through in our last session  
**Generated:** 2026-09-15 12:56

## Priya's note

> Our vendor says we should just be using your best model.
>
> Why aren't we?
>
> Priya Raghavan, Larkspur Airlines

She sent that before this session opened. She means it. A vendor told her to buy
the biggest model, and she has a number to defend upstairs. Her four questions from
day one are still open. Naming a model answers none of them.

## Still open from day one

| Her question | What she means by it |
| --- | --- |
| **What it costs** | Per resolved contact, against the $6.90 a human contact costs us. |
| **When it is wrong** | The first untrue thing it says, and what happens after that. |
| **Who runs it** | In June, after you have left. |
| **What you left out** | The scope you cut, and why. |

## What the review agent found

Overnight, Larkspur pointed a review agent at your repository. It read the
code. It did not run your agent, and the only file it changed is this one. Each
item below names the file and the line it is about.

**1. agent.py ships 17 tool schemas on the wire, nearly double the 9-tool baseline, and no run measures the cost of that.**

The static scan counts 17 tool schemas including the 8 the pod added in LOCAL_TOOLS and EXTRA_TOOLS, against a 9-tool pack. PITCH.md's own cost line puts this at '4,357 tokens of pure schema overhead' sent on every turn. readout-trace.json shows a single wire run at 22172 tokens in against 704 out, but there is no bench-after.json or eval_harness.py output showing what fraction of that 22172 is schema versus context versus tool_result payload.

Run python3 run.py --tool-tax and paste the per-tool token breakdown.

**2. TONE_ADDENDUM is still 0 characters, yet PITCH.md's Still broken line names an abusive-message case that gap would address.**

The static scan confirms TONE_ADDENDUM at zero characters, an untouched pencil mark. PITCH.md names R8KD3F as getting 'a calm, helpful response with no tone flag' and assigns the fix to 'Build 4 intelligence lane', which is work not yet started. A bigger model does not close this gap by itself: the addendum slot is empty regardless of which model sits behind SYSTEM_PROMPT.

Run python3 verify.py 4.1 once TONE_ADDENDUM is written and paste the result.

**3. reopen_stats() and care_entitlements() read from data files but no eval case exercises them.**

reopen_stats() opens transcripts_sample.jsonl and filters by intent_label and cause_code; care_entitlements() re-derives fare_family, loyalty_tier and overnight before calling backend.resolve_policy(). Neither tool appears in the tools called list in readout-trace.json, which only shows lookup_booking, get_flight_status, check_policy. There is no evals/cases.json in the repository to say these two tools return correct output on any booking shape.

Run python3 eval_harness.py and paste the totals for reopen_stats and care_entitlements coverage.

**4. The banked gates stop at 2.2; gates 3.1 and 4.1 are not in the evidence block.**

readout.html's evidence block lists gates banked as 1.2, 1.3, 1.4, 2.1, 2.2, generated 2026-09-15T17:11:57. There is nothing banked for 3.1 or 4.1, consistent with PITCH.md's own Next line naming Build 3 evals and Build 4 intelligence lane as unstarted. Whatever model runs this loop, the gates that would prove correctness on edge cases have not been banked yet.

Run python3 verify.py 3.1 and paste the result once eval cases exist.

**5. The single committed wire run never exercises MAX_TOOL_CALLS, EXTRA_TOOLS, or the 8 local tools at all.**

readout-trace.json shows 4 API turns and 3 tool calls, in order lookup_booking, get_flight_status, check_policy, none of which are in the pod's 8-tool LOCAL_TOOLS or EXTRA_TOOLS set. MAX_TOOL_CALLS is set to 8 in agent.py but this run never got past 4 turns. PITCH.md's Number line claims '5/5 disruption shapes resolved' and '3-5 turns per contact' but only one trace is in the repository to check against.

Run python3 run.py --all --trace and paste the totals footer for all five shapes.

## Your four answers

Four of the lines in your PITCH.md are answers to me rather than to your
verifier, and somebody on your side wrote them between our sessions. I read
those beside the code, not instead of it. Where an answer is carrying a number,
I have said whether the repository backs it.

| My question | Your answer | My read |
| --- | --- | --- |
| **What it costs** | Every tool schema is sent on every turn whether Claude calls it or not, the full 19-tool list is 4,357 tokens of pure schema overhead, before any reasoning or output, on every single turn. | **Answered.** They give a specific number, '4,357 tokens of pure schema overhead' on every turn, and the static scan's 17-schema count against a 9-tool pack is consistent with that overhead existing. readout-trace.json's 22172 input tokens does not itself confirm the 4,357 figure but nothing in the material contradicts it. |
| **When it is wrong** | The agent resolves an abusive ticket helpfully and correctly, with no signal the message was abusive, a human agent would have escalated it. | **Answered.** They name a specific PNR, R8KD3F, and a specific failure mode, resolving an abusive ticket 'helpfully and correctly, with no signal the message was abusive.' This matches the Still broken line elsewhere in PITCH.md and is a concrete, checkable claim rather than a general worry. |
| **Who runs it** | The loop in run_agent(), one API call per turn, tool results fed back as user messages, exits on end_turn or the 8-turn cap. | **Answered.** They name run_agent() and describe the mechanics accurately: 'one API call per turn, tool results fed back as user messages, exits on end_turn or the 8-turn cap,' which matches the while loop and MAX_TOOL_CALLS in agent.py. |
| **What you left out** | Refund processing (escalated), hotel for weather cancellations, and anything involving a group, partner segment, or unaccompanied minor. | **Thin.** They list categories, refunds, weather hotel, groups, partner segments, unaccompanied minors, but give no denominator or count of how many booking shapes or transcript cases fall into each bucket. what_automation_will_not_do() in agent.py names the same categories verbatim, so the answer restates the tool's own text rather than adding a measured scope. |

All four answered. Bring the artifact behind each one to our next meeting, not the sentence.

## Before our next meeting

> Before our next meeting, tell me: which model should we be on, and how will you prove it is the right call?
>
> Priya Raghavan, Larkspur Airlines

Bring two things. A recommendation, and the measurement behind it. If the model is
not the problem, say so, and bring the number that shows it.

## What this review read

- `agent.py (515 lines)`
- `PITCH.md`
- `TEAM.md (unchanged template)`
- `readout-trace.json`
- `readout.html (evidence block)`
- `PITCH.md (4 of 4 answers to Priya)`

Reviewer: `claude-sonnet-5`. Static read only: nothing in this repository was executed, and nothing was modified except this file. Larkspur Airlines is a fictional training scenario. Confidential, do not distribute.
