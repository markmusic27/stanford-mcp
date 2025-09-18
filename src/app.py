from contextlib import asynccontextmanager
import logging
import os
from typing import Any, AsyncIterator
import click
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse, JSONResponse
from starlette.types import Receive, Scope, Send
from starlette.routing import Mount, Route
from starlette.config import Config
import uvicorn

from auth import require_bearer_token
from helpers import return_tools
from tools import register_all_tools
import mcp.types as types

from tools.registry import dispatch, list_all_tools
from tools.course_catalog.course_catalog import reset_course_connection_cache

logger = logging.getLogger(__name__)

# Setup basic CLI with variables passed on running script
@click.command()
@click.option(
    "--port", 
    default=8080, 
    help="Port to listen on for HTTP"
)
@click.option(
    "--log-level",
    default="INFO", 
    help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
)
@click.option(
    "--debug/--no-debug",
    default=False,
    help="Enable debug mode (Starlette debug and Uvicorn reload)",
)

# Main method below
def main(port: int, log_level: str, debug: bool):
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()), # -> converts log_level to logging.{log_level} (e.g, INFO -> logging.INFO)
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Load config from .env
    config = Config(".env")
    api_auth_token = config("API_AUTH_TOKEN", cast=str, default=None)
    api_auth_header = config("API_AUTH_HEADER", cast=str, default="Authorization")
    if not api_auth_token:
        raise RuntimeError("API_AUTH_TOKEN is not set. Create an .env with API_AUTH_TOKEN")
    
    app = Server("stanford-mcp")
    
    # Setup tool registry with app
    register_all_tools()
    
    # Log tools
    logger.info("\n\n" + return_tools() + "\n\n")
    
    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        return list_all_tools()
    
    @app.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.ContentBlock]:
        ctx = app.request_context
        return await dispatch(name, arguments, ctx)
    
    # Create the session manager with stateless mode
    session_manager = StreamableHTTPSessionManager(
        app=app,
        event_store=None,
        json_response=False,
        stateless=True
    )
    
    # Define methods for Starlette app
    async def handle_streamable_http(scope: Scope, receive: Receive, send: Send) -> None:
        await session_manager.handle_request(scope, receive, send)
        
    # Root redirect to github
    async def root_redirect(request):
        return RedirectResponse(url="https://github.com/markmusic27/stanford-mcp", status_code=307)
    
    # Simple health check
    async def healthz(request):
        return JSONResponse({"status": "ok"})
    
    # Wrap MCP handler with Bearer auth
    protected_http = require_bearer_token(
        handle_streamable_http, 
        api_auth_header,
        api_auth_token
    )
        
    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        """Context manager for session manager."""
        async with session_manager.run():
            logger.info("Application started with StreamableHTTP session manager")
            try:
                yield
            finally:
                logger.info("Application shutting down...")
                reset_course_connection_cache()
                
    # Initialize starlette app
    starlette_app = Starlette(
        debug=debug,
        routes=[
            Route("/", root_redirect),
            Route("/healthz", healthz),
            Mount("/mcp", app=protected_http)
        ],
        lifespan=lifespan,
    )
    
    # Wrap ASGI application with CORS middleware to expose Mcp-Session-Id header for browser-based clients
    starlette_app = CORSMiddleware(
        starlette_app,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "DELETE"],
        expose_headers=["Mcp-Session-Id"]
    )
    
    uvicorn.run(
        starlette_app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", port)),
        log_level=log_level.lower(),
        reload=debug,
    )
    
    return 0
