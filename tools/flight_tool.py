import os
import re
import certifi
import airportsdata
import pycountry
import requests
from dotenv import load_dotenv

from common.logger import get_logger
from common.custom_exceptions import CustomException

# Initialize logger
logger = get_logger(__name__)

load_dotenv()

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

API_KEY = os.getenv("AVIATIONSTACK_API_KEY")

# Default origin when user says only destination, e.g. "Japan trip"
# default location is Delhi
DEFAULT_ORIGIN_IATA = os.getenv("DEFAULT_ORIGIN_IATA", "DEL")

BASE_URL = "https://api.aviationstack.com/v1/flights"

try:
    logger.info("Loading airport IATA data...")
    AIRPORTS = airportsdata.load("IATA")
except Exception as e:
    logger.error("Failed to load airports data")
    raise CustomException("Failed to load airports data", e)

COUNTRY_ALIASES = {
    # North America
    "usa": "US", "u.s.a": "US", "u.s.": "US", "us": "US",
    "america": "US", "united states": "US", "united states of america": "US",
    "canada": "CA",
    "mexico": "MX",

    # UK / Europe
    "uk": "GB", "u.k.": "GB", "britain": "GB", "england": "GB",
    "great britain": "GB", "united kingdom": "GB",
    "germany": "DE", "deutschland": "DE",
    "france": "FR",
    "italy": "IT",
    "spain": "ES",
    "portugal": "PT",
    "netherlands": "NL", "holland": "NL",
    "belgium": "BE",
    "switzerland": "CH",
    "austria": "AT",
    "ireland": "IE",
    "sweden": "SE",
    "norway": "NO",
    "denmark": "DK",
    "finland": "FI",
    "iceland": "IS",
    "poland": "PL",
    "greece": "GR",
    "czech republic": "CZ", "czechia": "CZ",
    "hungary": "HU",
    "romania": "RO",
    "russia": "RU",
    "ukraine": "UA",

    # Middle East
    "uae": "AE", "dubai": "AE", "united arab emirates": "AE",
    "qatar": "QA",
    "saudi arabia": "SA", "ksa": "SA",
    "kuwait": "KW",
    "bahrain": "BH",
    "oman": "OM",
    "israel": "IL",
    "jordan": "JO",
    "lebanon": "LB",
    "iran": "IR",
    "iraq": "IQ",
    "turkey": "TR", "turkiye": "TR",
    "egypt": "EG",

    # South Asia
    "india": "IN", "bharat": "IN",
    "bangladesh": "BD",
    "nepal": "NP",
    "sri lanka": "LK", "ceylon": "LK",
    "pakistan": "PK",
    "bhutan": "BT",
    "maldives": "MV",
    "afghanistan": "AF",

    # East / Southeast Asia
    "japan": "JP",
    "china": "CN",
    "south korea": "KR", "korea": "KR",
    "north korea": "KP",
    "taiwan": "TW",
    "hong kong": "HK",
    "singapore": "SG",
    "malaysia": "MY",
    "thailand": "TH",
    "indonesia": "ID",
    "vietnam": "VN",
    "philippines": "PH",
    "cambodia": "KH",
    "laos": "LA",
    "myanmar": "MM", "burma": "MM",
    "mongolia": "MN",

    # Oceania
    "australia": "AU",
    "new zealand": "NZ",
    "fiji": "FJ",

    # Africa
    "south africa": "ZA",
    "nigeria": "NG",
    "kenya": "KE",
    "ethiopia": "ET",
    "morocco": "MA",
    "tanzania": "TZ",
    "ghana": "GH",
    "algeria": "DZ",
    "tunisia": "TN",
    "mauritius": "MU",
    "rwanda": "RW",
    "uganda": "UG",

    # South / Central America
    "brazil": "BR",
    "argentina": "AR",
    "chile": "CL",
    "colombia": "CO",
    "peru": "PE",
    "venezuela": "VE",
    "ecuador": "EC",
    "uruguay": "UY",
    "panama": "PA",
    "costa rica": "CR",
    "cuba": "CU",
    "jamaica": "JM",
    "dominican republic": "DO",
}

