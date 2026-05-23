"""FastAPI server: async chat with background task processing."""

import uuid
import traceback
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from ..graph.builder import build_enhanced_graph


app = FastAPI(
    title="Travel AI Assistant API",
    description="Async multi-agent system for intelligent travel planning",
    version="1.0.0",
)

agent_graph = build_enhanced_graph()

# In-memory job store (replace with Redis for production scale)
jobs = {}

# In-memory customer data (replace with database for production)
customer_data = {}


origins = [
    "http://localhost:3000",
    "http://localhost:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, description="User's travel query")
    thread_id: str = Field(min_length=5, description="Conversation thread ID")
    is_continuation: Optional[bool] = Field(False, description="Is this continuing a previous conversation")


class TaskResponse(BaseModel):
    task_id: str


class StatusResponse(BaseModel):
    status: str  # "running", "completed", "failed"
    result: dict | None = None
    form_to_display: str | None = None


class CustomerInfoRequest(BaseModel):
    thread_id: str = Field(min_length=5)
    customer_info: dict


async def run_agent_in_background(task_id: str, thread_id: str, message: str, is_continuation: bool = False):
    """Execute agent graph in background to prevent request timeout."""
    print(f"Background task {task_id} started (continuation: {is_continuation})")

    try:
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = {
            "messages": [HumanMessage(content=message)],
            "is_continuation": is_continuation,
        }

        if thread_id in customer_data:
            initial_state["customer_info"] = customer_data[thread_id]
            initial_state["current_step"] = "info_collected"
            print(f"Using stored customer info for thread {thread_id}")
        else:
            initial_state["current_step"] = "initial"

        final_state = await agent_graph.ainvoke(initial_state, config)

        last_message = final_state['messages'][-1]
        reply = str(last_message.content) if last_message.content else "I've processed the information."

        result_data = {"status": "completed", "result": {"reply": reply}}

        if final_state.get('form_to_display'):
            result_data["form_to_display"] = final_state['form_to_display']

        jobs[task_id] = result_data
        print(f"Background task {task_id} completed")

    except Exception as e:
        traceback.print_exc()
        jobs[task_id] = {"status": "failed", "result": {"error": str(e)}}
        print(f"Background task {task_id} failed: {e}")


@app.get("/", tags=["Status"])
def root():
    """Root endpoint - health check."""
    return {
        "status": "ok",
        "service": "Travel AI Assistant",
        "architecture": "async",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Status"])
def health():
    return {"status": "healthy"}


@app.post("/chat", response_model=TaskResponse, tags=["AI Agent"])
async def start_chat_task(request: ChatRequest, background_tasks: BackgroundTasks):
    """Start an async chat task with the AI agent."""
    task_id = str(uuid.uuid4())
    jobs[task_id] = {"status": "running"}

    background_tasks.add_task(
        run_agent_in_background,
        task_id,
        request.thread_id,
        request.message,
        request.is_continuation,
    )

    print(f"Chat task created: {task_id}")
    return TaskResponse(task_id=task_id)


@app.get("/chat/status/{task_id}", response_model=StatusResponse, tags=["AI Agent"])
async def get_task_status(task_id: str):
    """Poll the status of an async chat task."""
    job = jobs.get(task_id)
    if not job:
        raise HTTPException(status_code=404, detail="Task not found")
    return StatusResponse(**job)


@app.post("/chat/customer-info", tags=["AI Agent"])
async def submit_customer_info(request: CustomerInfoRequest):
    """Submit customer information for a conversation thread."""
    customer_data[request.thread_id] = request.customer_info
    print(f"Customer info stored for thread {request.thread_id}")

    return {"status": "received", "message": "Customer information saved successfully"}


@app.delete("/chat/thread/{thread_id}", tags=["AI Agent"])
async def clear_thread(thread_id: str):
    """Clear stored data for a conversation thread."""
    if thread_id in customer_data:
        del customer_data[thread_id]
        print(f"Thread {thread_id} cleared")
        return {"status": "cleared"}
    else:
        raise HTTPException(status_code=404, detail="Thread not found")


@app.on_event("startup")
async def startup_event():
    print("Travel AI Assistant - Server Starting")
    print("Agent graph initialized")
    print("CORS configured")
    print("Ready to accept requests")


@app.on_event("shutdown")
async def shutdown_event():
    print("Server shutting down")


if __name__ == "__main__":
    uvicorn.run("backend.api.main:app", host="0.0.0.0", port=8000, reload=True)
