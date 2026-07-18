import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000/api/travel"

st.set_page_config(
    page_title="TripMind AI-Agent",
    page_icon="✈️",
    layout="wide"
)

st.title("🌍 TripMind AI-Agent")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = None

prompt = st.text_area(
    "Where would you like to travel?",
    height=120,
    placeholder="Example: Plan a 5-day trip to Dubai under ₹80,000"
)

if st.button("Generate Plan"):

    if not prompt.strip():
        st.warning("Please enter a travel request.")
        st.stop()

    with st.spinner("Planning your trip..."):

        try:
            response = requests.post(
                API_URL,
                json={
                    "message": prompt,
                    "thread_id": st.session_state.thread_id
                },
                timeout=120
            )

        except requests.exceptions.RequestException as e:
            st.error(f"Backend Connection Error:\n{e}")
            st.stop()

    if response.status_code != 200:
        st.error(f"Backend Error ({response.status_code})")
        st.stop()

    data = response.json()

    if not data.get("success", False):
        st.error(data.get("error", "Unknown Error"))
        st.stop()

    st.session_state.thread_id = data["thread_id"]

    st.success("Trip Generated")

    # -------------------------------
    # Final Trip Plan
    # -------------------------------
    st.subheader("✈️ Trip Plan")
    st.markdown(data.get("answer", "No itinerary generated."))

    # -------------------------------
    # Flight Results
    # -------------------------------
    st.subheader("🛫 Flights")

    flights = data.get("flight_results")

    if flights:

        if isinstance(flights, list):
            for i, flight in enumerate(flights, start=1):
                st.markdown(f"### Flight {i}")
                st.write(flight)

        elif isinstance(flights, dict):
            st.json(flights)

        else:
            st.write(flights)

    else:
        st.info("No live flight data available.")

    # -------------------------------
    # Hotel Results
    # -------------------------------
    st.subheader("🏨 Hotels")

    hotels = data.get("hotel_results")

    if hotels:

        if isinstance(hotels, list):
            for i, hotel in enumerate(hotels, start=1):
                st.markdown(f"### Hotel {i}")
                st.write(hotel)

        elif isinstance(hotels, dict):
            st.json(hotels)

        else:
            st.write(hotels)

    else:
        st.info("No hotel data available.")

    # -------------------------------
    # Weather
    # -------------------------------
    weather = data.get("weather_results")

    if weather:
        st.subheader("🌤️ Weather")
        st.write(weather)

    # -------------------------------
    # Currency
    # -------------------------------
    currency = data.get("currency_results")

    if currency:
        st.subheader("💱 Currency")
        st.write(currency)

    # -------------------------------
    # LLM Calls
    # -------------------------------
    st.metric(
        label="🤖 LLM Calls",
        value=data.get("llm_calls", 0)
    )