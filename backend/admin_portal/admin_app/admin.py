from django.contrib import admin

from .models import Announcement, ManualOpportunity


@admin.register(ManualOpportunity)
class ManualOpportunityAdmin(admin.ModelAdmin):
    list_display = ("company_name", "role", "opportunity_type", "deadline", "source")
    list_filter = ("opportunity_type", "source")
    search_fields = ("company_name", "role")


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "created_by", "created_at")
    search_fields = ("title", "body")

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user.get_username()
        super().save_model(request, obj, form, change)
