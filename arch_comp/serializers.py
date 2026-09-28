from rest_framework import serializers

from .models import SecretDataset


class SecretDatasetSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = SecretDataset
        fields = ["id", "category", "season", "archive", "uploaded_at", "uploaded_by"]
        read_only_fields = ["id", "uploaded_at", "uploaded_by"]
        validators = []
