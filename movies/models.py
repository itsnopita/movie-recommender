from django.conf import settings
from django.db import models


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Movie(models.Model):
    """
    Mengikuti struktur dataset MovieLens (movies.csv + links.csv):
    - id        -> movieId pada MovieLens (dipakai apa adanya sebagai PK,
                   bukan auto-increment, supaya konsisten dengan dataset)
    - title     -> judul film, biasanya sudah termasuk tahun rilis, contoh:
                   "Toy Story (1995)"
    - genres_raw -> string genre asli dari movies.csv (dipisah "|"), disimpan
                   untuk referensi/import ulang, tapi relasi sebenarnya ada
                   di field genres (ManyToMany ke Genre)
    - imdb_id / tmdb_id -> dari links.csv, ditampilkan di kolom IMDB & TMDB
                   pada halaman admin
    """

    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=255)
    year = models.IntegerField(blank=True, null=True)
    overview = models.TextField(blank=True, null=True)
    poster = models.URLField(blank=True, null=True)

    genres_raw = models.CharField(max_length=255, blank=True, default="")
    genres = models.ManyToManyField(Genre, related_name="movies", blank=True)

    imdb_id = models.CharField(max_length=20, blank=True, null=True)
    tmdb_id = models.CharField(max_length=20, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["id"]


class ContactMessage(models.Model):
    """Pesan yang dikirim user (harus login dulu) ke developer lewat form Contact."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contact_messages",
    )
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.email} - {self.created_at:%Y-%m-%d %H:%M}"