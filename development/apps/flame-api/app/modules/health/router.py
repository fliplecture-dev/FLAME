from fastapi import APIRouter, Request
from app.core.errors import error_response

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def live():
    return {"status": "ok", "service": "flame-api"}


@router.get("/ready")
def ready(request: Request):
    if not request.app.state.database.ready():
        return error_response(request, 503, "dependency_unavailable",
                              "Database is not ready.", retryable=True)
    return {"status": "ok", "checks": {"database": "ok"}}
