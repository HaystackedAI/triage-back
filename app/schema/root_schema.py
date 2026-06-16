from typing import Dict, List, Any, Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Pydantic models
class ImageData(BaseModel):
    data: str  # base64 encoded image data
    name: str  # filename

class ChatMessage(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    message: str
    model_id: Optional[str] = "us.anthropic.claude-sonnet-4-20250514-v1:0"
    session_id: Optional[str] = "default"
    images: Optional[List[ImageData]] = None
    history: Optional[List[Dict[str, Any]]] = None

class ChatResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    response: str
    model_id: str
    tokens: Dict[str, int]