# Preferred main (usually largest international) airport for country-level search
COUNTRY_MAIN_AIRPORT = {
    # North America
    "US": "JFK",
    "CA": "YYZ",
    "MX": "MEX",

    # UK / Europe
    "GB": "LHR",
    "DE": "FRA",
    "FR": "CDG",
    "IT": "FCO",
    "ES": "MAD",
    "PT": "LIS",
    "NL": "AMS",
    "BE": "BRU",
    "CH": "ZRH",
    "AT": "VIE",
    "IE": "DUB",
    "SE": "ARN",
    "NO": "OSL",
    "DK": "CPH",
    "FI": "HEL",
    "IS": "KEF",
    "PL": "WAW",
    "GR": "ATH",
    "CZ": "PRG",
    "HU": "BUD",
    "RO": "OTP",
    "RU": "SVO",
    "UA": "KBP",

    # Middle East
    "AE": "DXB",
    "QA": "DOH",
    "SA": "JED",
    "KW": "KWI",
    "BH": "BAH",
    "OM": "MCT",
    "IL": "TLV",
    "JO": "AMM",
    "LB": "BEY",
    "IR": "IKA",
    "IQ": "BGW",
    "TR": "IST",
    "EG": "CAI",

    # South Asia
    "IN": "DEL",
    "BD": "DAC",
    "NP": "KTM",
    "LK": "CMB",
    "PK": "KHI",
    "BT": "PBH",
    "MV": "MLE",
    "AF": "KBL",

    # East / Southeast Asia
    "JP": "NRT",
    "CN": "PEK",
    "KR": "ICN",
    "KP": "FNJ",
    "TW": "TPE",
    "HK": "HKG",
    "SG": "SIN",
    "MY": "KUL",
    "TH": "BKK",
    "ID": "CGK",
    "VN": "SGN",
    "PH": "MNL",
    "KH": "PNH",
    "LA": "VTE",
    "MM": "RGN",
    "MN": "ULN",

    # Oceania
    "AU": "SYD",
    "NZ": "AKL",
    "FJ": "NAN",

    # Africa
    "ZA": "JNB",
    "NG": "LOS",
    "KE": "NBO",
    "ET": "ADD",
    "MA": "CMN",
    "TZ": "DAR",
    "GH": "ACC",
    "DZ": "ALG",
    "TN": "TUN",
    "MU": "MRU",
    "RW": "KGL",
    "UG": "EBB",

    # South / Central America
    "BR": "GRU",
    "AR": "EZE",
    "CL": "SCL",
    "CO": "BOG",
    "PE": "LIM",
    "VE": "CCS",
    "EC": "UIO",
    "UY": "MVD",
    "PA": "PTY",
    "CR": "SJO",
    "CU": "HAV",
    "JM": "KIN",
    "DO": "SDQ",
}

