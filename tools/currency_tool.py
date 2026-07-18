import requests
from common.logger import get_logger
from common.custom_exceptions import CustomException

# Initialize logger
logger = get_logger(__name__)

BASE_URL = "https://open.er-api.com/v6/latest"


def convert_currency(amount: float, from_currency: str, to_currency: str):
    """
    Convert currency using ExchangeRate-API.

    Returns:
    {
        "amount": 100,
        "from_currency": "USD",
        "to_currency": "INR",
        "exchange_rate": 85.62,
        "converted_amount": 8562.00
    }
    """

    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    logger.info(
        f"Converting {amount} {from_currency} -> {to_currency}"
    )

    try:
        url = f"{BASE_URL}/{from_currency}"

        response = requests.get(url, timeout=20)
        response.raise_for_status()

        data = response.json()

    except requests.exceptions.RequestException as e:
        logger.exception("Currency API request failed.")
        raise CustomException("Currency API request failed", e)

    except ValueError as e:
        logger.exception("Invalid JSON received from Currency API.")
        raise CustomException("Invalid JSON received", e)

    if data.get("result") != "success":
        logger.error("Currency API returned an unsuccessful response.")
        raise CustomException("Currency conversion failed.")

    rates = data.get("rates", {})

    if to_currency not in rates:
        logger.error(f"Currency '{to_currency}' not found in exchange rates.")
        raise CustomException(f"Unsupported currency: {to_currency}")

    exchange_rate = rates[to_currency]
    converted_amount = round(amount * exchange_rate, 2)

    logger.info(
        f"Conversion successful: {amount} {from_currency} = "
        f"{converted_amount} {to_currency}"
    )

    return {
        "amount": amount,
        "from_currency": from_currency,
        "to_currency": to_currency,
        "exchange_rate": round(exchange_rate, 4),
        "converted_amount": converted_amount
    }


# if __name__ == "__main__":
#     try:

#         print(convert_currency(1000, "INR", "JPY"))
#         print()

#         print(convert_currency(500, "USD", "EUR"))
#         print()

#         print(convert_currency(100, "GBP", "INR"))

#     except CustomException as e:
#         logger.exception(str(e))