"""Read-only analytical API; source imports run through the separate CLI."""

from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import Response

from gridbricks.api.errors import ApiError
from gridbricks.api.routes import build_router
from gridbricks.config import Settings
from gridbricks.diagnostics import emit_event, safe_code
from gridbricks.storage.repository import Repository

MAX_QUERY_BYTES = 2048
LOGGED_PATHS = {
    "/",
    "/health",
    "/api/v1/health",
    "/api/v1/data-status",
    "/api/v1/forecast",
    "/api/v1/accuracy",
    "/api/v1/export",
    "/api/v1/forecast/revisions",
}
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
UI_CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "font-src 'self'; connect-src 'self'; frame-ancestors 'none'; form-action 'self'; "
    "base-uri 'none'; object-src 'none'"
)


class HealthResponse(BaseModel):
    status: Literal["ok"]


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or Settings()
    if runtime_settings.static_dir and not (runtime_settings.static_dir / "index.html").is_file():
        raise ValueError("Configured frontend build is missing index.html")
    application = FastAPI(
        title="GridBricks wind forecast API",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=[],
    )
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["127.0.0.1", "localhost", *runtime_settings.public_hosts],
    )
    repository = Repository(runtime_settings)
    application.state.repository = repository
    application.include_router(build_router(repository))

    if runtime_settings.static_dir is None:

        @application.get("/", include_in_schema=False)
        def open_workspace() -> RedirectResponse:
            """Send local browser visits to the frontend development server."""
            return RedirectResponse("http://127.0.0.1:5173/")

    @application.exception_handler(ApiError)
    async def analytical_error(request: Request, error: ApiError) -> JSONResponse:
        request.state.error_code = safe_code(error.code)
        return JSONResponse(status_code=error.status, content=error.payload())

    @application.middleware("http")
    async def protect_response(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        started = perf_counter()
        request_id = uuid4().hex
        request.state.request_id = request_id
        # Bound untrusted input before query parsing and error-detail reflection.
        if len(request.scope.get("query_string", b"")) > MAX_QUERY_BYTES:
            request.state.error_code = "query_too_large"
            response = JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "query_too_large",
                        "message": "The query exceeds the supported size.",
                        "details": {},
                    }
                },
            )
        else:
            try:
                response = await call_next(request)
            except Exception as error:
                request.state.error_code = "internal_error"
                request.state.exception_type = type(error).__name__
                response = JSONResponse(
                    status_code=500,
                    content={
                        "error": {
                            "code": "internal_error",
                            "message": "An internal error occurred.",
                            "details": {},
                        }
                    },
                )
        path = request.url.path
        response.headers.update(SECURITY_HEADERS)
        if (
            runtime_settings.static_dir is not None
            and path != "/health"
            and not path.startswith("/api/")
        ):
            response.headers["Content-Security-Policy"] = UI_CONTENT_SECURITY_POLICY
        response.headers["X-Request-ID"] = request_id
        known_methods = {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}
        emit_event(
            "http_request",
            request_id=request_id,
            method=request.method if request.method in known_methods else "OTHER",
            route=path if path in LOGGED_PATHS else "unmatched",
            snapshot_id=getattr(request.state, "snapshot_id", None),
            decision_from=getattr(request.state, "decision_from", None),
            decision_to=getattr(request.state, "decision_to", None),
            cutoff_local=getattr(request.state, "cutoff_local", None),
            status_code=response.status_code,
            error_code=(
                getattr(request.state, "error_code", None)
                or (f"http_{response.status_code}" if response.status_code >= 400 else None)
            ),
            exception_type=getattr(request.state, "exception_type", None),
            duration_ms=round((perf_counter() - started) * 1000, 3),
        )
        return response

    @application.get("/health", response_model=HealthResponse, include_in_schema=False)
    @application.get("/api/v1/health", response_model=HealthResponse)
    def health(request: Request) -> HealthResponse | JSONResponse:
        """Report process health only; no dataset or source check is performed."""
        if request.query_params:
            request.state.error_code = "invalid_query"
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "invalid_query",
                        "message": "The health endpoint does not accept query parameters.",
                        "details": {"unknown_parameters": sorted(request.query_params)},
                    }
                },
            )
        return HealthResponse(status="ok")

    if runtime_settings.static_dir is not None:
        application.mount(
            "/", StaticFiles(directory=runtime_settings.static_dir, html=True), name="frontend"
        )

    return application


app = create_app()
