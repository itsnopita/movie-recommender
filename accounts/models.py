from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Data tambahan untuk User bawaan Django (khususnya foto profil admin)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    photo = models.ImageField(upload_to="avatars/", blank=True, null=True)

    def __str__(self):
        return f"Profile - {self.user.username}"
