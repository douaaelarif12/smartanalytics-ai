from fastapi import APIRouter, Depends, Query, Response, status

from .auth import PublicUser
from .dashboard_models import (
    DashboardCreate,
    DashboardDetail,
    DashboardListResponse,
    DashboardUpdate,
    DashboardWidgetCreate,
    DashboardWidgetResponse,
    DashboardWidgetUpdate,
)
from .dashboard_service import DashboardService


def create_dashboard_router(service: DashboardService, auth) -> APIRouter:
    router = APIRouter(prefix="/api/dashboards", tags=["dashboards"])

    @router.get("", response_model=DashboardListResponse)
    def list_dashboards(user: PublicUser = Depends(auth.require_user)):
        return service.list(user.id)

    @router.post("", response_model=DashboardDetail, status_code=status.HTTP_201_CREATED)
    def create_dashboard(body: DashboardCreate, user: PublicUser = Depends(auth.require_user)):
        return service.create(body, user.id)

    @router.get("/{dashboard_id}", response_model=DashboardDetail)
    def get_dashboard(dashboard_id: str, user: PublicUser = Depends(auth.require_user)):
        return service.get(dashboard_id, user.id)

    @router.patch("/{dashboard_id}", response_model=DashboardDetail)
    def update_dashboard(dashboard_id: str, body: DashboardUpdate, user: PublicUser = Depends(auth.require_user)):
        return service.update(dashboard_id, body, user.id)

    @router.delete("/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_dashboard(
        dashboard_id: str,
        expected_revision: int = Query(ge=1),
        user: PublicUser = Depends(auth.require_user),
    ):
        service.delete(dashboard_id, expected_revision, user.id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.post("/{dashboard_id}/widgets", response_model=DashboardDetail, status_code=status.HTTP_201_CREATED)
    def add_widget(dashboard_id: str, body: DashboardWidgetCreate, user: PublicUser = Depends(auth.require_user)):
        return service.add_widget(dashboard_id, body, user.id)

    @router.get("/{dashboard_id}/widgets/{widget_id}", response_model=DashboardWidgetResponse)
    def get_widget(dashboard_id: str, widget_id: str, user: PublicUser = Depends(auth.require_user)):
        return service.get_widget(dashboard_id, widget_id, user.id)

    @router.patch("/{dashboard_id}/widgets/{widget_id}", response_model=DashboardDetail)
    def update_widget(
        dashboard_id: str,
        widget_id: str,
        body: DashboardWidgetUpdate,
        user: PublicUser = Depends(auth.require_user),
    ):
        return service.update_widget(dashboard_id, widget_id, body, user.id)

    @router.delete("/{dashboard_id}/widgets/{widget_id}", response_model=DashboardDetail)
    def delete_widget(
        dashboard_id: str,
        widget_id: str,
        expected_revision: int = Query(ge=1),
        user: PublicUser = Depends(auth.require_user),
    ):
        return service.delete_widget(dashboard_id, widget_id, expected_revision, user.id)

    return router
