import os
import time
import requests
from dotenv import load_dotenv

from common.logger import get_logger
from common.custom_exceptions import CustomException

logger = get_logger(__name__)

load_dotenv()

BASE_URL = "https://open.er-api.com/v6/latest"

logger.info("Currency API configuration loaded.")

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2  # 2s, 4s, 8s between attempts
REQUEST_TIMEOUT = 30


def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                f"Fetching exchange rate {from_currency}->{to_currency} "
                f"(attempt {attempt}/{MAX_RETRIES})"
            )

            response = requests.get(
                f"{BASE_URL}/{from_currency}",
                timeout=REQUEST_TIMEOUT
            )

            try:
                data = response.json()
            except ValueError as e:
                raise CustomException("Currency API returned invalid JSON.", e)

            if data.get("result") != "success":
                raise CustomException(
                    f"Currency API error: {data.get('error-type', 'unknown error')}"
                )

            response.raise_for_status()

            rates = data.get("rates", {})
            if to_currency not in rates:
                raise CustomException(
                    f"Currency '{to_currency}' not found in exchange rate response."
                )

            exchange_rate = rates[to_currency]
            converted_amount = round(amount * exchange_rate, 4)

            logger.info(
                f"Converted {amount} {from_currency} -> "
                f"{converted_amount} {to_currency} (rate: {exchange_rate})"
            )

            return {
                "amount": amount,
                "from_currency": from_currency,
                "to_currency": to_currency,
                "exchange_rate": exchange_rate,
                "converted_amount": converted_amount,
            }

        except requests.exceptions.RequestException as e:
            last_error = e
            logger.warning(
                f"Currency API request failed on attempt {attempt}/{MAX_RETRIES}: {e}"
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)

        except CustomException:
            # Don't retry on a well-formed API error response (e.g. bad
            # currency code) — retrying won't fix that, only a network
            # failure benefits from another attempt.
            raise

    # Exhausted all retries on network-level failures.
    logger.exception("Currency API request failed after all retries.")
    raise CustomException("Currency API request failed after retries.", last_error)


# if __name__ == "__main__":
#     try:
#         print(convert_currency(1, "INR", "USD"))
#     except CustomException as e:
#         logger.exception(f"CustomException occurred: {str(e)}")