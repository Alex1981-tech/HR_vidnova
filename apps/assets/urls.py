from django.urls import path

# HR-нативні в'юхи активів (після консолідації — читають з HR-моделей, без cmms_client).
from .asset_api import (
    AssetDetailView,
    AssetListView,
    AssetOptionsView,
    AssetOwnershipHistoryView,
    AssignResponsibleView,
    EntrustedAssetsView,
    PhysicalLocationApplyView,
    PhysicalLocationDetailView,
    PhysicalLocationListView,
)

urlpatterns = [
    path("", AssetListView.as_view(), name="asset-list"),
    path("options/", AssetOptionsView.as_view(), name="asset-options"),
    path("entrusted/", EntrustedAssetsView.as_view(), name="asset-entrusted"),
    # Фізична структура (tree-builder) — перед catch-all <int:asset_id>.
    path("physical-locations/", PhysicalLocationListView.as_view(), name="physical-location-list"),
    path("physical-locations/<int:node_id>/", PhysicalLocationDetailView.as_view(), name="physical-location-detail"),
    path("physical-locations/<int:node_id>/apply/", PhysicalLocationApplyView.as_view(), name="physical-location-apply"),
    path("<int:asset_id>/responsible/", AssignResponsibleView.as_view(), name="asset-assign-responsible"),
    path("<int:asset_id>/ownership-history/", AssetOwnershipHistoryView.as_view(), name="asset-ownership-history"),
    path("<int:asset_id>/", AssetDetailView.as_view(), name="asset-detail"),
]
