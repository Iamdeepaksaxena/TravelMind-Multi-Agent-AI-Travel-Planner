import os
from dotenv import load_dotenv
from tavily import TavilyClient

from common.logger import get_logger
from common.custom_exceptions import CustomException

logger = get_logger(__name__)

load_dotenv()

try:
    client = TavilyClient(
        api_key=os.getenv("TAVILY_API_KEY")
    )
    logger.info("Tavily client initialized successfully.")

except Exception as e:
    logger.exception("Failed to initialize Tavily client.")
    raise CustomException("Failed to initialize Tavily client.", e)


def tavily_search(query: str) -> str:
    try:
        logger.info(f"Performing Tavily search for query: {query}")

        response = client.search(
            query=query,
            max_results=5
        )

        results = []

        for i, r in enumerate(response.get("results", []), 1):
            title = r.get("title", "Unknown")
            url = r.get("url", "")
            snippet = r.get("content", "").strip()

            # Keep only the first 300 characters
            if len(snippet) > 300:
                snippet = snippet[:300].rsplit(" ", 1)[0] + "..."

            results.append(
                f"{i}. **{title}**\n"
                f"   {url}\n"
                f"   {snippet}"
            )

        logger.info(f"Tavily search completed successfully. Found {len(results)} results.")

        return "\n\n".join(results)

    except Exception as e:
        logger.exception("Error occurred while performing Tavily search.")
        raise CustomException("Failed to perform Tavily search.", e)