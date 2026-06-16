from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.observability.http_logging import add_http_logging_middleware
from app.api import rou


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize MCP servers and decision tree on startup, cleanup on shutdown"""
    global decision_tree

    # Startup
    try:
        initialize_mcp_servers()
    except Exception as e:
        logger.error(f"Failed to initialize MCP servers: {e}")
        add_server_log("system", f"Startup MCP init failed: {str(e)}")

    # Initialize decision tree
    try:
        tree_file = os.path.join(os.path.dirname(__file__), 'data/dividend_strategy_tree.json')
        decision_tree = DecisionTree(tree_file)
        add_server_log("system", f"Decision Tree initialized: {len(decision_tree.nodes)} nodes loaded", level="info")
    except Exception as e:
        add_server_log("system", f"Decision Tree initialization failed: {str(e)}", level="error")
        decision_tree = None

    yield

    # Shutdown
    add_server_log("system", "Shutting down MCP servers...")
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
