from django.db import models
from django.conf import settings
from movies.models import Movie


class Rating(models.Model):
    """
    Mengikuti ratings.csv MovieLens: userId, movieId, rating, timestamp.

    Ada 2 sumber data di tabel ini:
    - user_id (IntegerField)  -> ID user dari dataset MovieLens (buat rekomendasi
                                 berbasis dataset besar / cold-start / top rated).
    - user (ForeignKey)       -> akun login asli (auth.User) di web ini. Diisi saat
                                 user yang benar-benar login memberi rating lewat
                                 halaman detail film.

    Salah satu dari keduanya boleh kosong, tapi setidaknya salah satunya wajib diisi.
    """

    user_id = models.IntegerField(db_index=True, null=True, blank=True)
    account_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ratings",
    )
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="ratings")
    rating = models.FloatField()
    timestamp = models.DateTimeField(blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=["user_id", "movie"])]
        constraints = [
            models.UniqueConstraint(
                fields=["account_user", "movie"], name="unique_account_user_movie_rating"
            ),
        ]

    def __str__(self):
        who = self.account_user.username if self.account_user_id else f"user {self.user_id}"
        return f"{who} - {self.movie.title} ({self.rating})"