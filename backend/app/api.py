from __future__ import annotations

from contextlib import asynccontextmanager
import asyncio
import csv
from io import StringIO
import time
from threading import Event
from starlette.concurrency import run_in_threadpool

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile, status

from .models import AnalyticsQuerySpec, AnalyticsResult, DatasetListResponse, DatasetMetadata, DatasetPreview, DatasetProfile, HealthResponse
from .service import DatasetService
from .ai import AIService
from .ai_models import AskRequest, AskResponse
from .auth import PublicUser
from .errors import ApiError


def create_router(service: DatasetService, auth) -> APIRouter:
    assistant = AIService(service)

    @asynccontextmanager
    async def lifespan(_):
        try:
            yield
        finally:
            assistant.close()
            auth.limiter.close()
            service.database.close()

    router = APIRouter(prefix="/api", lifespan=lifespan)

    @router.post("/datasets/{dataset_id}/ai/ask", response_model=AskResponse)
    async def ask_dataset(dataset_id: str, body: AskRequest, request: Request, user: PublicUser = Depends(auth.require_user)):
        await run_in_threadpool(service.get, dataset_id, user.id)
        if await request.is_disconnected():
            return Response(status_code=499)
        cancelled = Event()
        task = asyncio.create_task(run_in_threadpool(
            assistant.ask, dataset_id, body.question, user.id, cancelled))
        deadline = time.monotonic()+90
        while True:
            done, _ = await asyncio.wait({task}, timeout=.25)
            if done:
                return task.result()
            if await request.is_disconnected() or time.monotonic() > deadline:
                cancelled.set()
                # Do not kill a thread inside DuckDB/HTTP. It retains its concurrency
                # slot until completion and records any provider usage already incurred.
                task.add_done_callback(lambda finished: finished.exception()
                                       if not finished.cancelled() else None)
                if time.monotonic() > deadline:
                    raise ApiError(504, "ai_timeout", "The analytical request timed out.")
                return Response(status_code=499)

    @router.get("/auth/usage")
    def usage(user: PublicUser = Depends(auth.require_user)):
        return assistant.usage(user.id)

    @router.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @router.get("/ready")
    def ready():
        from sqlalchemy import text
        from sqlalchemy.exc import SQLAlchemyError
        from redis.exceptions import RedisError
        try:
            with service.database.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            if auth.limiter.redis is not None:
                auth.limiter.redis.ping()
        except (SQLAlchemyError, RedisError):
            raise ApiError(503, "not_ready", "A required service is unavailable.") from None
        return {"status": "ready"}

    @router.post("/datasets", response_model=DatasetMetadata, status_code=status.HTTP_201_CREATED)
    async def create_dataset(file: UploadFile = File(...), user: PublicUser = Depends(auth.require_user)) -> DatasetMetadata:
        return await service.create(file, user.id)

    @router.get("/datasets", response_model=DatasetListResponse)
    def list_datasets(user: PublicUser = Depends(auth.require_user)) -> DatasetListResponse:
        items = service.list(user.id)
        return DatasetListResponse(items=items, total=len(items))

    @router.get("/datasets/{dataset_id}", response_model=DatasetMetadata)
    def get_dataset(dataset_id: str, user: PublicUser = Depends(auth.require_user)) -> DatasetMetadata:
        return service.get(dataset_id, user.id)

    @router.get("/datasets/{dataset_id}/preview", response_model=DatasetPreview)
    def preview_dataset(
        dataset_id: str,
        offset: int = Query(0, ge=0, le=10_000_000),
        limit: int = Query(25, ge=1, le=100),
        user: PublicUser = Depends(auth.require_user),
    ) -> DatasetPreview:
        return service.preview(dataset_id, offset, limit, user.id)

    @router.get("/datasets/{dataset_id}/profile", response_model=DatasetProfile)
    def profile_dataset(dataset_id: str, user: PublicUser = Depends(auth.require_user)) -> DatasetProfile:
        return service.profile(dataset_id, user.id)

    @router.post("/datasets/{dataset_id}/query", response_model=AnalyticsResult)
    def query_dataset(dataset_id: str, specification: AnalyticsQuerySpec, user: PublicUser = Depends(auth.require_user)) -> AnalyticsResult:
        return service.query(dataset_id, specification, user.id)

    @router.delete("/datasets/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_dataset(dataset_id: str, user: PublicUser = Depends(auth.require_user)) -> Response:
        service.delete(dataset_id, user.id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    def export_result(dataset_id, specification, user):
        result = service.query(dataset_id, specification, user.id)
        buffer = StringIO(newline="")
        writer = csv.writer(buffer, quoting=csv.QUOTE_ALL)

        def cell(value):
            if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
                return "'"+value
            return value
        writer.writerow([cell(column) for column in result.columns])
        writer.writerows([[cell(row[column]) for column in result.columns] for row in result.rows])
        return Response(buffer.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{result.dataset_id}-analysis.csv"'})

    @router.post("/datasets/{dataset_id}/export")
    def export_query(dataset_id: str, specification: AnalyticsQuerySpec, user: PublicUser = Depends(auth.require_user)):
        return export_result(dataset_id, specification, user)

    @router.get("/datasets/{dataset_id}/export")
    def export_rows(dataset_id: str, user: PublicUser = Depends(auth.require_user)):
        return export_result(dataset_id, AnalyticsQuerySpec(limit=200), user)

    return router
