from app.modules.bulk_transfer import models as bulk_transfer_models
from contextlib import asynccontextmanager
import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from app.core.config import Settings
from app.core.database import Database
from app.core.errors import error_response, install_error_handlers
from app.core.logging import configure_logging
from app.modules.bulk_transfer.router import router as bulk_router
from app.modules.bulk_transfer.google_router import router as google_sheets_router
from app.modules.health.router import router as health_router
from app.modules.identity.router import router as identity_router
from app.modules.curriculum.router import router as curriculum_router
from app.modules.conversations.router import router as conversations_router
from app.modules.teaching.router import router as teaching_router
from app.modules.teaching.answer_router import router as answer_router
from app.modules.teaching.gateway import OpenAIResponsesGateway, UnconfiguredGateway
from app.modules.resources.router import router as resources_router
from app.modules.resources.member_router import router as member_resources_router
from app.modules.recommendations.router import router as recommendations_router
from app.modules.learning_response.explore_router import router as explore_router
from app.modules.activity_kits import models as activity_kit_models  # register resource-upload FK target
from app.modules.activity_kits.router import router as kits_router
from app.modules.teachers.router import router as teachers_router


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(application):
        configure_logging(config.log_level)
        application.state.database = Database(config)
        application.state.settings = config
        application.state.gateway = (OpenAIResponsesGateway(
            config.llm_openai_api_key.get_secret_value(), config.llm_model,
            timeout_seconds=config.llm_timeout_seconds,
            max_output_tokens=config.llm_max_output_tokens)
            if config.llm_openai_api_key and config.llm_model else UnconfiguredGateway())
        try:
            yield
        finally:
            application.state.database.close()

    application = FastAPI(
        title="FLAME API", version="0.1.0",
        description="FLAME identity, curriculum, import and My Learning API.",
        lifespan=lifespan,
        docs_url="/docs" if config.environment != "production" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if config.environment != "production" else None,
    )
    install_error_handlers(application)

    @application.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = str(uuid4())
        started = perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            # No exception/body/URL logging: these can contain private data.
            logging.getLogger("flame").error("request_exception", extra={"fields": {
                "request_id": request.state.request_id, "exception_type": type(exc).__name__,
                "route": getattr(request.scope.get("route"), "path", "unmatched")}})
            response = error_response(request, 500, "internal_error",
                                      "An unexpected error occurred.")
        response.headers["X-Request-ID"] = request.state.request_id
        route = request.scope.get("route")
        logging.getLogger("flame").info("http_request", extra={"fields": {
            "request_id": request.state.request_id,
            "method": request.method,
            "route": getattr(route, "path", "unmatched"),
            "status": response.status_code,
            "duration_ms": round((perf_counter() - started) * 1000, 2),
        }})
        return response

    application.include_router(google_sheets_router)
    application.include_router(bulk_router)
    application.include_router(health_router)
    application.include_router(identity_router)
    application.include_router(curriculum_router)
    application.include_router(conversations_router)
    application.include_router(teaching_router)
    application.include_router(answer_router)
    application.include_router(resources_router)
    application.include_router(member_resources_router)
    application.include_router(recommendations_router)
    application.include_router(explore_router)
    application.include_router(teachers_router)
    application.include_router(kits_router)
    return application


app = create_app()


