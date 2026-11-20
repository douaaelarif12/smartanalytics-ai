from __future__ import annotations

from uuid import UUID

from .dashboard_models import (
    DashboardCreate,
    DashboardDetail,
    DashboardListResponse,
    DashboardUpdate,
    DashboardWidgetCreate,
    DashboardWidgetResponse,
    DashboardWidgetUpdate,
)
from .dashboard_repository import DashboardRepository
from .errors import ApiError
from .service import DatasetService


class DashboardService:
    def __init__(self, datasets: DatasetService):
        self.datasets = datasets
        self.repository = DashboardRepository(datasets.database)

    @staticmethod
    def _owner(owner_id: str | None) -> str:
        if not owner_id:
            raise ApiError(401, "authentication_required", "Please sign in to continue.")
        return owner_id

    @staticmethod
    def _id(value: str, resource: str) -> str:
        try:
            return str(UUID(value))
        except ValueError:
            raise ApiError(404, f"{resource}_not_found", f"The requested {resource} does not exist.") from None

    def _validate_query(self, dataset_id: str, query, owner_id: str) -> None:
        metadata = self.datasets.get(dataset_id, owner_id)
        kinds = {column.name: column.type for column in metadata.columns}
        # Reuse the exact compiler validation used by live Data Explorer queries.
        self.datasets.analytics._validate(query, kinds)

    def list(self, owner_id: str | None) -> DashboardListResponse:
        return self.repository.list(self._owner(owner_id))

    def get(self, dashboard_id: str, owner_id: str | None) -> DashboardDetail:
        return self.repository.get(self._id(dashboard_id, "dashboard"), self._owner(owner_id))

    def create(self, body: DashboardCreate, owner_id: str | None) -> DashboardDetail:
        return self.repository.create(body, self._owner(owner_id))

    def update(self, dashboard_id: str, body: DashboardUpdate, owner_id: str | None) -> DashboardDetail:
        return self.repository.update(self._id(dashboard_id, "dashboard"), body, self._owner(owner_id))

    def delete(self, dashboard_id: str, expected_revision: int, owner_id: str | None) -> None:
        self.repository.delete(self._id(dashboard_id, "dashboard"), expected_revision, self._owner(owner_id))

    def add_widget(self, dashboard_id: str, body: DashboardWidgetCreate, owner_id: str | None) -> DashboardDetail:
        owner = self._owner(owner_id)
        self._validate_query(body.dataset_id, body.query, owner)
        return self.repository.add_widget(self._id(dashboard_id, "dashboard"), body, owner)

    def get_widget(self, dashboard_id: str, widget_id: str, owner_id: str | None) -> DashboardWidgetResponse:
        owner = self._owner(owner_id)
        return self.repository.get_widget(
            self._id(dashboard_id, "dashboard"), self._id(widget_id, "widget"), owner)

    def update_widget(self, dashboard_id: str, widget_id: str, body: DashboardWidgetUpdate, owner_id: str | None) -> DashboardDetail:
        owner = self._owner(owner_id)
        dashboard = self._id(dashboard_id, "dashboard")
        widget = self.repository.get_widget(dashboard, self._id(widget_id, "widget"), owner)
        if body.query is not None or "dataset_id" in body.model_fields_set:
            dataset_id = body.dataset_id if "dataset_id" in body.model_fields_set else widget.dataset_id
            if not dataset_id:
                raise ApiError(422, "dataset_required", "Choose an available dataset before changing this analysis.")
            self._validate_query(dataset_id, body.query or widget.query, owner)
        return self.repository.update_widget(dashboard, widget.id, body, owner)

    def delete_widget(self, dashboard_id: str, widget_id: str, expected_revision: int, owner_id: str | None) -> DashboardDetail:
        owner = self._owner(owner_id)
        return self.repository.delete_widget(
            self._id(dashboard_id, "dashboard"), self._id(widget_id, "widget"), expected_revision, owner)
