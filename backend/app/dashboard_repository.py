from __future__ import annotations

from datetime import UTC, datetime
import time
from uuid import uuid4

from sqlalchemy import delete, func, select, update

from .dashboard_models import (
    DashboardCreate,
    DashboardDetail,
    DashboardListResponse,
    DashboardSummary,
    DashboardUpdate,
    DashboardVisualizationConfig,
    DashboardWidgetCreate,
    DashboardWidgetResponse,
    DashboardWidgetUpdate,
    SavedWidgetDefinition,
)
from .database import Database
from .db_models import Dashboard, DashboardWidget, DatasetRecord, User
from .errors import ApiError
from .models import AnalyticsQuerySpec, DatasetMetadata


MAX_DASHBOARDS_PER_OWNER = 50
MAX_WIDGETS_PER_DASHBOARD = 12


class DashboardRepository:
    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def _timestamp(value: int) -> datetime:
        return datetime.fromtimestamp(value, UTC)

    @staticmethod
    def _dashboard(session, dashboard_id: str, owner_id: str, *, lock: bool = False) -> Dashboard:
        statement = select(Dashboard).where(
            Dashboard.id == dashboard_id, Dashboard.owner_id == owner_id)
        if lock:
            statement = statement.with_for_update()
        dashboard = session.scalar(statement)
        if dashboard is None:
            raise ApiError(404, "dashboard_not_found", "The requested dashboard does not exist.")
        return dashboard

    @staticmethod
    def _widget(session, dashboard_id: str, widget_id: str, owner_id: str) -> DashboardWidget:
        widget = session.scalar(
            select(DashboardWidget)
            .join(Dashboard, Dashboard.id == DashboardWidget.dashboard_id)
            .where(
                DashboardWidget.id == widget_id,
                DashboardWidget.dashboard_id == dashboard_id,
                Dashboard.owner_id == owner_id,
            )
        )
        if widget is None:
            raise ApiError(404, "widget_not_found", "The requested dashboard widget does not exist.")
        return widget

    @staticmethod
    def _dataset(session, dataset_id: str, owner_id: str) -> tuple[DatasetRecord, DatasetMetadata]:
        record = session.scalar(select(DatasetRecord).where(
            DatasetRecord.id == dataset_id, DatasetRecord.owner_id == owner_id))
        if record is None:
            raise ApiError(404, "dataset_not_found", "The requested dataset does not exist.")
        return record, DatasetMetadata.model_validate_json(record.metadata_json)

    @staticmethod
    def _bump_revision(session, dashboard_id: str, owner_id: str, expected: int, now: int) -> int:
        result = session.execute(
            update(Dashboard)
            .where(
                Dashboard.id == dashboard_id,
                Dashboard.owner_id == owner_id,
                Dashboard.revision == expected,
            )
            .values(revision=Dashboard.revision + 1, updated_at=now)
        )
        if result.rowcount != 1:
            raise ApiError(
                409,
                "dashboard_conflict",
                "The dashboard changed in another request. Refresh it and retry.",
                {"expected_revision": expected},
            )
        return expected + 1

    def _summary(self, session, dashboard: Dashboard) -> DashboardSummary:
        widget_count = session.scalar(select(func.count()).select_from(DashboardWidget).where(
            DashboardWidget.dashboard_id == dashboard.id)) or 0
        return DashboardSummary(
            id=dashboard.id,
            name=dashboard.name,
            description=dashboard.description,
            revision=dashboard.revision,
            widget_count=widget_count,
            created_at=self._timestamp(dashboard.created_at),
            updated_at=self._timestamp(dashboard.updated_at),
        )

    def _widget_response(self, widget: DashboardWidget) -> DashboardWidgetResponse:
        return DashboardWidgetResponse(
            id=widget.id,
            dashboard_id=widget.dashboard_id,
            dataset_id=widget.dataset_id,
            dataset_id_snapshot=widget.dataset_id_snapshot,
            dataset_name_snapshot=widget.dataset_name_snapshot,
            dataset_status="ready" if widget.dataset_id is not None else "dataset_deleted",
            title=widget.title,
            query_version=1,
            query=AnalyticsQuerySpec.model_validate_json(widget.query_spec_json),
            visualization=DashboardVisualizationConfig.model_validate_json(widget.visualization_json),
            position=widget.position,
            width_columns=widget.width_columns,
            height_rows=widget.height_rows,
            created_at=self._timestamp(widget.created_at),
            updated_at=self._timestamp(widget.updated_at),
        )

    def list(self, owner_id: str) -> DashboardListResponse:
        with self.database.session() as session:
            dashboards = session.scalars(select(Dashboard).where(
                Dashboard.owner_id == owner_id).order_by(Dashboard.updated_at.desc(), Dashboard.id)).all()
            items = [self._summary(session, dashboard) for dashboard in dashboards]
            return DashboardListResponse(items=items, total=len(items))

    def get(self, dashboard_id: str, owner_id: str) -> DashboardDetail:
        with self.database.session() as session:
            dashboard = self._dashboard(session, dashboard_id, owner_id)
            widgets = session.scalars(select(DashboardWidget).where(
                DashboardWidget.dashboard_id == dashboard.id
            ).order_by(DashboardWidget.position, DashboardWidget.created_at, DashboardWidget.id)).all()
            summary = self._summary(session, dashboard)
            return DashboardDetail(**summary.model_dump(), widgets=[self._widget_response(widget) for widget in widgets])

    def create(self, body: DashboardCreate, owner_id: str) -> DashboardDetail:
        now = int(time.time())
        with self.database.session.begin() as session:
            # Serializes the per-owner quota on PostgreSQL; SQLite serializes writes.
            session.scalar(select(User).where(User.id == owner_id).with_for_update())
            count = session.scalar(select(func.count()).select_from(Dashboard).where(Dashboard.owner_id == owner_id)) or 0
            if count >= MAX_DASHBOARDS_PER_OWNER:
                raise ApiError(409, "dashboard_limit_reached", "The account already has the maximum of 50 dashboards.")
            dashboard = Dashboard(
                id=str(uuid4()), owner_id=owner_id, name=body.name, description=body.description,
                revision=1, created_at=now, updated_at=now,
            )
            session.add(dashboard)
            session.flush()
            return DashboardDetail(**self._summary(session, dashboard).model_dump(), widgets=[])

    def update(self, dashboard_id: str, body: DashboardUpdate, owner_id: str) -> DashboardDetail:
        now = int(time.time())
        values = {"updated_at": now, "revision": Dashboard.revision + 1}
        if "name" in body.model_fields_set:
            values["name"] = body.name
        if "description" in body.model_fields_set:
            values["description"] = body.description
        with self.database.session.begin() as session:
            self._dashboard(session, dashboard_id, owner_id)
            result = session.execute(update(Dashboard).where(
                Dashboard.id == dashboard_id,
                Dashboard.owner_id == owner_id,
                Dashboard.revision == body.expected_revision,
            ).values(**values))
            if result.rowcount != 1:
                raise ApiError(409, "dashboard_conflict", "The dashboard changed in another request. Refresh it and retry.")
        return self.get(dashboard_id, owner_id)

    def delete(self, dashboard_id: str, expected_revision: int, owner_id: str) -> None:
        with self.database.session.begin() as session:
            self._dashboard(session, dashboard_id, owner_id)
            result = session.execute(delete(Dashboard).where(
                Dashboard.id == dashboard_id,
                Dashboard.owner_id == owner_id,
                Dashboard.revision == expected_revision,
            ))
            if result.rowcount != 1:
                raise ApiError(409, "dashboard_conflict", "The dashboard changed in another request. Refresh it and retry.")

    def add_widget(self, dashboard_id: str, body: DashboardWidgetCreate, owner_id: str) -> DashboardDetail:
        now = int(time.time())
        with self.database.session.begin() as session:
            self._dashboard(session, dashboard_id, owner_id, lock=True)
            _, metadata = self._dataset(session, body.dataset_id, owner_id)
            widgets = session.scalars(select(DashboardWidget).where(
                DashboardWidget.dashboard_id == dashboard_id).order_by(DashboardWidget.position)).all()
            if len(widgets) >= MAX_WIDGETS_PER_DASHBOARD:
                raise ApiError(409, "widget_limit_reached", "A dashboard can contain at most 12 widgets.")
            position = body.position if body.position is not None else len(widgets)
            self._bump_revision(session, dashboard_id, owner_id, body.expected_revision, now)
            widget = DashboardWidget(
                id=str(uuid4()), dashboard_id=dashboard_id, dataset_id=metadata.id,
                dataset_id_snapshot=metadata.id, dataset_name_snapshot=metadata.name,
                title=body.title, query_version=1, query_spec_json=body.query.model_dump_json(),
                visualization_json=body.visualization.model_dump_json(), position=position,
                width_columns=body.width_columns, height_rows=body.height_rows,
                created_at=now, updated_at=now,
            )
            session.add(widget)
            session.flush()
        return self.get(dashboard_id, owner_id)

    def get_widget(self, dashboard_id: str, widget_id: str, owner_id: str) -> DashboardWidgetResponse:
        with self.database.session() as session:
            return self._widget_response(self._widget(session, dashboard_id, widget_id, owner_id))

    def update_widget(self, dashboard_id: str, widget_id: str, body: DashboardWidgetUpdate, owner_id: str) -> DashboardDetail:
        now = int(time.time())
        with self.database.session.begin() as session:
            self._dashboard(session, dashboard_id, owner_id)
            widget = self._widget(session, dashboard_id, widget_id, owner_id)
            query = body.query or AnalyticsQuerySpec.model_validate_json(widget.query_spec_json)
            visualization = body.visualization or DashboardVisualizationConfig.model_validate_json(widget.visualization_json)
            SavedWidgetDefinition(query=query, visualization=visualization)
            if "dataset_id" in body.model_fields_set:
                if body.dataset_id is None:
                    raise ApiError(422, "dataset_required", "A widget must reference an available dataset when it is updated.")
                _, metadata = self._dataset(session, body.dataset_id, owner_id)
                widget.dataset_id = metadata.id
                widget.dataset_id_snapshot = metadata.id
                widget.dataset_name_snapshot = metadata.name
            self._bump_revision(session, dashboard_id, owner_id, body.expected_revision, now)
            for field in ("title", "position", "width_columns", "height_rows"):
                if field in body.model_fields_set:
                    setattr(widget, field, getattr(body, field))
            widget.query_spec_json = query.model_dump_json()
            widget.visualization_json = visualization.model_dump_json()
            widget.updated_at = now
        return self.get(dashboard_id, owner_id)

    def delete_widget(self, dashboard_id: str, widget_id: str, expected_revision: int, owner_id: str) -> DashboardDetail:
        now = int(time.time())
        with self.database.session.begin() as session:
            self._dashboard(session, dashboard_id, owner_id)
            widget = self._widget(session, dashboard_id, widget_id, owner_id)
            self._bump_revision(session, dashboard_id, owner_id, expected_revision, now)
            session.delete(widget)
        return self.get(dashboard_id, owner_id)
