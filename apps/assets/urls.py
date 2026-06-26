from django.urls import path

from .views import AssetListView, AssetOptionsView, AssetPhotoProxyView, AssignResponsibleView

urlpatterns = [
    path("", AssetListView.as_view(), name="asset-list"),
    path("options/", AssetOptionsView.as_view(), name="asset-options"),
    path("photo/", AssetPhotoProxyView.as_view(), name="asset-photo"),
    path("<int:asset_id>/responsible/", AssignResponsibleView.as_view(), name="asset-assign-responsible"),
]
