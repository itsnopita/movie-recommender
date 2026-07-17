from django.db import models
from django.conf import settings
from movies.models import Movie


class Tag(models.Model):
    """
    Mengikuti tags.csv MovieLens: userId, movieId, tag, timestamp.

    Sama seperti Rating: user_id (dataset) dan user (akun login asli) dua-duanya
    ada, salah satu bisa kosong tergantung sumber datanya.
    """

    user_id = models.IntegerField(db_index=True, null=True, blank=True)
    account_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="tags",
    )
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="tags")
    tag = models.CharField(max_length=150)
    timestamp = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.tag