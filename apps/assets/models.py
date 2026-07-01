from django.db import models


class PhysicalLocation(models.Model):
    """Фізична структура (HR — джерело істини): клініка → поверхи → кабінети.

    Синкається в CMMS locations (`cmms_location_id`). До вузлів (кабінет/поверх)
    привʼязуються департаменти; на вузол призначається інженер, якого «Застосувати»
    проставляє активам у субдереві.
    """

    KIND_CITY = "city"
    KIND_CLINIC = "clinic"
    KIND_FLOOR = "floor"
    KIND_CABINET = "cabinet"
    KIND_CHOICES = [
        (KIND_CITY, "Місто"),
        (KIND_CLINIC, "Клініка"),
        (KIND_FLOOR, "Поверх"),
        (KIND_CABINET, "Кабінет"),
    ]
    # Рівень у CMMS locations (city=0, clinic=1, floor=2, room=3).
    KIND_LEVEL = {KIND_CITY: 0, KIND_CLINIC: 1, KIND_FLOOR: 2, KIND_CABINET: 3}

    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    parent = models.ForeignKey(
        "self", null=True, blank=True, related_name="children", on_delete=models.CASCADE
    )
    order = models.IntegerField(default=0)

    # Звʼязок із CMMS locations для двобічного синку/матчингу.
    cmms_location_id = models.IntegerField(null=True, blank=True, db_index=True)

    departments = models.ManyToManyField(
        "employees.Department", blank=True, related_name="physical_locations"
    )

    # Призначений інженер — CMMS user.
    engineer_user_id = models.IntegerField(null=True, blank=True)
    engineer_name = models.CharField(max_length=200, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "asset_physical_locations"
        ordering = ["order", "name"]

    def __str__(self) -> str:
        return f"{self.get_kind_display()}: {self.name}"

    @property
    def level(self) -> int:
        return self.KIND_LEVEL.get(self.kind, 0)


class AssetResponsibilityZone(models.Model):
    """Зона відповідальності: скоуп (локація/департамент CMMS) + призначений інженер.

    HR — майстер зони; таргети (location_id/department_id) та інженер (user) живуть у CMMS.
    «Застосувати» проставляє engineer_id усім активам CMMS у межах скоупу.
    """

    SCOPE_LOCATION = "location"
    SCOPE_DEPARTMENT = "department"
    SCOPE_CHOICES = [
        (SCOPE_LOCATION, "Локація"),
        (SCOPE_DEPARTMENT, "Департамент"),
    ]

    name = models.CharField(max_length=200, blank=True)
    scope_type = models.CharField(max_length=20, choices=SCOPE_CHOICES)

    # CMMS location (будь-який рівень: клініка/поверх/кабінет) + денормалізований шлях.
    location_id = models.IntegerField(null=True, blank=True)
    location_name = models.CharField(max_length=300, blank=True)

    # CMMS department.
    department_id = models.IntegerField(null=True, blank=True)
    department_name = models.CharField(max_length=200, blank=True)

    # Призначений інженер — CMMS user.
    engineer_user_id = models.IntegerField(null=True, blank=True)
    engineer_name = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_applied_at = models.DateTimeField(null=True, blank=True)
    last_applied_count = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "asset_responsibility_zones"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        target = self.location_name or self.department_name or self.scope_type
        return f"{target} → {self.engineer_name or '—'}"
