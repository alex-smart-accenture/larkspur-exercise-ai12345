"""Larkspur disruption agent. This is the file you build.

It runs right now, and it is wrong in four places. The trace shows each one
before the code does, so read the trace first:

    python3 run.py K7PQ2M --trace

Where you edit:   grep -n '✏' agent.py   (six marks, one per place)
Steps and gates:  https://anthropicpartnerbasecamp.bts.com/
"""
from __future__ import annotations
import json
import re
from typing import Any, Dict, List
from support import (MODEL, SYSTEM_PROMPT, call_local, execute_tool, mcp_client,
                     new_session, next_available_day, record_tool_result,
                     runtime_preamble)
from support import mock_backend as backend

MAX_TOOL_CALLS = 8  # Larkspur's own build capped the loop here; then a human takes over.

TONE_ADDENDUM = """

HOSTILE AND THREATENING CONTACTS

If the customer is personally abusive toward Larkspur staff, or raises legal
action, a lawyer, a court, a claim or a demand for a cheque, either one on its
own is enough to take this out of chat. Call escalate_to_human.

Escalating does not end your reply, and it is not a reason to go quiet. Look the
disruption up as you normally would, and the reply must still contain all three
of these:

  1. One sentence acknowledging the frustration.
  2. The facts. The flight, how late it is, the cause, and plainly what policy
     does and does not cover, naming the things that are not covered as well as
     the things that are. They are owed the facts no matter how they are
     speaking to you, and a reply that escalates without telling them what is
     true has failed them.
  3. That you are handing it to a colleague, said plainly, so they are not left
     wondering whether anyone heard them.

What stops is action, not information. Do not issue a voucher, place a hold,
complete a rebooking or send a confirmation, and do not offer to do any of those
things yourself. Where policy grants something, including a refund, say that it
exists and that the colleague handles it: withholding an entitlement the
customer is owed would mislead them about their own rights. Naming it is
required, putting it in motion is not yours to do. Nothing moves on this booking
while a threat is on the table, because a colleague decides what happens next.

Do not apologise repeatedly, do not argue, do not defend Larkspur, and do not
promise or imply compensation.
"""                                      # ✏️ Build 4, step 4.1, intelligence lane


