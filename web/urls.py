from django.urls import path

from . import views
from . import api_views


urlpatterns = [
    path('', views.home, name='home'),
    path('api/datasets/upload', api_views.dataset_upload, name='api_dataset_upload'),
    path('api/datasets/<str:dataset_id>/clean', api_views.dataset_clean, name='api_dataset_clean'),
    path('api/datasets/<str:dataset_id>/train', api_views.dataset_train, name='api_dataset_train'),
    path('api/datasets/<str:dataset_id>/export', api_views.dataset_export, name='api_dataset_export'),
    path('api/datasets/<str:dataset_id>/stats', api_views.dataset_stats, name='api_dataset_stats'),
    path('api/model-runs/<str:model_run_id>/predict', api_views.model_predict, name='api_model_predict'),
]
