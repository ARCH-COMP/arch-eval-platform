from pathlib import Path

from django.http import FileResponse
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from comp_eval_platform.core.api import IsAdmin

from .models import SecretDataset, current_season
from .serializers import SecretDatasetSerializer


class SecretDatasetListCreateView(generics.ListCreateAPIView):
    queryset = SecretDataset.objects.all().order_by("-uploaded_at", "category", "season")
    serializer_class = SecretDatasetSerializer
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.validated_data["category"]
        season = serializer.validated_data["season"]
        archive = serializer.validated_data["archive"]

        dataset = SecretDataset.objects.filter(category=category, season=season).first()
        if dataset is None:
            dataset = SecretDataset(category=category, season=season, uploaded_by=request.user)
            dataset.archive = archive
            dataset.save()
            return Response(self.get_serializer(dataset).data, status=201)

        old_archive_name = dataset.archive.name
        dataset.archive = archive
        dataset.uploaded_by = request.user
        dataset.save()
        if old_archive_name and old_archive_name != dataset.archive.name:
            dataset.archive.storage.delete(old_archive_name)
        return Response(self.get_serializer(dataset).data, status=200)


class SecretDatasetDetailView(generics.DestroyAPIView):
    queryset = SecretDataset.objects.all()
    serializer_class = SecretDatasetSerializer
    permission_classes = [IsAdmin]


@api_view(["GET"])
@permission_classes([AllowAny])
def secret_dataset_download(request, category):
    dataset = SecretDataset.objects.filter(category=category, season=current_season()).first()
    if dataset is None or not dataset.archive or not dataset.archive.storage.exists(dataset.archive.name):
        return Response(status=404)
    response = FileResponse(dataset.archive.open("rb"), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{Path(dataset.archive.name).name}"'
    return response