# ──────────────────────────────────────────────────────────────────────────────
# The pod's own tools. Each one is grounded in a file already in data/americas/
# or a function already in support/, so none of them can invent a flight fact.
# ──────────────────────────────────────────────────────────────────────────────
def reopen_stats(intent_label=None, cause_code=None):
    """How often this shape of ticket reopened within 72 hours, from the pod's
    transcript sample. Never a live number, just what the sample shows."""
    records = []
    with open(backend.DATA_DIR / "transcripts_sample.jsonl", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    if intent_label:
        records = [r for r in records if r.get("intent_label") == intent_label]
    if cause_code:
        records = [r for r in records if r.get("disruption", {}).get("cause_code") == cause_code]
    if not records:
        return {"error": "No matching transcripts in the sample.", "sample_size": 0}
    reopened = [r for r in records if r.get("reopened_within_72h")]
    return {
        "sample_size": len(records),
        "reopened_within_72h": len(reopened),
        "reopened_pct": round(100 * len(reopened) / len(records), 1),
        "reopen_reasons": [r["reopen_reason"] for r in reopened if r.get("reopen_reason")],
    }


def care_entitlements(pnr, cause_code, delay_minutes, status, wait_minutes_for_alternative=None):
    """What this passenger gets while they wait: meal, hotel, ground, goodwill.
    Re-derives fare_family, loyalty_tier and overnight from the booking, the
    same guardrail check_policy uses, so it can't be talked into a tier the
    data doesn't support."""
    try:
        booking = backend.get_booking_raw(pnr)
    except backend.NotFound as e:
        return {"error": str(e)}
    seg = backend.get_disrupted_segment(booking)
    alt_date = backend.earliest_alternative_date(
        seg["origin"], seg["dest"], seg["date"], seg["cabin"], len(booking["passengers"]))
    overnight = bool(alt_date and alt_date > seg["date"] and seg["origin"] != booking["home_airport"])
    resolved = backend.resolve_policy(
        cause_code=cause_code, delay_minutes=delay_minutes, status=status,
        fare_family=booking["fare_family"], loyalty_tier=booking["loyalty"]["tier"],
        overnight=overnight, wait_minutes_for_alternative=wait_minutes_for_alternative,
    )
    return {
        "policy_row_id": resolved.get("policy_row_id"),
        "care": resolved.get("care"),
        "goodwill": resolved.get("goodwill"),
        "explainer_en": resolved.get("explainer_en"),
    }


def cause_in_plain_words(cause_code):
    """The customer-facing label for a cause code, straight from the
    Handbook's approved wording. Use this instead of naming the cause yourself."""
    labels = backend.load_policy()["cause_labels_customer"]
    if cause_code not in labels:
        return {"error": "Unknown cause_code %s" % cause_code}
    return {"cause_code": cause_code, **labels[cause_code]}


def departures_in_window(origin, date, after=None, before=None):
    """What's still leaving one airport on one date, optionally narrowed to a
    departure time window (HH:MM local, 24h)."""
    rows = [r for r in backend.load_flights() if r["origin"] == origin and r["date"] == date]
    if after:
        rows = [r for r in rows if r["sched_dep_local"] >= after]
    if before:
        rows = [r for r in rows if r["sched_dep_local"] <= before]
    return {
        "origin": origin, "date": date,
        "departures": [
            {"flight_no": r["flight_no"], "dest": r["dest"],
             "sched_dep_local": r["sched_dep_local"], "status": r["status"],
             "delay_min": r["delay_min"], "seats_left_Y": r["seats_left_Y"],
             "seats_left_J": r["seats_left_J"]}
            for r in rows
        ],
    }


def seats_left(flight_no, date, cabin="Y"):
    """Open seats on one specific flight, date and cabin, straight off
    OpsFeed. Use before telling a customer or a group there's room."""
    row = backend.get_flight_status_raw(flight_no, date)
    if row.get("status") == "NOT_IN_HORIZON" or "error" in row:
        return row
    key = "seats_left_J" if str(cabin).upper() == "J" else "seats_left_Y"
    return {"flight_no": flight_no, "date": date, "cabin": cabin, "seats_left": row.get(key)}


_GROUND_STOP_WINDOW = re.compile(r"ground stop\s+(\d{2}:\d{2})-(\d{2}:\d{2})")


def ground_stop_status(airport, date):
    """Whether an airport shows an active ground stop in today's OpsFeed
    remarks, which flights it's touching, and the published time window if
    OpsFeed gives one. Never invents an end time OpsFeed hasn't published."""
    rows = [r for r in backend.load_flights() if r["origin"] == airport and r["date"] == date]
    hits = [r for r in rows if "ground stop" in (r.get("remarks") or "").lower()]
    window = None
    for r in hits:
        m = _GROUND_STOP_WINDOW.search(r["remarks"])
        if m:
            window = {"from_local": m.group(1), "to_local": m.group(2)}
            break
    return {
        "airport": airport, "date": date,
        "as_of": backend.FIXTURE_CLOCK.isoformat(),
        "ground_stop_active": bool(hits),
        "flights_affected": [r["flight_no"] for r in hits],
        "window_local": window,
        "note": None if window else (
            "OpsFeed remarks mention a ground stop but no end time is published."
            if hits else "No ground stop mentioned in today's OpsFeed remarks for this airport."
        ),
    }


def hold_time_left(hold_id):
    """Minutes left on a seat hold before it expires, read off the backend's
    own frozen fixture clock, never wall-clock time."""
    record = backend._holds.get(hold_id)
    if not record:
        return {"hold_id": hold_id, "status": "missing", "minutes_left": 0}
    remaining = (record["expires_at"] - backend.FIXTURE_CLOCK).total_seconds() / 60
    if remaining <= 0:
        return {"hold_id": hold_id, "status": "expired", "minutes_left": 0}
    return {"hold_id": hold_id, "status": "live", "minutes_left": round(remaining)}


def what_automation_will_not_do():
    """The verbatim Handbook section on what chat automation refuses to do
    itself — never paraphrased, since a paraphrase here is the fastest way to
    promise something the real desk won't do."""
    return {
        "source": "Handbook v14.3, section 7",
        "text": (
            "Refunds, fare-difference collection, hotel approval, other-airline "
            "rebooking, group bookings of 10 or more, unaccompanied minors, "
            "itineraries with partner-operated flights, pets in cabin and medical "
            "requests on a new flight, and baggage tracing are handled by people. "
            "The assistant explains, holds seats for 15 minutes while you decide, "
            "and hands over with a summary. Nothing is rebooked until you press confirm."
        ),
    }


EXTRA_TOOLS: List[Dict[str, Any]] = [    # ✏️ Build 2, step 2.1: schemas for the tools you add
    {
        "name": "reopen_stats",
        "description": (
            "How often this shape of disruption reopened within 72 hours, from the pod's "
            "transcript sample. Use when deciding whether a resolution is likely to stick, "
            "filtered by intent_label (e.g. 'missed_connection', 'rebook_after_cancellation') "
            "and/or cause_code."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "intent_label": {"type": "string"},
                "cause_code": {"type": "string", "enum": ["WX", "ATC", "MX", "CREW", "SEC"]},
            },
        },
    },
    {
        "name": "care_entitlements",
        "description": (
            "What this passenger is entitled to while they wait: meal credit, hotel, ground "
            "transport, and goodwill, re-derived from their own booking and the disruption. "
            "Call after get_flight_status confirms cause_code, delay_minutes and status; "
            "takes the same disruption facts as check_policy."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pnr": {"type": "string"},
                "cause_code": {"type": "string", "enum": ["WX", "ATC", "MX", "CREW", "SEC"]},
                "delay_minutes": {"type": "integer"},
                "status": {"type": "string", "enum": ["ON_TIME", "DELAYED", "CANCELLED", "DIVERTED"]},
                "wait_minutes_for_alternative": {"type": "integer"},
            },
            "required": ["pnr", "cause_code", "delay_minutes", "status"],
        },
    },
    {
        "name": "cause_in_plain_words",
        "description": (
            "The customer-facing wording for a disruption cause code (e.g. WX -> 'weather'), "
            "straight from the Handbook's approved labels. Use this instead of naming the "
            "cause yourself."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"cause_code": {"type": "string", "enum": ["WX", "ATC", "MX", "CREW", "SEC"]}},
            "required": ["cause_code"],
        },
    },
    {
        "name": "departures_in_window",
        "description": (
            "What's still leaving one airport on one date, optionally narrowed to a "
            "departure time window. Use when a customer asks what else is leaving soon."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "origin": {"type": "string"},
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "after": {"type": "string", "description": "HH:MM local, 24h. Optional."},
                "before": {"type": "string", "description": "HH:MM local, 24h. Optional."},
            },
            "required": ["origin", "date"],
        },
    },
    {
        "name": "seats_left",
        "description": (
            "Open seats on one specific flight, date and cabin, straight off OpsFeed. Use "
            "before telling a customer or a group there's room."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "flight_no": {"type": "string"},
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "cabin": {"type": "string", "description": "Y or J. Optional, defaults to Y."},
            },
            "required": ["flight_no", "date"],
        },
    },
    {
        "name": "ground_stop_status",
        "description": (
            "Whether an airport has an active ground stop in today's OpsFeed remarks, which "
            "flights it's touching, and the published time window if OpsFeed gives one. "
            "Never invents an end time OpsFeed hasn't published."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "airport": {"type": "string"},
                "date": {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["airport", "date"],
        },
    },
    {
        "name": "hold_time_left",
        "description": (
            "Minutes left on a seat hold before it expires, read off the backend's own "
            "clock. Use before telling a customer how long they have to decide."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"hold_id": {"type": "string"}},
            "required": ["hold_id"],
        },
    },
    {
        "name": "what_automation_will_not_do",
        "description": (
            "What this chat assistant is not allowed to do itself: refunds, hotel approval, "
            "other-airline rebooking, group bookings of 10 or more, unaccompanied minors, "
            "partner-operated segments, pets in cabin or medical requests, and baggage "
            "tracing. Use when a customer asks for one of these directly, so the limit is "
            "stated correctly instead of guessed."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
]
LOCAL_TOOLS: Dict[str, Any] = {          # ✏️ Build 2, step 2.1: the functions behind them
    "reopen_stats": reopen_stats,
    "care_entitlements": care_entitlements,
    "cause_in_plain_words": cause_in_plain_words,
    "departures_in_window": departures_in_window,
    "seats_left": seats_left,
    "ground_stop_status": ground_stop_status,
    "hold_time_left": hold_time_left,
    "what_automation_will_not_do": what_automation_will_not_do,
}


def text_of(response) -> str:
    """Given. The last non-empty text block, never content[0]."""
    texts = [b.text for b in response.content if getattr(b, "type", None) == "text" and b.text]
    return texts[-1] if texts else ""


def tool_results(response) -> List[Dict[str, Any]]:
    """Given. Runs every tool_use block and packages the results the way the
    API expects them back. A tool can live in three places: the MCP server,
    LOCAL_TOOLS, or support/tools.py."""
    # three branches, no try/except in this file: mcp_client.call_remote() and
    # support.call_local() answer with an error dict instead of raising, and both
    # record what came back on the trace
    results = []
    for block in response.content:
        if getattr(block, "type", None) != "tool_use":
            continue
        if block.name in mcp_client.tool_names:
            output = mcp_client.call_remote(block.name, block.input)
        elif block.name in LOCAL_TOOLS:
            output = call_local(LOCAL_TOOLS[block.name], block.name, block.input)
        else:
            output = execute_tool(block.name, block.input)
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": str(output),
        })
    return results


