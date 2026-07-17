from django.db import models
from movies.models import Movie


class Recommendation(models.Model):
    """
    Cache hasil rekomendasi per user dataset, supaya tidak perlu hitung ulang
    setiap kali halaman admin "Recommendation" dibuka.

    method menjelaskan strategi yang dipakai untuk user tsb:
    - genre_favorit   : user dengan riwayat rating cukup -> rekomendasi
                         berdasar genre yang paling sering ia rating tinggi
    - user_baru       : user yang sama sekali belum ada di tabel Rating
                         (cold-start) -> direkomendasikan film top rated
    - rating_sekali   : user yang baru memberi 1 rating -> rekomendasi
                         film mirip (genre yang sama) dengan film tsb
    - top_rated       : fallback umum, film dengan rata-rata rating tertinggi
    """

    METHOD_CHOICES = [
        ("genre_favorit", "Genre Favorit"),
        ("user_baru", "User Baru (Cold Start)"),
        ("rating_sekali", "Rating Satu Kali"),
        ("top_rated", "Top Rated"),
    ]

    user_id = models.IntegerField(db_index=True)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="recommended_to")
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    score = models.FloatField(default=0)
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user_id", "movie", "method")
        ordering = ["-score"]

    def __str__(self):
        return f"user {self.user_id} -> {self.movie.title} ({self.method})"