# Preferred main airport for city-level search.
# India is covered in depth (all major metros + state capitals + key
# tourist/business hubs), since it is the default region for this app.
CITY_MAIN_AIRPORT = {
    # --- India: metros ---
    "delhi": "DEL", "new delhi": "DEL",
    "mumbai": "BOM", "bombay": "BOM",
    "kolkata": "CCU", "calcutta": "CCU",
    "chennai": "MAA", "madras": "MAA",
    "bangalore": "BLR", "bengaluru": "BLR",
    "hyderabad": "HYD",

    # --- India: other major cities ---
    "pune": "PNQ",
    "ahmedabad": "AMD",
    "surat": "STV",
    "jaipur": "JAI",
    "lucknow": "LKO",
    "kanpur": "KNU",
    "nagpur": "NAG",
    "indore": "IDR",
    "bhopal": "BHO",
    "patna": "PAT",
    "vadodara": "BDQ", "baroda": "BDQ",
    "coimbatore": "CJB",
    "kochi": "COK", "cochin": "COK", "ernakulam": "COK",
    "thiruvananthapuram": "TRV", "trivandrum": "TRV",
    "kozhikode": "CCJ", "calicut": "CCJ",
    "guwahati": "GAU",
    "chandigarh": "IXC",
    "bhubaneswar": "BBI",
    "visakhapatnam": "VTZ", "vizag": "VTZ",
    "vijayawada": "VGA",
    "amritsar": "ATQ",
    "varanasi": "VNS", "banaras": "VNS",
    "ranchi": "IXR",
    "raipur": "RPR",
    "madurai": "IXM",
    "tiruchirappalli": "TRZ", "trichy": "TRZ",
    "mangalore": "IXE", "mangaluru": "IXE",
    "dehradun": "DED",
    "srinagar": "SXR",
    "jammu": "IXJ",
    "leh": "IXL",
    "udaipur": "UDR",
    "jodhpur": "JDH",
    "agra": "AGR",
    "gaya": "GAY",
    "imphal": "IMF",
    "agartala": "IXA",
    "port blair": "IXZ",
    "goa": "GOI", "panaji": "GOI", "dabolim": "GOI", "mopa": "GOX",
    "rajkot": "HSR",
    "aurangabad": "IXU",
    "gwalior": "GWL",
    "tirupati": "TIR",
    "pondicherry": "PNY", "puducherry": "PNY",
    "shimla": "SLV",

    # --- East / Southeast Asia ---
    "tokyo": "NRT",
    "osaka": "KIX",
    "kyoto": "KIX",
    "seoul": "ICN",
    "beijing": "PEK",
    "shanghai": "PVG",
    "hong kong": "HKG",
    "taipei": "TPE",
    "kuala lumpur": "KUL",
    "bangkok": "BKK",
    "phuket": "HKT",
    "jakarta": "CGK",
    "bali": "DPS", "denpasar": "DPS",
    "ho chi minh city": "SGN", "saigon": "SGN",
    "hanoi": "HAN",
    "manila": "MNL",

    # --- Middle East ---
    "dubai": "DXB",
    "abu dhabi": "AUH",
    "doha": "DOH",
    "riyadh": "RUH",
    "jeddah": "JED",
    "istanbul": "IST",
    "cairo": "CAI",
    "tel aviv": "TLV",

    # --- Europe ---
    "london": "LHR",
    "paris": "CDG",
    "rome": "FCO",
    "madrid": "MAD",
    "barcelona": "BCN",
    "frankfurt": "FRA",
    "munich": "MUC",
    "berlin": "BER",
    "amsterdam": "AMS",
    "zurich": "ZRH",
    "vienna": "VIE",
    "dublin": "DUB",
    "lisbon": "LIS",
    "athens": "ATH",
    "moscow": "SVO",
    "warsaw": "WAW",
    "prague": "PRG",
    "copenhagen": "CPH",
    "stockholm": "ARN",
    "oslo": "OSL",
    "helsinki": "HEL",

    # --- North America ---
    "new york": "JFK",
    "los angeles": "LAX",
    "san francisco": "SFO",
    "chicago": "ORD",
    "toronto": "YYZ",
    "vancouver": "YVR",
    "mexico city": "MEX",

    # --- Oceania ---
    "sydney": "SYD",
    "melbourne": "MEL",
    "auckland": "AKL",

    # --- South Asia (non-India) ---
    "dhaka": "DAC",
    "kathmandu": "KTM",
    "colombo": "CMB",
    "karachi": "KHI",
    "lahore": "LHE",
    "male": "MLE",

    # --- Africa ---
    "johannesburg": "JNB",
    "cape town": "CPT",
    "nairobi": "NBO",
    "lagos": "LOS",

    # --- South America ---
    "sao paulo": "GRU",
    "rio de janeiro": "GIG",
    "buenos aires": "EZE",
    "bogota": "BOG",
    "lima": "LIM",
}


def clean_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    stop_words = [
        "flight", "flights", "ticket", "tickets", "trip", "travel",
        "plan", "complete", "days", "day", "including", "hotel",
        "hotels", "sightseeing", "under", "budget", "info", "information"
    ]
    words = [w for w in text.split() if w not in stop_words]
    return " ".join(words).strip()


def country_name_to_code(text: str):
    text = clean_text(text)

    if text in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[text]

    try:
        country = pycountry.countries.lookup(text)
        return country.alpha_2
    except LookupError:
        pass

    # Detect country name inside longer text
    for country in pycountry.countries:
        country_name = country.name.lower()
        if country_name in text:
            return country.alpha_2

    for alias, code in COUNTRY_ALIASES.items():
        if alias in text:
            return code

    return None


def airport_country_matches(airport: dict, country_code: str) -> bool:
    airport_country = str(airport.get("country", "")).upper().strip()

    if airport_country == country_code:
        return True

    try:
        country = pycountry.countries.get(alpha_2=country_code)
        if country and airport_country.lower() == country.name.lower():
            return True
    except LookupError:
        logger.debug(f"Could not resolve country code '{country_code}' via pycountry")

    return False


def get_best_airport_for_country(country_code: str):
    preferred = COUNTRY_MAIN_AIRPORT.get(country_code)

    if preferred and preferred in AIRPORTS:
        return preferred

    candidates = []

    for iata, airport in AIRPORTS.items():
        if not iata:
            continue

        if airport_country_matches(airport, country_code):
            name = str(airport.get("name", "")).lower()
            city = str(airport.get("city", "")).lower()

            score = 0

            if "international" in name:
                score += 50
            if "intl" in name:
                score += 40
            if "capital" in name:
                score += 20
            if city:
                score += 5

            candidates.append((score, iata))

    if not candidates:
        return None

    candidates.sort(reverse=True)
    return candidates[0][1]


def resolve_location_to_iata(location: str):
    """
    Converts country/city/airport/IATA into IATA code.

    Examples:
    Bangladesh -> DAC
    Japan -> NRT
    Dhaka -> DAC
    Tokyo -> NRT
    DAC -> DAC
    """
    if not location:
        return None

    raw_location = location.strip()

    # Direct IATA code
    if re.fullmatch(r"[A-Za-z]{3}", raw_location):
        code = raw_location.upper()
        if code in AIRPORTS:
            return code

    location_clean = clean_text(raw_location)

    if not location_clean:
        return None

    # City preferred airport
    if location_clean in CITY_MAIN_AIRPORT:
        return CITY_MAIN_AIRPORT[location_clean]

    # Country preferred airport
    country_code = country_name_to_code(location_clean)
    if country_code:
        airport = get_best_airport_for_country(country_code)
        if airport:
            return airport

    # Exact / fuzzy city match from airport database
    city_matches = []

    for iata, airport in AIRPORTS.items():
        city = str(airport.get("city", "")).lower().strip()
        name = str(airport.get("name", "")).lower().strip()

        score = 0

        if city == location_clean:
            score += 100
        elif location_clean in city:
            score += 70

        if location_clean in name:
            score += 50

        if "international" in name:
            score += 10

        if score > 0:
            city_matches.append((score, iata))

    if city_matches:
        city_matches.sort(reverse=True)
        return city_matches[0][1]

    return None


def find_location_mentions(query: str):
    """
    Finds country or city names inside a natural language query.
    """
    q = query.lower()
    mentions = []

    # Country aliases
    for alias in COUNTRY_ALIASES:
        if re.search(rf"\b{re.escape(alias)}\b", q):
            mentions.append(alias)

    # Country names from pycountry
    for country in pycountry.countries:
        name = country.name.lower()
        if len(name) >= 4 and re.search(rf"\b{re.escape(name)}\b", q):
            mentions.append(name)

    # City names from our preferred city map
    for city in CITY_MAIN_AIRPORT:
        if re.search(rf"\b{re.escape(city)}\b", q):
            mentions.append(city)

    # Remove duplicates while keeping order
    unique_mentions = []
    for item in mentions:
        if item not in unique_mentions:
            unique_mentions.append(item)

    return unique_mentions


