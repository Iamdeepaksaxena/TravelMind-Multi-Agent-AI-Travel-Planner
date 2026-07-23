from contextlib import asynccontextmanager
from pathlib import Path
import json
import traceback
import uvicorn

from fastapi import FastAPI, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from agent.agent import (
    run_travel_agent,
    stream_travel_agent,
    list_threads,
    get_thread_detail,
    close_pool,
)

BASE_DIR = Path(__file__).resolve().parent


# =========================
# Lifespan — release DB pool connections cleanly on shutdown instead of
# leaking them (the previous version had no shutdown hook at all).
# =========================
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    close_pool()


app = FastAPI(
    title="TripMind AI-Agent",
    description="LangGraph Multi-Agent Travel Planner API",
    version="0.1.0",
    lifespan=lifespan,
)


class TravelRequest(BaseModel):
    message: str
    thread_id: str | None = None


class TravelResponse(BaseModel):
    success: bool
    thread_id: str
    answer: str
    flight_results: str | None = None
    hotel_results: str | None = None
    llm_calls: int = 0


class ErrorResponse(BaseModel):
    success: bool = False
    error: str


@app.post(
    "/api/travel",
    response_model=TravelResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Empty/invalid message"},
        500: {"model": ErrorResponse, "description": "Agent execution failed"},
    },
)
async def travel_planner(request_data: TravelRequest):
    user_message = request_data.message.strip()

    if not user_message:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": "Message cannot be empty."
            }
        )

    try:
    
        result = await run_in_threadpool(
            run_travel_agent,
            user_input=user_message,
            thread_id=request_data.thread_id,
        )
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": str(e)
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "thread_id": result.get("thread_id"),
            "answer": result.get("answer"),
            "flight_results": result.get("flight_results"),
            "hotel_results": result.get("hotel_results"),
            "llm_calls": result.get("llm_calls", 0),
        }
    )


@app.post("/api/travel/stream", status_code=status.HTTP_200_OK)
async def travel_planner_stream(request_data: TravelRequest):
    user_message = request_data.message.strip()

    if not user_message:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": "Message cannot be empty."
            }
        )

    def event_generator():
        try:
            for event in stream_travel_agent(
                user_input=user_message,
                thread_id=request_data.thread_id
            ):
                yield json.dumps(event) + "\n"
        except Exception as e:
            traceback.print_exc()
            yield json.dumps({"type": "error", "error": str(e)}) + "\n"

    # Note: event_generator is a sync generator; Starlette already iterates
    # sync generators passed to StreamingResponse in a threadpool, so this
    # one was not actually blocking the event loop like the endpoint above.
    return StreamingResponse(
        event_generator(),
        media_type="application/x-ndjson"
    )


@app.get("/api/threads", status_code=status.HTTP_200_OK)
async def get_threads():
    try:
        sessions = await run_in_threadpool(list_threads)
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"success": True, "sessions": sessions}
    )


@app.get("/api/threads/{thread_id}", status_code=status.HTTP_200_OK)
async def get_thread(thread_id: str):
    try:
        detail = await run_in_threadpool(get_thread_detail, thread_id)
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )

    if detail is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"success": False, "error": "Thread not found"}
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"success": True, "thread_id": thread_id, **detail}
    )


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {
        "status": "ok",
        "message": "TripMind AI-Agent API is running"
    }


if __name__ == "__main__":
    uvicorn.run(
        "backend.fastapi:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )