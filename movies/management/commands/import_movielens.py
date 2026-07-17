"""
Import dataset MovieLens (ml-latest-small) ke database.

Cara pakai:
    1. Download "ml-latest-small.zip" dari https://grouplens.org/datasets/movielens/
    2. Ekstrak, lalu taruh movies.csv, ratings.csv, tags.csv, links.csv
       di dalam folder  movie_recommender/dataset/
    3. Jalankan:
         python manage.py import_movielens

    Bisa juga arahkan ke folder lain:
         python manage.py import_movielens --path /lokasi/folder/dataset
"""

import csv
import re
from datetime import datetime, timezone

from django.core.management.base import BaseCommand
from django.conf import settings

from movies.models import Movie, Genre
from ratings.models import Rating
from tags.models import Tag


YEAR_RE = re.compile(r"\((\d{4})\)\s*$")


def parse_year(title: str):
    match = YEAR_RE.search(title)
    return int(match.group(1)) if match else None


def parse_timestamp(value: str):
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (ValueError, OSError):
        return None


class Command(BaseCommand):
    help = "Import dataset MovieLens (movies.csv, links.csv, ratings.csv, tags.csv)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            type=str,
            default=str(settings.BASE_DIR / "dataset"),
            help="Folder yang berisi movies.csv, links.csv, ratings.csv, tags.csv",
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Kosongkan dulu tabel Movie/Genre/Rating/Tag sebelum import",
        )

    def handle(self, *args, **options):
        from pathlib import Path

        folder = Path(options["path"])
        if not folder.exists():
            self.stderr.write(self.style.ERROR(f"Folder tidak ditemukan: {folder}"))
            return

        if options["flush"]:
            Rating.objects.all().delete()
            Tag.objects.all().delete()
            Movie.objects.all().delete()
            Genre.objects.all().delete()
            self.stdout.write("Tabel lama dikosongkan.")

        self.import_movies(folder / "movies.csv")
        self.import_links(folder / "links.csv")
        self.import_ratings(folder / "ratings.csv")
        self.import_tags(folder / "tags.csv")

        self.stdout.write(self.style.SUCCESS("Import dataset MovieLens selesai!"))

    # ------------------------------------------------------------------ #

    def import_movies(self, path):
        if not path.exists():
            self.stderr.write(self.style.WARNING(f"Lewati: {path} tidak ditemukan"))
            return

        genre_cache = {}
        movies_to_create = []
        movie_genre_map = {}

        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                movie_id = int(row["movieId"])
                title = row["title"]
                genres_raw = row["genres"]

                movies_to_create.append(
                    Movie(
                        id=movie_id,
                        title=title,
                        year=parse_year(title),
                        genres_raw=genres_raw,
                    )
                )

                if genres_raw and genres_raw != "(no genres listed)":
                    genre_names = genres_raw.split("|")
                    movie_genre_map[movie_id] = genre_names
                    for g in genre_names:
                        genre_cache.setdefault(g, None)

        # Bulk-create genre dulu
        existing = {g.name: g for g in Genre.objects.all()}
        new_genres = [Genre(name=n) for n in genre_cache if n not in existing]
        Genre.objects.bulk_create(new_genres, ignore_conflicts=True)
        all_genres = {g.name: g for g in Genre.objects.all()}

        Movie.objects.bulk_create(movies_to_create, ignore_conflicts=True, batch_size=2000)
        self.stdout.write(f"  Movie diimport: {len(movies_to_create)}")

        # Set relasi M2M genre per movie
        through_model = Movie.genres.through
        links = []
        for movie_id, genre_names in movie_genre_map.items():
            for name in genre_names:
                genre = all_genres.get(name)
                if genre:
                    links.append(through_model(movie_id=movie_id, genre_id=genre.id))
        through_model.objects.bulk_create(links, ignore_conflicts=True, batch_size=5000)
        self.stdout.write(f"  Genre diimport: {len(all_genres)}")

    def import_links(self, path):
        if not path.exists():
            self.stderr.write(self.style.WARNING(f"Lewati: {path} tidak ditemukan"))
            return

        updates = []
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                movie_id = int(row["movieId"])
                imdb_id = row.get("imdbId") or None
                tmdb_id = row.get("tmdbId") or None
                updates.append(Movie(id=movie_id, imdb_id=imdb_id, tmdb_id=tmdb_id))

        Movie.objects.bulk_update(
            updates,
            ["imdb_id", "tmdb_id"],
            batch_size=2000,
        )
        self.stdout.write(f"  Link IMDB/TMDB diupdate: {len(updates)}")

    def import_ratings(self, path):
        if not path.exists():
            self.stderr.write(self.style.WARNING(f"Lewati: {path} tidak ditemukan"))
            return

        valid_ids = set(Movie.objects.values_list("id", flat=True))
        batch = []
        total = 0
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                movie_id = int(row["movieId"])
                if movie_id not in valid_ids:
                    continue
                batch.append(
                    Rating(
                        user_id=int(row["userId"]),
                        movie_id=movie_id,
                        rating=float(row["rating"]),
                        timestamp=parse_timestamp(row.get("timestamp")),
                    )
                )
                if len(batch) >= 5000:
                    Rating.objects.bulk_create(batch)
                    total += len(batch)
                    batch = []
            if batch:
                Rating.objects.bulk_create(batch)
                total += len(batch)

        self.stdout.write(f"  Rating diimport: {total}")

    def import_tags(self, path):
        if not path.exists():
            self.stderr.write(self.style.WARNING(f"Lewati: {path} tidak ditemukan"))
            return

        valid_ids = set(Movie.objects.values_list("id", flat=True))
        batch = []
        total = 0
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                movie_id = int(row["movieId"])
                if movie_id not in valid_ids:
                    continue
                batch.append(
                    Tag(
                        user_id=int(row["userId"]),
                        movie_id=movie_id,
                        tag=row["tag"],
                        timestamp=parse_timestamp(row.get("timestamp")),
                    )
                )
                if len(batch) >= 5000:
                    Tag.objects.bulk_create(batch)
                    total += len(batch)
                    batch = []
            if batch:
                Tag.objects.bulk_create(batch)
                total += len(batch)

        self.stdout.write(f"  Tag diimport: {total}")
