"""DRF views: manual opportunity CRUD, announcements, engagement analytics."""

from django.db import connection
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Announcement, ManualOpportunity
from .serializers import AnnouncementSerializer, ManualOpportunitySerializer


class ManualOpportunityViewSet(viewsets.ModelViewSet):
    queryset = ManualOpportunity.objects.all()
    serializer_class = ManualOpportunitySerializer
    permission_classes = [IsAdminUser]


class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.get_username())


def _scalar(sql: str, default=0):
    """Run a COUNT-style query, tolerating a missing table in fresh dev DBs."""
    try:
        with connection.cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone()
            return row[0] if row else default
    except Exception:
        return default


def _rows(sql: str):
    try:
        with connection.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()
    except Exception:
        return []


class EngagementView(APIView):
    """Aggregate student engagement across the shared tables (read-only)."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        status_breakdown = {
            row[0]: row[1]
            for row in _rows("SELECT status, COUNT(*) FROM applications GROUP BY status")
        }
        type_breakdown = {
            row[0]: row[1]
            for row in _rows(
                "SELECT opportunity_type, COUNT(*) FROM opportunities GROUP BY opportunity_type"
            )
        }
        return Response(
            {
                "total_students": _scalar("SELECT COUNT(*) FROM users"),
                "total_opportunities": _scalar("SELECT COUNT(*) FROM opportunities"),
                "total_applications": _scalar("SELECT COUNT(*) FROM applications"),
                "offers": _scalar(
                    "SELECT COUNT(*) FROM applications WHERE status = 'Offer Received'"
                ),
                "gmail_connected": _scalar(
                    "SELECT COUNT(*) FROM users WHERE gmail_refresh_token IS NOT NULL"
                ),
                "applications_by_status": status_breakdown,
                "opportunities_by_type": type_breakdown,
            }
        )
