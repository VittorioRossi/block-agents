"""Main entry point for the block-based agentic pipeline system API server."""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from block_agents.api.routes import router as routes_router
from block_agents.api.stream import router as stream_router
from block_agents.core.config import Config

# Load configuration
config = Config.load()

# Create FastAPI app
app = FastAPI(
    title="Block Agent Pipeline API",
    description="API for the block-based agentic pipeline system",
    version="0.1.0",
)

# Add CORS middleware
cors_origins = config.get("api.cors_origins", ["http://localhost:3000"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add routers
app.include_router(routes_router, prefix="/api")
app.include_router(stream_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint.

    Returns:
        Welcome message
    """
    return {"message": "Welcome to the Block Agent Pipeline API"}


def start():
    """Start the API server."""
    host = config.get("api.host", "0.0.0.0")
    port = config.get("api.port", 8080)
    
    uvicorn.run(
        "block_agents.main:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    start()