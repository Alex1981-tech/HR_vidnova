from django.db import models
from django.utils import timezone


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

    # Призначений інженер зони — нативний HR-співробітник.
    engineer = models.ForeignKey(
        "employees.Employee", null=True, blank=True, related_name="zone_locations", on_delete=models.SET_NULL
    )

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


class AssetCategory(models.Model):
    """Категорія активу (дерево). Мігрується з CMMS categories."""

    name = models.CharField(max_length=200)
    parent = models.ForeignKey(
        "self", null=True, blank=True, related_name="children", on_delete=models.SET_NULL
    )
    path = models.CharField(max_length=600, blank=True)  # денормалізований category_path
    cmms_category_id = models.IntegerField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "asset_categories"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class AssetType(models.Model):
    """Тип активу. Мігрується з CMMS asset-types."""

    name = models.CharField(max_length=200)
    cmms_asset_type_id = models.IntegerField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "asset_types"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Asset(models.Model):
    """Актив (обладнання). HR — джерело істини після консолідації з CMMS.

    Локація/департамент/відповідальний/інженер — нативні FK у HR (без синку/id-мапінгу).
    """

    inventory_number = models.CharField(max_length=100, blank=True)
    name = models.CharField(max_length=300)
    status = models.CharField(max_length=50, blank=True)
    manufacturer = models.CharField(max_length=200, blank=True)

    category = models.ForeignKey(
        AssetCategory, null=True, blank=True, related_name="assets", on_delete=models.SET_NULL
    )
    asset_type = models.ForeignKey(
        AssetType, null=True, blank=True, related_name="assets", on_delete=models.SET_NULL
    )
    location = models.ForeignKey(
        PhysicalLocation, null=True, blank=True, related_name="assets", on_delete=models.SET_NULL
    )
    department = models.ForeignKey(
        "employees.Department", null=True, blank=True, related_name="assets", on_delete=models.SET_NULL
    )
    responsible = models.ForeignKey(
        "employees.Employee", null=True, blank=True, related_name="responsible_assets", on_delete=models.SET_NULL
    )
    engineer = models.ForeignKey(
        "employees.Employee", null=True, blank=True, related_name="engineer_assets", on_delete=models.SET_NULL
    )

    description = models.TextField(blank=True)
    tags = models.CharField(max_length=300, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    initial_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, blank=True)

    # Лінк на CMMS-актив для одноразової міграції/матчингу.
    cmms_asset_id = models.IntegerField(null=True, blank=True, db_index=True, unique=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "asset_registry"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.inventory_number} · {self.name}" if self.inventory_number else self.name


class AssetOwnershipEvent(models.Model):
    """Снапшот стану власності активу (локація+відповідальний+інженер) на момент зміни.

    Пишеться сигналами при зміні location/responsible/engineer активу. З цих подій
    збирається таблиця «Історія володіння» (нативно, без CMMS).
    """

    asset = models.ForeignKey(Asset, related_name="ownership_events", on_delete=models.CASCADE)
    changed_at = models.DateTimeField(default=timezone.now)
    location = models.ForeignKey(PhysicalLocation, null=True, blank=True, related_name="+", on_delete=models.SET_NULL)
    responsible = models.ForeignKey("employees.Employee", null=True, blank=True, related_name="+", on_delete=models.SET_NULL)
    engineer = models.ForeignKey("employees.Employee", null=True, blank=True, related_name="+", on_delete=models.SET_NULL)
    is_creation = models.BooleanField(default=False)

    class Meta:
        db_table = "asset_ownership_events"
        ordering = ["changed_at", "id"]


class AssetPhoto(models.Model):
    asset = models.ForeignKey(Asset, related_name="photos", on_delete=models.CASCADE)
    image = models.FileField(upload_to="assets/%Y/%m/", blank=True)
    content_type = models.CharField(max_length=60, blank=True)  # image/jpeg, video/mp4, …
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    cmms_photo_id = models.IntegerField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_video(self) -> bool:
        return self.content_type.startswith("video/")

    class Meta:
        db_table = "asset_photos"
        ordering = ["order", "id"]


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