def parse_route(query: str):
    """
    Returns:
    dep_iata, arr_iata

    Can return:
    None, None  -> global live flights
    DAC, NRT    -> filtered route
    DAC, None   -> all flights from DAC
    None, NRT   -> all flights to NRT
    """
    q = query.strip()
    q_lower = q.lower()

    # Global / all-country query
    global_keywords = [
        "all country",
        "all countries",
        "global flight",
        "global flights",
        "all flight",
        "all flights",
        "worldwide flight",
        "worldwide flights",
    ]

    if any(keyword in q_lower for keyword in global_keywords):
        return None, None

    # Direct IATA code route: DAC to NRT
    # Only accept codes that are actually valid IATA codes, to avoid
    # false positives from random 3-letter uppercase words.
    codes = re.findall(r"\b[A-Z]{3}\b", q.upper())

    valid_codes = [code for code in codes if code in AIRPORTS]

    if len(valid_codes) >= 2:
        return valid_codes[0], valid_codes[1]

    # Pattern: from X to Y
    match = re.search(
        r"\bfrom\s+(.+?)\s+\bto\s+(.+?)(?:\s+(?:on|for|under|including|with|in|at)\b|[.!?]|$)",
        q_lower,
    )

    if match:
        origin_text = match.group(1)
        dest_text = match.group(2)

        dep_iata = resolve_location_to_iata(origin_text)
        arr_iata = resolve_location_to_iata(dest_text)

        return dep_iata, arr_iata

    # Pattern: to Y from X
    match = re.search(
        r"\bto\s+(.+?)\s+\bfrom\s+(.+?)(?:\s+(?:on|for|under|including|with|in|at)\b|[.!?]|$)",
        q_lower,
    )

    if match:
        dest_text = match.group(1)
        origin_text = match.group(2)

        dep_iata = resolve_location_to_iata(origin_text)
        arr_iata = resolve_location_to_iata(dest_text)

        return dep_iata, arr_iata

    # Pattern: destination trip from origin
    # Example: "Japan trip from Bangladesh"
    match = re.search(r"(.+?)\s+trip\s+from\s+(.+)", q_lower)

    if match:
        dest_text = match.group(1)
        origin_text = match.group(2)

        dep_iata = resolve_location_to_iata(origin_text)
        arr_iata = resolve_location_to_iata(dest_text)

        return dep_iata, arr_iata

    # Pattern: flights from X
    match = re.search(r"\bfrom\s+(.+?)(?:[.!?]|$)", q_lower)

    if match:
        origin_text = match.group(1)
        dep_iata = resolve_location_to_iata(origin_text)
        return dep_iata, None

    # Pattern: flights to X
    match = re.search(r"\bto\s+(.+?)(?:[.!?]|$)", q_lower)

    if match:
        dest_text = match.group(1)
        arr_iata = resolve_location_to_iata(dest_text)
        return None, arr_iata

    # Fallback: find country/city mentions
    mentions = find_location_mentions(q)

    if len(mentions) >= 2:
        dep_iata = resolve_location_to_iata(mentions[0])
        arr_iata = resolve_location_to_iata(mentions[1])
        return dep_iata, arr_iata

    if len(mentions) == 1:
        arr_iata = resolve_location_to_iata(mentions[0])
        return DEFAULT_ORIGIN_IATA, arr_iata

    return None, None


