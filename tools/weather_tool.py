import os
import requests
from dotenv import load_dotenv

from common.logger import get_logger
from common.custom_exceptions import CustomException

logger = get_logger(__name__)

load_dotenv()

API_KEY = os.getenv("WEATHER_API_KEY")
BASE_URL = "https://api.weatherapi.com/v1/current.json"
SEARCH_URL = "https://api.weatherapi.com/v1/search.json"

logger.info("Weather API configuration loaded.")


def _resolve_location(city: str) -> str:
    """
    current.json's own "q=<city name>" matching is fuzzy and, for city
    names that exist in more than one country (e.g. "Delhi" is also a
    small town in Ontario, Canada), it can silently resolve to the
    wrong one — which is exactly the "Delhi, Canada" bug.

    To avoid that, we first call the search/autocomplete endpoint,
    which returns every candidate match with its own lat/lon instead
    of picking one for us. We then choose the best candidate ourselves
    and query current.json using that exact lat/lon, so there's no
    ambiguity left for current.json to re-guess.

    Preference order:
      1. Exact (case-insensitive) name match located in India — this
         app is India-based, and most of these collisions involve an
         Indian city sharing a name with a much smaller town abroad.
      2. Any exact name match (first one search.json returns).
      3. Whatever search.json ranks first, if there's no exact match.
      4. The original bare city string, if the search call itself
         fails for any reason (network error, bad JSON, no key, etc.)
         — current.json will then fall back to its own default
         matching rather than the request failing outright.
    """
    try:
        resp = requests.get(
            SEARCH_URL,
            params={"key": API_KEY, "q": city},
            timeout=20
        )
        resp.raise_for_status()
        candidates = resp.json()
    except (requests.exceptions.RequestException, ValueError):
        logger.warning(f"Location search failed for '{city}'; falling back to raw query.")
        return city

    if not isinstance(candidates, list) or not candidates:
        return city

    exact_matches = [
        c for c in candidates
        if str(c.get("name", "")).strip().lower() == city.strip().lower()
    ]
    pool = exact_matches or candidates

    india_match = next((c for c in pool if c.get("country") == "India"), None)
    best = india_match or pool[0]

    lat, lon = best.get("lat"), best.get("lon")
    if lat is None or lon is None:
        return city

    logger.info(
        f"Resolved '{city}' -> {best.get('name')}, {best.get('region')}, "
        f"{best.get('country')} ({lat},{lon})"
    )
    return f"{lat},{lon}"


def get_weather(city: str) -> str:
    try:
        logger.info(f"Fetching weather data for city: {city}")

        if not API_KEY:
            logger.error("Weather API key not found.")
            raise CustomException(
                "Weather API key not found. Please add WEATHER_API_KEY to your .env file."
            )

        resolved_location = _resolve_location(city)

        params = {
            "key": API_KEY,
            "q": resolved_location,
            "aqi": "yes"
        }

        response = requests.get(BASE_URL, params=params, timeout=20)

        try:
            data = response.json()
        except ValueError as e:
            logger.exception("Weather API returned invalid JSON.")
            raise CustomException("Weather API returned invalid JSON.", e)

        # Check for WeatherAPI's own error payload BEFORE raise_for_status(),
        # since WeatherAPI returns 4xx codes alongside a JSON {"error": {...}}
        # body — raise_for_status() would otherwise swallow that message
        # inside a generic requests.HTTPError.
        if "error" in data:
            logger.error(f"Weather API Error: {data['error']['message']}")
            raise CustomException(data["error"]["message"])

        response.raise_for_status()

        location = data["location"]
        current = data["current"]

        logger.info(f"Weather data fetched successfully for {location['name']}.")

        return f"""
Weather Information

City: {location['name']}
Country: {location['country']}

Temperature: {current['temp_c']} °C
Feels Like: {current['feelslike_c']} °C
Condition: {current['condition']['text']}

Humidity: {current['humidity']}%
Wind Speed: {current['wind_kph']} km/h
Pressure: {current['pressure_mb']} mb
Visibility: {current['vis_km']} km
UV Index: {current['uv']}

Local Time: {location['localtime']}
""".strip()

    except requests.exceptions.RequestException as e:
        logger.exception("Weather API request failed.")
        raise CustomException("Weather API request failed.", e)

    except CustomException:
        raise

    except Exception as e:
        logger.exception("Unexpected error while fetching weather.")
        raise CustomException("Failed to fetch weather information.", e)


# if __name__ == "__main__":
#     try:
#         print(get_weather("Delhi"))
#     except CustomException as e:
#         logger.exception(f"CustomException occurred: {str(e)}")