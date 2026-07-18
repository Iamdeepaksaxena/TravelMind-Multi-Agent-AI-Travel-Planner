from pathlib import Path
import traceback
import uvicorn

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agent.agent import run_travel_agent

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="TripMind AI-Agent",
    description="LangGraph Multi-Agent Travel Planner API",
    version="0.1.0"
)


class TravelRequest(BaseModel):
    message: str
    thread_id: str | None = None


@app.post("/api/travel")
async def travel_planner(request_data: TravelRequest):
    try:
        user_message = request_data.message.strip()

        if not user_message:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Message cannot be empty."
                }
            )

        result = run_travel_agent(
            user_input=user_message,
            thread_id=request_data.thread_id
        )

        return JSONResponse(
            content={
                "success": True,
                "thread_id": result.get("thread_id"),
                "answer": result.get("answer"),
                "flight_results": result.get("flight_results", []),
                "hotel_results": result.get("hotel_results", []),
                "itinerary": result.get("itinerary"),
                "llm_calls": result.get("llm_calls", 0),
            }
        )

    except Exception as e:
        traceback.print_exc()

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "message": "TripMind AI-Agent API is running"
    }


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )