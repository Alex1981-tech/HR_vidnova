from django.urls import path

from .views import AssetListView, AssetOptionsView, AssignResponsibleView

urlpatterns = [
    path("", AssetListView.as_view(), name="asset-list"),
    path("options/", AssetOptionsView.as_view(), name="asset-options"),
    path("<int:asset_id>/responsible/", AssignResponsibleView.as_view(), name="asset-assign-responsible"),
]
