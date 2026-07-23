import os
import certifi
from langchain_openai import ChatOpenAI
from tools.weather_tool import get_weather
from tools.maps_tool import search_places
from tools.currency_tool import convert_currency
from dotenv import load_dotenv

load_dotenv()

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

from typing import TypedDict, Annotated
import operator
import uuid

from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import (
    AnyMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
)
from tools.tavily_tool import tavily_search
from tools.flight_tool import search_flights


def get_database_url():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError(
            "DATABASE_URL is missing. Please add your Render PostgreSQL External Database URL to .env"
        )

    if "sslmode=" not in database_url:
        separator = "&" if "?" in database_url else "?"
        database_url = f"{database_url}{separator}sslmode=require"

    return database_url


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is missing. Please add it to your .env file.")


# =========================
# LLM
# =========================

llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=OPENAI_API_KEY,
    streaming=True
)


# =========================
# State
# =========================
class TravelState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    user_query: str
    destination: str
    flight_results: str
    hotel_results: str
    weather_results: str
    currency_results: str
    itinerary: str
    llm_calls: int


# =========================
# Shared helper
# =========================
# Marker used to join separate flights/hotels in flight_results and
# hotel_results. It must be something that can never appear inside real
# flight/hotel text, so downstream consumers can split on it unambiguously
# instead of guessing based on blank lines (see flight_agent/hotel_agent).
LIST_ENTRY_SEPARATOR = "\n\n@@@ENTRY@@@\n\n"


def _for_llm(text: str) -> str:
    """Swap the entry marker back to a plain blank line before handing
    flight/hotel text to the LLM — the marker is only meaningful to the
    frontend's parser, not something the model needs to see."""
    return (text or "").replace(LIST_ENTRY_SEPARATOR, "\n\n")


def extract_destination(query: str) -> str:
    """
    Pulls the destination out of a query like "flights from Delhi to Tokyo".
    Falls back to the full query if there's no explicit "... to <place>".
    """
    if " to " in query.lower():
        return query.lower().split(" to ")[-1].strip()
    return query.strip()


# =========================
# Flight Agent
# =========================

