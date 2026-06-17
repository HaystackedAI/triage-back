from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from app.data.models import AVAILABLE_MODELS
from app.schema.root_schema import ChatMessage, StreamingResponse
from app.schema.stream_response import stream_ai_response_with_images, stream_plain_response
from app.observability import http_logging, server_logging

rouRoot = APIRouter()


@rouRoot.get("/")
async def root(): return {"message": "AI Triage Agent API",
                          "status": "online", "version": "2.0"}


@rouRoot.get("/health")
async def health_check(): return {
    "status": "healthy", "timestamp": datetime.now().isoformat()}


@rouRoot.get("/models")
async def get_models(): return AVAILABLE_MODELS


@rouRoot.post("/chat")
async def chat_endpoint(chat_message: ChatMessage, request: Request):
    """Chat endpoint using Strands Agent with streaming"""
    try:
        # Default model if not specified or empty
        DEFAULT_MODEL_ID = "us.amazon.nova-pro-v1:0"
        if not chat_message.model_id or chat_message.model_id.strip() == "":
            chat_message.model_id = DEFAULT_MODEL_ID
            server_logging.add_server_log("user", f"Using default model: {DEFAULT_MODEL_ID}", level="info")

        # Check if model is available
        model_ids = [model["id"] for model in AVAILABLE_MODELS]
        if chat_message.model_id not in model_ids: raise HTTPException(status_code=400, detail="Model not available")
        server_logging.add_server_log("user", f"Chat request: {chat_message.message[:50]}...")
        server_logging.add_server_log("user", f"Model: {chat_message.model_id}", level="info")
        

        # Check if client accepts streaming
        accept_header = request.headers.get("accept", "")
        if "text/event-stream" in accept_header:
            # Return SSE streaming response
            return StreamingResponse(
                stream_ai_response_with_images(
                    chat_message.message,
                    chat_message.model_id,
                    chat_message.session_id,
                    chat_message.images,
                    chat_message.history
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "X-Accel-Buffering": "no",
                }
            )
        elif "text/plain" in accept_header:
            # Return plain text streaming
            return StreamingResponse(
                stream_plain_response(
                    chat_message.message, chat_message.model_id),
                media_type="text/plain"
            )
        else:
            # Default SSE streaming
            return StreamingResponse(
                stream_ai_response_with_images(
                    chat_message.message,
                    chat_message.model_id,
                    chat_message.session_id,
                    chat_message.images,
                    chat_message.history
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                }
            )

    except Exception as e:
        http_logging.logger.error(f"Chat endpoint error: {str(e)}")
        server_logging.add_server_log(
            "system", f"Chat error: {str(e)[:50]}...")
        raise HTTPException(status_code=500, detail="Internal server error")
