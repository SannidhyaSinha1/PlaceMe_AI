"""Django models mapped onto the shared database (managed=False).

The relational schema is owned by db/schema.sql + the FastAPI SQLAlchemy
models; Django reads/writes the same tables but never migrates them. Django
manages only its own auth/admin tables.
"""

from django.db import models


class ManualOpportunity(models.Model):
    """Placement-staff-uploaded opportunities (the `opportunities` table)."""

    company_name = models.CharField(max_length=255)
    role = models.CharField(max_length=255, blank=True, null=True)
    opportunity_type = models.CharField(max_length=50, default="Other")
    description = models.TextField(blank=True, null=True)
    deadline = models.DateField(blank=True, null=True)
    salary_stipend = models.CharField(max_length=100, blank=True, null=True)
    job_location = models.CharField(max_length=255, blank=True, null=True)
    required_skills = models.JSONField(default=list, blank=True)
    eligibility_criteria = models.JSONField(default=dict, blank=True)
    source_email_id = models.CharField(max_length=255, blank=True, null=True)
    source = models.CharField(max_length=20, default="manual")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "opportunities"
        ordering = ["-created_at"]
        verbose_name_plural = "Manual opportunities"

    def __str__(self):
        return f"{self.company_name} — {self.role or self.opportunity_type}"


class Announcement(models.Model):
    """Broadcasts to all students (the `announcements` table)."""

    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, null=True)
    created_by = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "announcements"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
