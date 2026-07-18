import os
import requests
from dotenv import load_dotenv

from common.logger import get_logger
from common.custom_exceptions import CustomException

logger = get_logger(__name__)

load_dotenv()

API_KEY = os.getenv("GEOAPIFY_API_KEY")

GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"
PLACES_URL = "https://api.geoapify.com/v2/places"

DEFAULT_CITY = "Delhi"

logger.info("Geoapify configuration loaded.")


def get_place_id(city: str):
    try:
        logger.info(f"Fetching place ID for city: {city}")

        params = {
            "text": city,
            "limit": 1,
            "apiKey": API_KEY
        }

        response = requests.get(GEOCODE_URL, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        features = data.get("features", [])

        if not features:
            logger.warning(f"No place ID found for city: {city}")
            return None

        logger.info(f"Successfully retrieved place ID for {city}")
        return features[0]["properties"]["place_id"]

    except requests.exceptions.RequestException as e:
        logger.exception("Failed to fetch place ID from Geoapify.")
        raise CustomException("Failed to fetch place ID.", e)

    except Exception as e:
        logger.exception("Unexpected error while fetching place ID.")
        raise CustomException("Unexpected error while fetching place ID.", e)


def search_places(category: str, city: str = DEFAULT_CITY, limit: int = 5):
    try:
        logger.info(
            f"Searching places | Category: {category} | City: {city} | Limit: {limit}"
        )

        if not API_KEY:
            logger.error("Geoapify API key not found.")
            raise CustomException(
                "Geoapify API key not found. Please add GEOAPIFY_API_KEY to your .env file."
            )

        place_id = get_place_id(city)
 
        if place_id is None:
            logger.warning(f"Could not find city: {city}")
            return []

        # if place_id is None:
        #     logger.warning(f"Could not find city: {city}")
        #     return f"Could not find {city}"

        params = {
            "categories": category,
            "filter": f"place:{place_id}",
            "limit": limit,
            "lang": "en",
            "apiKey": API_KEY
        }

        response = requests.get(PLACES_URL, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        places = data.get("features", [])

        
        if not places:
            logger.warning(f"No places found in {city}")
            return []

        results = []

        for i, place in enumerate(places, 1):
            prop = place.get("properties", {})

            name = (
                prop.get("name")
                or prop.get("address_line1")
                or "Unknown"
            )

            address = prop.get("formatted", "Unknown")
            categories = ", ".join(prop.get("categories", []))

            results.append(
                f"""
{i}. {name}

Address: {address}

Categories: {categories}
""".strip()
            )

        logger.info(f"Successfully found {len(results)} places in {city}")

        results

        # return "\n\n".join(results)

    except requests.exceptions.RequestException as e:
        logger.exception("Geoapify request failed.")
        raise CustomException("Geoapify request failed.", e)

    except CustomException:
        raise

    except Exception as e:
        logger.exception("Unexpected error while searching places.")
        raise CustomException("Failed to search places.", e)


if __name__ == "__main__":
    try:
        print("=" * 70)
        print("Hotels in Delhi")
        print("=" * 70)
        print(search_places("accommodation.hotel"))

        print("\n")

        print("=" * 70)
        print("Restaurants in Paris")
        print("=" * 70)
        print(search_places("catering.restaurant", "Paris"))

        print("\n")

        print("=" * 70)
        print("Museums in Dubai")
        print("=" * 70)
        print(search_places("entertainment.museum", "Dubai"))

    except CustomException as e:
        logger.exception(f"CustomException occurred: {str(e)}")