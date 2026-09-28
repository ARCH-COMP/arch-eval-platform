from django.urls import path

from . import views

urlpatterns = [
    path("secret-data/", views.SecretDatasetListCreateView.as_view(), name="secret-dataset-list"),
    path("secret-data/<int:pk>/", views.SecretDatasetDetailView.as_view(), name="secret-dataset-detail"),
    path("secret-data/<str:category>/download", views.secret_dataset_download, name="secret-dataset-download"),
]