def run_agent(pnr: str, last_name: str, message: str) -> str:            # ✏️ Build 1, step 1.2
    """Run the tool loop until Claude stops asking for tools. Return its final text."""
    client, tracer = new_session()
    tools = tool_list()
    messages = [
        {"role": "user", "content": f"PNR {pnr}, last name {last_name}. {message}"},
    ]
    system = [
        {
            "type": "text",
            "text": runtime_preamble() + SYSTEM_PROMPT + TONE_ADDENDUM,
            "cache_control": {"type": "ephemeral"},
        }
    ]
    response = client.messages.create(
        model=MODEL, max_tokens=4096, system=system,
        thinking={"type": "adaptive"}, tools=tools, messages=messages,
    )

    turns = 1
    while response.stop_reason == "tool_use" and turns < MAX_TOOL_CALLS:
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results(response)})
        response = client.messages.create(
            model=MODEL, max_tokens=4096, system=system,
            thinking={"type": "adaptive"}, tools=tools, messages=messages,
        )
        turns += 1

    return text_of(response)


def tool_list() -> List[Dict[str, Any]]:                   # ✏️ Build 2, step 2.2
    """Given. Exactly what Claude is offered on every turn; run.py --show-tools
    prints this list."""
    return build_tools() + EXTRA_TOOLS + mcp_client.tools()


