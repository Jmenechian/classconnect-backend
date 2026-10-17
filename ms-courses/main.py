import logging
import os

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from router import router  # from router folder import router.py
from utils import api_setup

logging.basicConfig(level=logging.INFO)

# Check if we're in testing mode
IS_TESTING = os.getenv("TESTING", "false").lower() == "true"

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Datadog setup (only if not testing)
if not IS_TESTING:
    from ddtrace import patch, config
    from datadog import statsd, initialize, api

    initialize(
        api_key=os.getenv("DD_API_KEY"),
        host=os.getenv("DD_AGENT_HOST", "localhost"),
        port=int(os.getenv("DD_TRACE_AGENT_PORT", 8126)),
    )

    api.Metric.send(
        metric="api.requests",
        points=1,
        tags=["environment:development"],
    )

    patch(fastapi=True)
    config.fastapi['service_name'] = "Courses API"

# General setup
api_setup()
app = FastAPI(title="ClassConnect Content Service API", version="1.0.0")

# Request counter middleware (only if Datadog is enabled)
if not IS_TESTING:
    @app.middleware("http")
    async def count_requests(request, call_next):
        statsd.increment("api.requests")
        response = await call_next(request)
        return response

# CORS for development
if ENVIRONMENT == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# CORS for production (with restricted origins)
if ENVIRONMENT == "production":
    allowed_origins = [
        "http://localhost:3000",  # Next.js dev server
        "https://backoffice-xi-dusky.vercel.app" # Production frontend
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

# Routers
app.include_router(router.router)
