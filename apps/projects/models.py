from django.db import models
from django.utils import timezone


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Project(TimestampedModel):
    """Проєкт для обліку часу (time tracking). Учасники — співробітники (M2M).

    Per-project облік годин у MVP не реалізовано; модель тримає лише склад
    учасників, назву, емодзі та стан архівації.
    """

    name = models.CharField(max_length=180)
    emoji = models.CharField(max_length=16, blank=True, default="📁")
    is_archived = models.BooleanField(default=False, db_index=True)
    order = models.PositiveIntegerField(default=0, db_index=True)
    members = models.ManyToManyField(
        "employees.Employee", related_name="projects", blank=True
    )
    legacy_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self) -> str:
        return self.name


class TimeEntry(TimestampedModel):
    """Запис відстеження часу: робота співробітника над проєктом (старт/стоп)."""

    employee = models.ForeignKey("employees.Employee", on_delete=models.CASCADE, related_name="time_entries")
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="time_entries")
    comment = models.TextField(blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"{self.employee_id} · {self.project_id} · {self.started_at:%Y-%m-%d %H:%M}"

    @property
    def duration_seconds(self) -> int:
        end = self.ended_at or timezone.now()
        return max(0, int((end - self.started_at).total_seconds()))

    @property
    def is_running(self) -> bool:
        return self.ended_at is None
