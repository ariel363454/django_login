from django.urls import path
from .views import (
    login_api,
    test_admin_api,
    dashboard_page,
    search_parking_lots,
    delete_parking_lot,
    login_page,
    update_parking_lot,
    create_parking_lot,
    update_history_api,
    admin_action_logs_api,
    area_list_api,
    logs_page
)

urlpatterns = [
    path("login/", login_api),
    path("test-admin/", test_admin_api),
    path("dashboard/", dashboard_page),
    path("search/", search_parking_lots),
    path("parking-lots/<str:lot_id>/delete/", delete_parking_lot),
    path("login-page/", login_page),
    path("parking-lots/<str:lot_id>/update/", update_parking_lot),
    path("parking-lots/create/",create_parking_lot),
    path("update-history/", update_history_api),
    path("admin-action-logs/", admin_action_logs_api),
    path("areas/", area_list_api),
    path("logs/", logs_page),
]