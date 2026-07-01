from django.urls import path

from .views import (
    AssetDetailApiView,
    AssetListView,
    AssetOptionsView,
    AssetOwnershipHistoryView,
    AssetPhotoProxyView,
    AssetZoneApplyView,
    AssetZoneDetailView,
    AssetZoneListView,
    AssetZoneOptionsView,
    AssignResponsibleView,
)

urlpatterns = [
    path("", AssetListView.as_view(), name="asset-list"),
    path("options/", AssetOptionsView.as_view(), name="asset-options"),
    path("photo/", AssetPhotoProxyView.as_view(), name="asset-photo"),
    # Зони відповідальності (перед catch-all <int:asset_id>).
    path("zones/", AssetZoneListView.as_view(), name="asset-zone-list"),
    path("zones/options/", AssetZoneOptionsView.as_view(), name="asset-zone-options"),
    path("zones/<int:zone_id>/", AssetZoneDetailView.as_view(), name="asset-zone-detail"),
    path("zones/<int:zone_id>/apply/", AssetZoneApplyView.as_view(), name="asset-zone-apply"),
    path("<int:asset_id>/responsible/", AssignResponsibleView.as_view(), name="asset-assign-responsible"),
    path("<int:asset_id>/ownership-history/", AssetOwnershipHistoryView.as_view(), name="asset-ownership-history"),
    path("<int:asset_id>/", AssetDetailApiView.as_view(), name="asset-detail"),
]