def flight_agent(state: TravelState):
    query = state["user_query"]

    flight_data = search_flights(query)

    if flight_data:
    
        flight_results = LIST_ENTRY_SEPARATOR.join(flight_data)
    else:
        flight_results = "No live flight data available for this route."

    return {
        "flight_results": flight_results,
        "messages": [
            AIMessage(content="Flight results fetched.")
        ],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


# =========================
# Hotel Agent
# =========================

def hotel_agent(state: TravelState):
    destination = extract_destination(state["user_query"])

    hotel_data = search_places("accommodation.hotel", destination)

    if hotel_data:
        hotel_results = LIST_ENTRY_SEPARATOR.join(hotel_data)
    else:
        hotel_results = f"No hotels found for {destination}."

    return {
        "destination": destination,
        "hotel_results": hotel_results,
        "messages": [
            AIMessage(content="Hotel information fetched.")
        ],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


# =========================
# Weather Agent
# =========================

def weather_agent(state: TravelState):
    destination = state.get("destination") or extract_destination(state["user_query"])

    weather = get_weather(destination)

    return {
        "weather_results": weather,
        "messages": [
            AIMessage(content="Weather fetched.")
        ],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


# =========================
# Currency Agent
# =========================
def currency_agent(state: TravelState):
    try:
        result = convert_currency(1, "INR", "USD")
        currency_results = (
            f"{result['amount']} {result['from_currency']} = "
            f"{result['converted_amount']} {result['to_currency']} "
            f"(rate: {result['exchange_rate']})"
        )
    except Exception:
        currency_results = (
            "Live currency conversion is temporarily unavailable. "
            "Please check current INR-USD exchange rates separately before booking."
        )

    return {
        "currency_results": currency_results,
        "messages": [
            AIMessage(content="Currency fetched.")
        ],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


# =========================
# Itinerary Agent
# =========================


_NO_FLIGHT_MARKERS = ("no live flight data",)
_NO_HOTEL_MARKERS = ("no hotels found",)


def _is_missing(text: str, markers: tuple[str, ...]) -> bool:
    lowered = (text or "").lower()
    return any(marker in lowered for marker in markers)


def itinerary_agent(state: TravelState):
    flights_missing = _is_missing(state["flight_results"], _NO_FLIGHT_MARKERS)
    hotels_missing = _is_missing(state["hotel_results"], _NO_HOTEL_MARKERS)

    prompt = f"""
Create a complete travel itinerary.

User Query:
{state['user_query']}

Flight Results:
{_for_llm(state['flight_results'])}

Hotel Results:
{_for_llm(state['hotel_results'])}

Weather:
{state['weather_results']}

Currency:
{state['currency_results']}

Important rules:
- Only reference specific flight numbers, airlines, prices, or hotel names if
  they are literally present in the Flight Results / Hotel Results above.
- {"Flight data was NOT found for this route. Say so plainly and suggest checking a booking site (e.g. Google Flights, Skyscanner) instead of inventing flight details." if flights_missing else "Real flight data is available above — use it."}
- {"Hotel data was NOT found for this destination. Say so plainly and suggest checking a booking site (e.g. Booking.com, Google Hotels) instead of inventing hotel names." if hotels_missing else "Real hotel data is available above — use it."}
- Make the itinerary practical, budget-aware, and easy to follow.
"""

    response = llm.invoke([
        SystemMessage(content="You are an expert travel planner who never fabricates prices, flight numbers, or hotel names that aren't in the provided data."),
        HumanMessage(content=prompt)
    ])

    return {
        "itinerary": response.content,
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


# =========================
# Final Response Agent
# =========================

def final_agent(state: TravelState):
    flights_missing = _is_missing(state["flight_results"], _NO_FLIGHT_MARKERS)
    hotels_missing = _is_missing(state["hotel_results"], _NO_HOTEL_MARKERS)

    final_prompt = f"""
Generate the final travel response for the user.

User Request:
{state['user_query']}

Flights:
{_for_llm(state['flight_results'])}

Hotels:
{_for_llm(state['hotel_results'])}

Weather:
{state['weather_results']}

make sure currency should be in indian format i.e INR
Currency:
{state['currency_results']}

Itinerary:
{state['itinerary']}

Format the final answer beautifully using these sections:

1. Trip Summary
2. Flight Information
3. Hotel Suggestions
4. Day-by-Day Itinerary
5. Estimated Budget
6. Final Recommendations

Important:
- Be clear and practical.
- Mention that live flight API may not provide ticket prices if pricing is unavailable.
- Do NOT invent specific flight numbers, airline names, prices, or hotel names
  that are not present in the Flights / Hotels sections above.
- {"No live flight data was found — the Flight Information section must say this explicitly and point the user to a booking site, not present made-up options." if flights_missing else ""}
- {"No live hotel data was found — the Hotel Suggestions section must say this explicitly and point the user to a booking site, not present made-up options." if hotels_missing else ""}
- Keep the response useful for real travel planning.
"""

    response = llm.invoke([
        SystemMessage(content="You are a professional AI travel booking assistant who never fabricates data that wasn't actually returned by the booking tools."),
        HumanMessage(content=final_prompt)
    ])

    return {
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


# =========================
# Build Graph
# =========================

graph = StateGraph(TravelState)

graph.add_node("flight_agent", flight_agent)
graph.add_node("hotel_agent", hotel_agent)
graph.add_node("itinerary_agent", itinerary_agent)
graph.add_node("final_agent", final_agent)
graph.add_node("weather_agent", weather_agent)
graph.add_node("currency_agent", currency_agent)

graph.add_edge(START, "flight_agent")
graph.add_edge("flight_agent", "hotel_agent")
graph.add_edge("hotel_agent", "weather_agent")
graph.add_edge("weather_agent", "currency_agent")
graph.add_edge("currency_agent", "itinerary_agent")
graph.add_edge("itinerary_agent", "final_agent")
graph.add_edge("final_agent", END)


# =========================
# PostgreSQL connection pool
# =========================
DATABASE_URL = get_database_url()

pool = ConnectionPool(
    conninfo=DATABASE_URL,
    max_size=20,
    kwargs={
        "autocommit": True,
        "row_factory": dict_row,
    },
)

# PostgresSaver accepts a pool directly — this is the documented pattern
# for using it safely across concurrent requests.
checkpointer = PostgresSaver(pool)
checkpointer.setup()

travel_graph = graph.compile(checkpointer=checkpointer)


def close_pool():
    """Call this on application shutdown to release DB connections cleanly."""
    pool.close()


# =========================
# Lightweight thread metadata table
#
# Stores just enough to render the sidebar instantly: title (set once,
# from that thread's single query) and updated_at (for ordering).
# Pruned down to the 10 most recent rows on every write so the
# sidebar query stays a fixed, tiny cost forever.
# =========================
with pool.connection() as _conn:
    with _conn.cursor() as _cur:
        _cur.execute("""
            CREATE TABLE IF NOT EXISTS thread_meta (
                thread_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        _cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_thread_meta_updated_at
            ON thread_meta (updated_at DESC)
        """)

MAX_HISTORY = 10


def _make_title(text: str | None, max_len: int = 45) -> str:
    """
    Turns a user query into a short sidebar-friendly title: collapses
    newlines/extra whitespace, then truncates at a word boundary near
    max_len instead of chopping mid-word or showing the full prompt.
    """
    if not text:
        return "Untitled chat"

    cleaned = " ".join(text.split())
    if len(cleaned) <= max_len:
        return cleaned

    truncated = cleaned[:max_len].rsplit(" ", 1)[0]
    return (truncated or cleaned[:max_len]) + "…"


def _record_thread_meta(thread_id: str, user_input: str):
    """
    Inserts one thread_meta row per thread, then prunes the table down
    to the MAX_HISTORY most recently updated rows so history never
    grows unbounded and the sidebar query stays fast forever.

    """
    title = _make_title(user_input)
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO thread_meta (thread_id, title, updated_at)
                VALUES (%s, %s, now())
                ON CONFLICT (thread_id) DO UPDATE
                    SET updated_at = EXCLUDED.updated_at
                """,
                (thread_id, title)
            )
            cur.execute(
                """
                DELETE FROM thread_meta
                WHERE thread_id NOT IN (
                    SELECT thread_id FROM thread_meta
                    ORDER BY updated_at DESC
                    LIMIT %s
                )
                """,
                (MAX_HISTORY,)
            )


# =========================
# Function for FastAPI (blocking — single response)
#
# Every call is an independent trip query — the itinerary/final
# agents only look at THIS run's state, never earlier turns, so each
# UI-triggered generation gets its own fresh thread_id. This is what
# keeps one sidebar entry = one query (no blended flights/hotels) and
# keeps each thread's message history small (fast checkpoint writes).
# =========================

def run_travel_agent(user_input: str, thread_id: str | None = None):
    if not thread_id:
        thread_id = f"user_{uuid.uuid4().hex}"

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    _record_thread_meta(thread_id, user_input)

    result = travel_graph.invoke(
        {
            "messages": [
                HumanMessage(content=user_input)
            ],
            "user_query": user_input,
            "destination": "",
            "flight_results": "",
            "hotel_results": "",
            "weather_results": "",
            "currency_results": "",
            "itinerary": "",
            "llm_calls": 0
        },
        config=config
    )

    final_answer = result["messages"][-1].content

    return {
        "thread_id": thread_id,
        "answer": final_answer,
        "flight_results": result.get("flight_results"),
        "hotel_results": result.get("hotel_results"),
        "weather_results": result.get("weather_results"),
        "currency_results": result.get("currency_results"),
        "itinerary": result.get("itinerary"),
        "llm_calls": result.get("llm_calls"),
    }


# =========================
# Function for FastAPI (streaming — live per-node progress + live tokens)
# =========================

def stream_travel_agent(user_input: str, thread_id: str | None = None):
    """
    Generator version of run_travel_agent().

    Yields dicts as the graph executes:
      {"type": "node", "node": "<node_name>"}
      {"type": "token", "node": "<node_name>", "content": "<text chunk>"}
      {"type": "final", "thread_id": ..., "answer": ..., "flight_results": ...,
       "hotel_results": ..., "weather_results": ..., "currency_results": ...,
       "itinerary": ..., "llm_calls": ...}
    """
    if not thread_id:
        thread_id = f"user_{uuid.uuid4().hex}"

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    _record_thread_meta(thread_id, user_input)

    inputs = {
        "messages": [
            HumanMessage(content=user_input)
        ],
        "user_query": user_input,
        "destination": "",
        "flight_results": "",
        "hotel_results": "",
        "weather_results": "",
        "currency_results": "",
        "itinerary": "",
        "llm_calls": 0
    }

    for mode, payload in travel_graph.stream(
        inputs,
        config=config,
        stream_mode=["updates", "messages"]
    ):
        if mode == "updates":
            for node_name in payload.keys():
                yield {"type": "node", "node": node_name}

        elif mode == "messages":
            message_chunk, metadata = payload
            content = getattr(message_chunk, "content", "") or ""
            if content:
                yield {
                    "type": "token",
                    "node": metadata.get("langgraph_node"),
                    "content": content,
                }

    snapshot = travel_graph.get_state(config)
    values = snapshot.values

    final_answer = values["messages"][-1].content

    yield {
        "type": "final",
        "thread_id": thread_id,
        "answer": final_answer,
        "flight_results": values.get("flight_results"),
        "hotel_results": values.get("hotel_results"),
        "weather_results": values.get("weather_results"),
        "currency_results": values.get("currency_results"),
        "itinerary": values.get("itinerary"),
        "llm_calls": values.get("llm_calls"),
    }


# =========================
# Chat history support (list past threads + replay one thread)
# =========================

def list_threads(limit: int = MAX_HISTORY):
    """
    Returns [{"thread_id": ..., "title": ...}, ...], newest first.
    Reads only from thread_meta — one fast indexed query, capped at
    `limit` rows (defaults to MAX_HISTORY, kept in sync with the
    pruning in _record_thread_meta).
    """
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT thread_id, title FROM thread_meta ORDER BY updated_at DESC LIMIT %s",
                (limit,)
            )
            rows = cur.fetchall()

    return [{"thread_id": r["thread_id"], "title": r["title"]} for r in rows]


def get_thread_detail(thread_id: str):
    """
    Replays one thread's full checkpoint state for the Streamlit sidebar.
    Returns None if the thread doesn't exist.
    """
    config = {"configurable": {"thread_id": thread_id}}

    try:
        snapshot = travel_graph.get_state(config)
    except Exception:
        return None

    if not snapshot or not snapshot.values:
        return None

    values = snapshot.values
    messages = values.get("messages", [])

    runs = []
    current = None
    for m in messages:
        if isinstance(m, HumanMessage):
            if current:
                runs.append(current)
            current = {"user": m.content, "candidates": []}
        elif current is not None:
            content = getattr(m, "content", "")
            if content:
                current["candidates"].append(content)
    if current:
        runs.append(current)

    turns = [
        {
            "user": r["user"],
            "assistant": r["candidates"][-1] if r["candidates"] else ""
        }
        for r in runs
    ]

    return {
        "turns": turns,
        "flight_results": values.get("flight_results"),
        "hotel_results": values.get("hotel_results"),
        "weather_results": values.get("weather_results"),
        "currency_results": values.get("currency_results"),
        "llm_calls": values.get("llm_calls", 0),
    }