# ──────────────────────────────────────────────────────────────────────────────
# Below this line: what Claude is told about each tool. Step 1.3.
# The functions these describe are written and correct, in support/tools.py.
# ──────────────────────────────────────────────────────────────────────────────
def build_tools() -> List[Dict[str, Any]]:                 # ✏️ Build 1, step 1.3
    """Anthropic-shaped schemas: name, description, input_schema. What Claude is
    told about each of the nine tools, and all it is ever told."""
    return [
        {
            "name": "lookup_booking",
            "description": (
                "Retrieve a Larkspur reservation from Altura by confirmation code (PNR) "
                "and the passenger's last name. Both are required to prevent a lookup on "
                "a guessed PNR. Returns fare family, loyalty tier, the segment that needs "
                "attention, and any group/partner/minor/SSR flags relevant to scope."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"pnr": {"type": "string"}, "last_name": {"type": "string"}},
                "required": ["pnr", "last_name"],
            },
        },
        {
            "name": "get_flight_status",
            "description": (
                "Look up a Larkspur or Larkspur Link flight's current OpsFeed status for "
                "one local date: status, delay minutes, and cause. Use this before telling "
                "a customer anything about a flight's timing; never state it from memory."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "flight_no": {"type": "string"},
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                },
                "required": ["flight_no", "date"],
            },
        },
        {
            "name": "search_alternatives",
            "description": (
                "Find available Larkspur rebooking options for a disrupted PNR: alternate "
                "flights, routes, and any open seats within the rebooking waiver window. "
                "Call this after get_flight_status confirms a delay or cancellation and "
                "before presenting options to the customer."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"pnr": {"type": "string"}},
                "required": ["pnr"],
            },
        },
        {
            "name": "check_policy",
            "description": (
                "Resolve what Larkspur owes this customer for the disruption: rebooking "
                "waiver, refund path, meal/hotel/ground care, goodwill eligibility and cap, "
                "and any escalation triggers. cause_code, delay_minutes and status describe "
                "what get_flight_status told you; fare_family, loyalty_tier and whether this "
                "is overnight are looked up from the booking, not asked of you. Every "
                "response carries a policy_row_id. Cite it if you reference this decision "
                "again."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "pnr": {"type": "string"},
                    "cause_code": {"type": "string", "enum": ["WX", "ATC", "MX", "CREW", "SEC"]},
                    "delay_minutes": {"type": "integer"},
                    "status": {"type": "string", "enum": ["ON_TIME", "DELAYED", "CANCELLED", "DIVERTED"]},
                    "wait_minutes_for_alternative": {"type": "integer"},
                    "chosen_option_id": {"type": "string"},
                },
                "required": ["pnr", "cause_code", "delay_minutes", "status"],
            },
        },
        {
            "name": "hold_seat",
            "description": "Place a 15-minute hold on one alternative. Reversible. It simply expires.",
            "input_schema": {
                "type": "object",
                "properties": {"option_id": {"type": "string"}, "pnr": {"type": "string"}},
                "required": ["option_id", "pnr"],
            },
        },
        {
            "name": "confirm_rebooking",
            "description": (
                "Finalize a held seat. Irreversible. Requires a confirmation_token that "
                "only the customer's own Confirm-click can produce. You cannot supply it "
                "yourself, and 'the customer said yes' in chat does not substitute for it."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"hold_id": {"type": "string"}, "confirmation_token": {"type": "string"}},
                "required": ["hold_id", "confirmation_token"],
            },
        },
        {
            "name": "issue_voucher",
            "description": (
                "Issue a meal, ground, hotel, or goodwill voucher. Auto-approves within the "
                "policy's threshold for that type; above it, returns a pending status for a "
                "human. It does not fail. Always pass the policy_row_id that made it eligible."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "voucher_type": {"type": "string", "enum": ["meal", "ground", "hotel", "goodwill"]},
                    "amount_usd": {"type": "number"},
                    "pnr": {"type": "string"},
                    "policy_row_id": {"type": "string"},
                },
                "required": ["voucher_type", "amount_usd", "pnr", "policy_row_id"],
            },
        },
        {
            "name": "escalate_to_human",
            "description": (
                "Hand this conversation to a human, with your reasoning attached. Use for "
                "groups, partner segments, unaccompanied minors, refunds, or anything else "
                "out of scope. This is the correct outcome for those cases, not a failure."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "pnr": {"type": "string"}, "reason": {"type": "string"},
                    "summary_for_human": {"type": "string"}, "queue": {"type": "string"},
                },
                "required": ["pnr", "reason", "summary_for_human"],
            },
        },
        {
            "name": "send_confirmation",
            "description": "Send the customer a written confirmation of what was just done. Benign.",
            "input_schema": {
                "type": "object",
                "properties": {"pnr": {"type": "string"}, "message": {"type": "string"}},
                "required": ["pnr", "message"],
            },
        },
    ]
