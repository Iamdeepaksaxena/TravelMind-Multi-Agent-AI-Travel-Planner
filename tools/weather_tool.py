import os
import requests
from dotenv import load_dotenv

from common.logger import get_logger
from common.custom_exceptions import CustomException

logger = get_logger(__name__)

load_dotenv()

API_KEY = os.getenv("WEATHER_API_KEY")
BASE_URL = "http://api.weatherapi.com/v1/current.json"

logger.info("Weather API configuration loaded.")


def get_weather(city: str) -> str:
    try:
        logger.info(f"Fetching weather data for city: {city}")

        if not API_KEY:
            logger.error("Weather API key not found.")
            raise CustomException(
                "Weather API key not found. Please add WEATHER_API_KEY to your .env file."
            )

        params = {
            "key": API_KEY,
            "q": city,
            "aqi": "yes"
        }

        response = requests.get(BASE_URL, params=params, timeout=20)
        response.raise_for_status()

        try:
            data = response.json()
        except ValueError as e:
            logger.exception("Weather API returned invalid JSON.")
            raise CustomException("Weather API returned invalid JSON.", e)

        if "error" in data:
            logger.error(f"Weather API Error: {data['error']['message']}")
            raise CustomException(data["error"]["message"])

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
#         print(get_weather("Tokyo"))
#     except CustomException as e:
#         logger.exception(f"CustomException occurred: {str(e)}")