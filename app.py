from __future__ import annotations

import ast
import json
import re
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

API_BASE = "http://127.0.0.1:8000"
STREAM_URL = f"{API_BASE}/api/travel/stream"
THREADS_URL = f"{API_BASE}/api/threads"

st.set_page_config(
    page_title="TripMind AI-Agent",
    page_icon="✈️",
    layout="wide"
)

st.title("🌍 TripMind AI-Agent")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = None

if "last_out" not in st.session_state:
    st.session_state.last_out = None

if "logs" not in st.session_state:
    st.session_state.logs = []

if "sessions_cache" not in st.session_state:
    st.session_state.sessions_cache = None


def log(msg: str):
    st.session_state.logs.append(msg)


def fetch_sessions() -> List[Dict[str, Any]]:
    try:
        resp = requests.get(THREADS_URL, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if data.get("success"):
            return data.get("sessions", [])
    except (requests.exceptions.RequestException, ValueError):
        pass
    return []


def fetch_thread(thread_id: str) -> Optional[Dict[str, Any]]:
    try:
        resp = requests.get(f"{THREADS_URL}/{thread_id}", timeout=20)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        if data.get("success"):
            return data
    except (requests.exceptions.RequestException, ValueError) as e:
        st.sidebar.error(f"Could not load chat: {e}")
    return None


def load_thread_into_session(thread_id: str):
    data = fetch_thread(thread_id)
    if not data:
        st.sidebar.warning("Couldn't find that conversation.")
        return

    st.session_state.thread_id = thread_id
    turns = data.get("turns", [])
    last_answer = turns[-1]["assistant"] if turns else None

    st.session_state.last_out = {
        "thread_id": thread_id,
        "answer": last_answer,
        "flight_results": data.get("flight_results"),
        "hotel_results": data.get("hotel_results"),
        "weather_results": data.get("weather_results"),
        "currency_results": data.get("currency_results"),
        "llm_calls": data.get("llm_calls", 0),
    }


def start_new_chat():
    st.session_state.thread_id = None
    st.session_state.last_out = None


with st.sidebar:
    st.header("💬 Chats")

    if st.button("🆕 New Chat", use_container_width=True):
        start_new_chat()
        st.rerun()

    st.divider()
    st.subheader("Past chats")

    if st.button("🔄 Refresh list", use_container_width=True):
        st.session_state.sessions_cache = fetch_sessions()

    if st.session_state.sessions_cache is None:
        st.session_state.sessions_cache = fetch_sessions()

    sessions = st.session_state.sessions_cache or []

    if not sessions:
        st.caption("No past chats yet — generate a plan to start one.")
    else:
        for s in sessions:
            thread_id = s["thread_id"]
            title = s.get("title") or "Untitled chat"
            is_active = thread_id == st.session_state.thread_id

            label = f"{'🟢 ' if is_active else ''}{title}"
            if st.button(label, key=f"session_{thread_id}", use_container_width=True):
                load_thread_into_session(thread_id)
                st.rerun()

if st.session_state.thread_id:
    st.caption(f"Continuing chat · thread `{st.session_state.thread_id}`")

prompt = st.text_area(
    "Where would you like to travel?",
    height=120,
    placeholder="Example: Plan a 5-day trip to Dubai under ₹80,000"
)
run_btn = st.button("🚀 Generate Plan", type="primary")

tab_plan, tab_flights, tab_hotels, tab_weather, tab_logs = st.tabs(
    ["📋 Trip Plan", "🛫 Flights", "🏨 Hotels", "🌤️ Weather & Currency", "🧾 Logs"]
)

NODE_LABELS = {
    "flight_agent": "🛫 Searching flights",
    "hotel_agent": "🏨 Searching hotels",
    "weather_agent": "🌤️ Checking weather",
    "currency_agent": "💱 Converting currency",
    "itinerary_agent": "🧭 Drafting itinerary",
    "final_agent": "✍️ Writing final response",
}

# Node whose token stream we show live as it's generated — this is the
# node that actually produces the text shown in the Trip Plan tab.
LIVE_TEXT_NODE = "final_agent"

# Must match LIST_ENTRY_SEPARATOR in agent.py — the backend now joins
# separate flights/hotels with this unambiguous marker instead of a plain
# blank line, specifically so this file can split on real item boundaries
# instead of guessing from blank lines (which also appear *inside* a single
# flight/hotel, between its header/Departure/Arrival or name/address/
# categories sections — that collision was what broke the Flights/Hotels
# tabs, splitting one flight or hotel into several fake entries).
LIST_ENTRY_SEPARATOR = "\n\n@@@ENTRY@@@\n\n"


def normalize_to_entries(value: Any) -> List[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]

    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []

        if LIST_ENTRY_SEPARATOR.strip() in s:
            parts = [p.strip() for p in s.split(LIST_ENTRY_SEPARATOR.strip()) if p.strip()]
            if parts:
                return parts

        if s.startswith("[") and s.endswith("]"):
            try:
                parsed = ast.literal_eval(s)
                if isinstance(parsed, list):
                    return [str(v).strip() for v in parsed if str(v).strip()]
            except (ValueError, SyntaxError):
                pass

        # Fallback for content that never had multiple distinct items to
        # begin with (e.g. a single "No live flight data..." message) —
        # treat the whole string as one entry rather than guessing at
        # blank-line boundaries.
        return [s]

    return [str(value)]


def parse_kv_block(text: str) -> Dict[str, Dict[str, str]]:
    sections: Dict[str, Dict[str, str]] = {"top": {}}
    current = "top"

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        header = line.rstrip(":")
        if header in ("Departure", "Arrival") and line.endswith(":"):
            current = header
            sections.setdefault(current, {})
            continue

        cleaned = line.lstrip("-").strip()
        if ":" in cleaned:
            key, _, val = cleaned.partition(":")
            sections.setdefault(current, {})[key.strip()] = val.strip()

    return sections


def render_flight_entry(entry: str, idx: int):
    parsed = parse_kv_block(entry)
    top = parsed.get("top", {})
    dep = parsed.get("Departure", {})
    arr = parsed.get("Arrival", {})

    with st.container(border=True):
        title = " · ".join(x for x in [top.get("Airline"), top.get("Flight")] if x)
        st.markdown(f"**✈️ Flight {idx}: {title or 'Details'}**")
        if top.get("Status"):
            st.caption(f"Status: {top['Status']}")

        col_dep, col_arr = st.columns(2)

        with col_dep:
            st.markdown("**🛫 Departure**")
            if dep:
                st.write(f"{dep.get('Airport', '—')} ({dep.get('IATA', '—')})")
                st.write(f"Terminal {dep.get('Terminal', 'N/A')} · Gate {dep.get('Gate', 'N/A')}")
                st.write(f"🕓 {dep.get('Scheduled', 'N/A')}")
            else:
                st.write("—")

        with col_arr:
            st.markdown("**🛬 Arrival**")
            if arr:
                st.write(f"{arr.get('Airport', '—')} ({arr.get('IATA', '—')})")
                st.write(f"Terminal {arr.get('Terminal', 'N/A')} · Gate {arr.get('Gate', 'N/A')}")
                st.write(f"🕓 {arr.get('Scheduled', 'N/A')}")
            else:
                st.write("—")

        if not top and not dep and not arr:
            st.markdown(entry)


def parse_hotel_block(text: str) -> Dict[str, Any]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return {"name": "Hotel", "address": "", "tags": []}

    name = re.sub(r"^\d+\.\s*", "", lines[0])
    address = ""
    tags: List[str] = []

    for line in lines[1:]:
        low = line.lower()
        if low.startswith("address:"):
            address = line.split(":", 1)[1].strip()
        elif low.startswith("categories:"):
            raw_tags = [t.strip() for t in line.split(":", 1)[1].split(",")]
            tags = [t for t in raw_tags if t not in ("accommodation", "accommodation.hotel") and t]

    return {"name": name, "address": address, "tags": tags}


def render_hotel_entry(entry: str, idx: int):
    parsed = parse_hotel_block(entry)

    with st.container(border=True):
        st.markdown(f"**🏨 {idx}. {parsed['name']}**")
        if parsed["address"]:
            st.write(f"📍 {parsed['address']}")
        if parsed["tags"]:
            st.caption(" · ".join(parsed["tags"]))


if run_btn:
    if not prompt.strip():
        st.warning("Please enter a travel request.")
        st.stop()

    run_logs: List[str] = []
    status = st.status("Running multi-agent workflow…", expanded=True)

    # FIX: the backend already streams individual LLM tokens per node
    # (see stream_travel_agent in agent.py), but this file previously only
    # handled "node" and "final" events and dropped every "token" event on
    # the floor — so the UI just showed a spinner until the whole run
    # finished. This placeholder now renders the final_agent's answer live,
    # token by token, as it streams in.
    live_placeholder = st.empty()
    node_tokens: Dict[str, str] = {}

    final_payload: Dict[str, Any] = {}
    error_payload: Optional[Dict[str, Any]] = None

    try:
        with requests.post(
            STREAM_URL,
            json={
                "message": prompt,
                "thread_id": st.session_state.thread_id
            },
            timeout=180,
            stream=True
        ) as response:

            if response.status_code != 200:
                try:
                    err = response.json()
                    error_payload = {"error": err.get("error", f"Backend error ({response.status_code})")}
                except ValueError:
                    error_payload = {"error": f"Backend error ({response.status_code})"}
            else:
                for raw_line in response.iter_lines(decode_unicode=True):
                    if not raw_line:
                        continue

                    try:
                        event = json.loads(raw_line)
                    except json.JSONDecodeError:
                        continue

                    event_type = event.get("type")

                    if event_type == "node":
                        node_name = event.get("node", "")
                        label = NODE_LABELS.get(node_name, f"Running: {node_name}")
                        status.write(f"➡️ {label}")
                        run_logs.append(f"[node] {node_name}")

                    elif event_type == "token":
                        node_name = event.get("node") or "unknown"
                        content = event.get("content", "")
                        node_tokens[node_name] = node_tokens.get(node_name, "") + content

                        if node_name == LIVE_TEXT_NODE:
                            live_placeholder.markdown(node_tokens[node_name])

                    elif event_type == "final":
                        final_payload = event
                        run_logs.append("[final] received final state")

                    elif event_type == "error":
                        error_payload = event
                        run_logs.append(f"[error] {event.get('error')}")

    except requests.exceptions.RequestException as e:
        error_payload = {"error": f"Backend Connection Error: {e}"}

    # Once the run is done, hand off from the live-streaming placeholder to
    # the normal Trip Plan tab below — clear it so the answer isn't shown
    # twice.
    live_placeholder.empty()

    # Token events are high-volume; log a summary instead of one line per
    # token so the Logs tab stays readable.
    for node_name, text in node_tokens.items():
        run_logs.append(f"[tokens] {node_name}: {len(text)} chars streamed")

    st.session_state.logs.extend(run_logs)

    if error_payload:
        status.update(label="❌ Failed", state="error", expanded=True)
        st.error(error_payload.get("error", "Unknown error"))
    elif final_payload:
        status.update(label="✅ Done", state="complete", expanded=False)
        st.session_state.thread_id = final_payload.get("thread_id")
        st.session_state.last_out = final_payload
        st.session_state.sessions_cache = fetch_sessions()
        st.success("Trip Generated!")
    else:
        status.update(label="⚠️ No result", state="error", expanded=True)
        st.warning("The backend closed the stream without returning a result.")

out = st.session_state.last_out

with tab_plan:
    st.subheader("Trip Plan")
    if out:
        st.markdown(out.get("answer") or "No itinerary generated.")
        st.divider()
        st.metric(label="🤖 LLM Calls", value=out.get("llm_calls", 0))
    else:
        st.info("Enter a travel request and click **Generate Plan**.")

with tab_flights:
    st.subheader("Flights")
    if out:
        entries = normalize_to_entries(out.get("flight_results"))
        if entries:
            for i, entry in enumerate(entries, start=1):
                render_flight_entry(entry, i)
        else:
            st.info("No live flight data available.")
    else:
        st.info("No run yet.")

with tab_hotels:
    st.subheader("Hotels")
    if out:
        entries = normalize_to_entries(out.get("hotel_results"))
        if entries:
            for i, entry in enumerate(entries, start=1):
                render_hotel_entry(entry, i)
        else:
            st.info("No hotel data available.")
    else:
        st.info("No run yet.")

with tab_weather:
    st.subheader("Weather & Currency")
    if out:
        weather = out.get("weather_results")
        currency = out.get("currency_results")

        if weather:
            st.markdown("**Weather**")
            st.write(weather)
        else:
            st.info("No weather data available.")

        st.divider()

        if currency:
            st.markdown("**Currency**")
            st.write(currency)
        else:
            st.info("No currency data available.")
    else:
        st.info("No run yet.")

with tab_logs:
    st.subheader("Logs")
    st.text_area(
        "Event log",
        value="\n".join(st.session_state.logs[-200:]),
        height=520
    )