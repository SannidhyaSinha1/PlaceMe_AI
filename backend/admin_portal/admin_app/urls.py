from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AnnouncementViewSet, EngagementView, ManualOpportunityViewSet

router = DefaultRouter()
router.register("opportunities", ManualOpportunityViewSet, basename="opportunity")
router.register("announcements", AnnouncementViewSet, basename="announcement")

urlpatterns = [
    path("engagement", EngagementView.as_view(), name="engagement"),
    path("", include(router.urls)),
]
