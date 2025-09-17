from starlette.responses import JSONResponse
from starlette.types import Receive, Scope, Send


def require_bearer_token(app, header_name: str, expected_token: str):
    async def auth_app(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await app(scope, receive, send)
        
        # Only protect the MCP endpoint
        path = scope.get("path", "")
        if not path.startswith("/mcp"):
            return await app(scope, receive, send)
        
        if not expected_token:
            response = JSONResponse({
                "detail": "Server misconfigured: API_AUTH_TOKEN not set"
            }, status_code=500,)
            
            return await response(scope, receive, send)
        
        header_value = None
        for k, v in scope.get("headers", []):
            if k.decode().lower() == header_name.lower():
                header_value = v.decode()
                break
            
        if not header_value or not header_value.lower().startswith("bearer "):
            response = JSONResponse({
                "detail": "Missing bearer token"
            }, status_code=401, headers={"WWW-Authenticate": "Bearer"})
            
            return await response(scope, receive, send)
        
        token = header_value.split(" ", 1)[1]
        if token != expected_token:
            response = JSONResponse({
                "detail": "Invalid token"
            }, status_code=401, headers={"WWW-Authenticate": "Bearer"})
            
            return await response(scope, receive, send)
        
        return await app(scope, receive, send)
    
    return auth_app