from django.conf import settings
from django.db import models


class UserPreference(models.Model):
    class Language(models.TextChoices):
        EN = "en", "English"
        UK = "uk", "Українська"
        PL = "pl", "Polski"

    class Theme(models.TextChoices):
        LIGHT = "light", "Light"
        DARK = "dark", "Dark"
        AUTO = "auto", "Auto"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hr_preferences")
    language = models.CharField(max_length=8, choices=Language.choices, default=Language.UK)
    theme = models.CharField(max_length=12, choices=Theme.choices, default=Theme.LIGHT)
    time_zone = models.CharField(max_length=80, default="Europe/Kyiv")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user_id"]

    def __str__(self) -> str:
        return f"{self.user_id} preferences"
