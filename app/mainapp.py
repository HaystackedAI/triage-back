import os, sys, json
from contextlib import asynccontextmanager
from app.observability import server_logging, http_logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.observability.http_logging import add_http_logging_middleware
from app.api import rou
from app.mcps.mcp_main import initialize_mcp_servers
from app.data.decisiontree_type import DecisionTree
import app.globals as g

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize MCP servers and decision tree on startup, cleanup on shutdown"""

    # Startup
    try:
        initialize_mcp_servers()
    except Exception as e:
        http_logging.logger(f"Failed to initialize MCP servers: {str(e)}")
        server_logging.add_server_log("system", f"Startup MCP init failed: {str(e)}")

    # Initialize decision tree
    try:
        tree_file = os.path.join(os.path.dirname(__file__), 'data/dividend_strategy_tree.json')
        g.decision_tree = DecisionTree(tree_file)
        server_logging.add_server_log("system", f"Decision Tree initialized: {len(g.decision_tree.nodes)} nodes loaded", level="info")
    except Exception as e:
        server_logging.add_server_log("system", f"Decision Tree initialization failed: {str(e)}", level="error")
        decision_tree = None

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
