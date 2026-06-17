import os, sys, json
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from app.observability import server_logging, http_logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.observability.http_logging import add_http_logging_middleware
from app.api import rou
from app.mcp_conn.mcp_main import initialize_mcp_servers
from app.mcp_conn.mcpmanager import mcp_manager
from app.data.decisiontree_type import DecisionTree
from app.data.divtree_data import DECISION_TREE_DATA
import app.globals as g

# Filter out /mcp/logs from uvicorn access logs
class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("/mcp/logs") == -1

# Add filter to uvicorn access logger
logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize MCP servers and decision tree on startup, cleanup on shutdown"""

    # Startup
    server_logging.add_server_log("system", "Server starting up...", level="info")

    try:
        initialize_mcp_servers()
        mcp_manager.initialize_default_clients()
        server_logging.add_server_log("system", "MCP clients initialized", level="info")
    except Exception as e:
        http_logging.logger(f"Failed to initialize MCP servers: {str(e)}")
        server_logging.add_server_log("system", f"Startup MCP init failed: {str(e)}", level="error")

    # Initialize decision tree from imported data - REQUIRED, fail if it doesn't work
    g.decision_tree = DecisionTree(data_dict=DECISION_TREE_DATA)
    server_logging.add_server_log("system", f"Decision Tree initialized: {len(g.decision_tree.nodes)} nodes loaded", level="info")

    yield

    # Shutdown
    server_logging.add_server_log("system", "Shutting down MCP servers...")
    # Clean shutdown for stdio-based servers happens automatically


def create_app()-> FastAPI:
    app = FastAPI(docs_url="/swagger", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        # allow_origins=settings.ALLOWED_ORIGINS,
        # allow_credentials=True,
        allow_origins=["*"],
        allow_credentials=False,  # MUST be False when origins="*"
        allow_methods=["*"],
        allow_headers=["*"],
    )

    add_http_logging_middleware(app)
    app.include_router(rou)

    return app
