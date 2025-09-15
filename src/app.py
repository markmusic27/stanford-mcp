from contextlib import asynccontextmanager
import logging
from typing import Any, AsyncIterator
import click
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.types import Receive, Scope, Send
from starlette.routing import Mount
import uvicorn

from tools import register_all_tools
import mcp.types as types

from tools.registry import dispatch, list_all_tools

logger = logging.getLogger(__name__)

# Setup basic CLI with variables passed on running script
@click.command()
@click.option(
    "--port", 
    default=8000, 
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
    
    app = Server("stanford-mcp")
    
    
    # Setup tool registry with app
    register_all_tools()
    
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
        
    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        """Context manager for session manager."""
        async with session_manager.run():
            logger.info("Application started with StreamableHTTP session manager")
            try:
                yield
            finally:
                logger.info("Application shutting down...")
                
    # Initialize starlette app
    starlette_app = Starlette(
        debug=debug,
        routes=[
            Mount("/mcp", app=handle_streamable_http)
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
        host="localhost",
        port=port,
        log_level=log_level.lower(),
        reload=debug,
    )
    
    return 0
