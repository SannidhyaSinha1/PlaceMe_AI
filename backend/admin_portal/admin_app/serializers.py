from rest_framework import serializers

from .models import Announcement, ManualOpportunity


class ManualOpportunitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ManualOpportunity
        fields = "__all__"
        read_only_fields = ["id", "created_at", "source"]

    def create(self, validated_data):
        validated_data["source"] = "manual"
        return super().create(validated_data)


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ["id", "title", "body", "created_by", "created_at"]
        read_only_fields = ["id", "created_at", "created_by"]
