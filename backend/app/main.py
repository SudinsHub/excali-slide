import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.assets import assets_router, deck_assets_router
from app.api.decks import router as decks_router
from app.api.dev import router as dev_router
from app.api.drafts import router as drafts_router
from app.api.slides import deck_slides_router, slides_router
from app.api.versions import router as versions_router
from app.config import settings
from app.errors import AppError, app_error_handler
from app.logging import setup_logging

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Starting Excali-Slide API server in ENV=%s", settings.ENV)
    yield
    logger.info("Shutting down Excali-Slide API server")


app = FastAPI(
    title="Excalidraw Slide Studio API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled server exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_server_error",
                "message": "An unexpected server error occurred",
                "details": {"type": type(exc).__name__, "detail": str(exc)},
            }
        },
    )


# Health check
@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "env": settings.ENV}


# API Routers under /api
api_prefix = "/api"
app.include_router(decks_router, prefix=api_prefix)
app.include_router(deck_slides_router, prefix=api_prefix)
app.include_router(slides_router, prefix=api_prefix)
app.include_router(drafts_router, prefix=api_prefix)
app.include_router(versions_router, prefix=api_prefix)
app.include_router(deck_assets_router, prefix=api_prefix)
app.include_router(assets_router, prefix=api_prefix)

if settings.ENV == "dev":
    app.include_router(dev_router, prefix=api_prefix)
