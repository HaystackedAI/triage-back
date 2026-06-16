from datetime import datetime

from fastapi import APIRouter

rouToo = APIRouter()

@rouToo.get("/")
async def root():
    return {
        "message": "AI Triage Agent API", 
        "status": "online",
        "version": "2.0"
    }

@rouToo.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@rouToo.get("/models")
async def get_models():
    return AVAILABLE_MODELS


@app.post("/chat")
async def chat_endpoint(chat_message: ChatMessage, request: Request):
    """Chat endpoint using Strands Agent with streaming"""
    try:
        # Check if model is available
        model_ids = [model["id"] for model in AVAILABLE_MODELS]
        if chat_message.model_id not in model_ids:
            raise HTTPException(status_code=400, detail="Model not available")

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
                stream_plain_response(chat_message.message, chat_message.model_id),
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
        logger.error(f"Chat endpoint error: {str(e)}")
        add_server_log("system", f"Chat error: {str(e)[:50]}...")
        raise HTTPException(status_code=500, detail="Internal server error")
