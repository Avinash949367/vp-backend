from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.sessions import SessionMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
import json
import logging
import structlog
from typing import List, Dict, Any

from database import connect_to_mongo, close_mongo_connection, get_database
from models import *
from auth import *
from routers.auth_router import router as auth_router
from routers.oauth_router import router as oauth_router
from routers.trips_router import router as trips_router
from routers.activities_router import router as activities_router
from routers.expenses_router import router as expenses_router
from routers.packing_router import router as packing_router
from routers.weather_router import router as weather_router
from config import settings

# Configure structured logging
if settings.enable_structured_logging:
    structlog.configure(
        processors=[
            structlog.processors.JSONRenderer()
        ]
    )
    logger = structlog.get_logger()
else:
    logger = logging.getLogger("uvicorn")

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_requests}/{settings.rate_limit_window} second"])

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, trip_id: str):
        await websocket.accept()
        if trip_id not in self.active_connections:
            self.active_connections[trip_id] = []
        self.active_connections[trip_id].append(websocket)

    def disconnect(self, websocket: WebSocket, trip_id: str):
        if trip_id in self.active_connections:
            self.active_connections[trip_id].remove(websocket)
            if not self.active_connections[trip_id]:
                del self.active_connections[trip_id]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_to_trip(self, message: str, trip_id: str):
        if trip_id in self.active_connections:
            for connection in self.active_connections[trip_id]:
                try:
                    await connection.send_text(message)
                except:
                    # Remove broken connections
                    self.active_connections[trip_id].remove(connection)

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()

app = FastAPI(title="TravelMate API", lifespan=lifespan)

# Add rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted hosts middleware (optional, can be configured)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1"]
)

# Session middleware for OAuth
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="travelmate_session"
)

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["authentication"])
app.include_router(oauth_router, prefix="/auth/oauth", tags=["oauth"])
app.include_router(trips_router, prefix="/trips", tags=["trips"])
app.include_router(activities_router, prefix="/activities", tags=["activities"])
app.include_router(expenses_router, prefix="/expenses", tags=["expenses"])
app.include_router(packing_router, prefix="/packing", tags=["packing"])
app.include_router(weather_router, prefix="/weather", tags=["weather"])

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("request_start", method=request.method, url=str(request.url))
    response = await call_next(request)
    logger.info("request_end", status_code=response.status_code)
    return response

@app.get("/")
async def root():
    return {"message": "TravelMate API is running!"}

@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)

@app.websocket("/ws/{trip_id}")
async def websocket_endpoint(websocket: WebSocket, trip_id: str):
    await manager.connect(websocket, trip_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Broadcast the message to all connected clients for this trip
            await manager.broadcast_to_trip(data, trip_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, trip_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
