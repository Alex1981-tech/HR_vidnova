"""Сигнали активів: запис подій власності (локація/відповідальний/інженер) для історії."""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Asset, AssetOwnershipEvent


@receiver(pre_save, sender=Asset)
def _capture_ownership_change(sender, instance, **kwargs):
    if not instance.pk:
        instance._ownership_changed = True
        instance._is_creation = True
        return
    old = Asset.objects.filter(pk=instance.pk).only(
        "location_id", "responsible_id", "engineer_id"
    ).first()
    if old is None:
        instance._ownership_changed = True
        instance._is_creation = True
        return
    instance._ownership_changed = (
        old.location_id != instance.location_id
        or old.responsible_id != instance.responsible_id
        or old.engineer_id != instance.engineer_id
    )
    instance._is_creation = False


@receiver(post_save, sender=Asset)
def _write_ownership_event(sender, instance, created, **kwargs):
    if not getattr(instance, "_ownership_changed", False):
        return
    AssetOwnershipEvent.objects.create(
        asset=instance,
        location=instance.location,
        responsible=instance.responsible,
        engineer=instance.engineer,
        is_creation=bool(getattr(instance, "_is_creation", False) or created),
    )
