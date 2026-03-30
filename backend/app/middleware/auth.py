from fastapi import HTTPException, Request
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

import structlog

from app.core.logging import get_logger
from app.core.security import verify_token

log = get_logger("app.middleware.auth")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip authentication for certain paths
        if request.url.path in ["/docs", "/redoc", "/openapi.json", "/health"]:
            return await call_next(request)
        
        # Skip authentication for auth endpoints
        if request.url.path.startswith("/auth/"):
            return await call_next(request)
        
        # Get authorization header
        authorization: str = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)
        
        if not authorization or scheme.lower() != "bearer":
            return await call_next(request)  # Let endpoint handle authentication
        
        token = param
        try:
            payload = verify_token(token)
            if payload is None:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Attach user info to request state for use in endpoints
            request.state.user_id = user_id
            # Bind to structlog so every log line includes user_id
            structlog.contextvars.bind_contextvars(user_id=user_id)
            
        except Exception as e:
            log.warning("auth_failed", path=request.url.path, error=str(e))
            # Let endpoint handle authentication errors
            pass
        
        response: Response = await call_next(request)
        return response