def format_flight(flight: dict):
    airline = flight.get("airline", {}).get("name") or "Unknown airline"
    flight_number = flight.get("flight", {}).get("iata") or "Unknown flight number"
    status = flight.get("flight_status") or "Unknown"

    dep = flight.get("departure", {}) or {}
    arr = flight.get("arrival", {}) or {}

    dep_airport = dep.get("airport") or "Unknown departure airport"
    dep_iata = dep.get("iata") or "Unknown"
    dep_terminal = dep.get("terminal") or "N/A"
    dep_gate = dep.get("gate") or "N/A"
    dep_scheduled = dep.get("scheduled") or "Unknown"
    dep_delay = dep.get("delay")
    dep_delay_text = f"{dep_delay} minutes" if dep_delay is not None else "N/A"

    arr_airport = arr.get("airport") or "Unknown arrival airport"
    arr_iata = arr.get("iata") or "Unknown"
    arr_terminal = arr.get("terminal") or "N/A"
    arr_gate = arr.get("gate") or "N/A"
    arr_scheduled = arr.get("scheduled") or "Unknown"
    arr_delay = arr.get("delay")
    arr_delay_text = f"{arr_delay} minutes" if arr_delay is not None else "N/A"

    return f"""
Airline: {airline}
Flight: {flight_number}
Status: {status}

Departure:
- Airport: {dep_airport}
- IATA: {dep_iata}
- Terminal: {dep_terminal}
- Gate: {dep_gate}
- Scheduled: {dep_scheduled}
- Delay: {dep_delay_text}

Arrival:
- Airport: {arr_airport}
- IATA: {arr_iata}
- Terminal: {arr_terminal}
- Gate: {arr_gate}
- Scheduled: {arr_scheduled}
- Delay: {arr_delay_text}
""".strip()


def search_flights(query: str, limit: int = 10):
    """
    Search for live flights matching a natural-language query.

    Returns a list of formatted flight strings. Returns an empty list
    if the API key is missing, the API returns an error payload, or
    no flights are found. Raises CustomException on request/parse
    failures.
    """
    logger.info(f"Processing flight search query: '{query}'")

    if not API_KEY:
        logger.warning("Flight API key is missing. Cannot complete request.")
        return []

    dep_iata, arr_iata = parse_route(query)
    logger.info(f"Parsed route -> Departure: {dep_iata}, Arrival: {arr_iata}")

    params = {
        "access_key": API_KEY,
        "limit": min(limit, 100),
    }

    if dep_iata:
        params["dep_iata"] = dep_iata

    if arr_iata:
        params["arr_iata"] = arr_iata

    try:
        logger.info(f"Calling Aviationstack API with params: {params}")
        response = requests.get(BASE_URL, params=params, timeout=30)
        logger.info(f"Aviationstack status code: {response.status_code}")
        data = response.json()
        logger.info(f"Flight API response keys: {list(data.keys())}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Aviationstack API request failed: {str(e)}")
        raise CustomException("Flight API request failed", e)
    except ValueError as e:
        logger.error("Aviationstack API returned invalid JSON.")
        raise CustomException("Flight API returned invalid JSON", e)

    if "error" in data:
        logger.error(f"Flight API returned an error payload: {data['error']}")
        return []

    flight_data = data.get("data", [])
    logger.info(f"Retrieved {len(flight_data)} flights from API.")

    if not flight_data:
        logger.warning(f"No live flight data found for route {dep_iata} -> {arr_iata}")
        return [f"No active flights found for route {dep_iata} -> {arr_iata}"]

    return [format_flight(flight) for flight in flight_data[:limit]]



# if __name__ == "__main__":
#     print("=" * 80)
#     print("Flight Search Tester")
#     print("Type 'exit' to quit.")
#     print("=" * 80)

#     while True:
#         try:
#             query = input("\nEnter your flight query: ").strip()

#             if query.lower() in {"exit", "quit", "q"}:
#                 print("Exiting...")
#                 break

#             if not query:
#                 print("Please enter a valid query.")
#                 continue

#             print("\n" + "-" * 80)
#             print("Parsing Route...")
#             dep_iata, arr_iata = parse_route(query)
#             print(f"Departure IATA : {dep_iata}")
#             print(f"Arrival IATA   : {arr_iata}")

#             print("\nSearching live flights...\n")

#             flights = search_flights(query)

#             if not flights:
#                 print("No flights found.")
#             else:
#                 print(f"Found {len(flights)} flight(s)\n")

#                 for idx, flight in enumerate(flights, start=1):
#                     print("=" * 80)
#                     print(f"Flight {idx}")
#                     print("=" * 80)
#                     print(flight)
#                     print()

#         except KeyboardInterrupt:
#             print("\nExiting...")
#             break

#         except Exception as e:
#             logger.exception("Unexpected error while searching flights.")
#             print(f"\nError: {e}")