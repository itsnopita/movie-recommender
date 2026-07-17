"""
Ambil URL poster film dari TMDB (The Movie Database) menggunakan tmdb_id
yang sudah tersimpan di tabel Movie (hasil import dari links.csv).

Persiapan:
    1. Daftar & buat API key di https://www.themoviedb.org/settings/api
    2. Set environment variable TMDB_API_KEY, atau isi langsung di
       settings.py: TMDB_API_KEY = "xxxxxxxx"

Cara pakai:
    python manage.py fetch_posters
    python manage.py fetch_posters --limit 200      # coba dulu sebagian
    python manage.py fetch_posters --only-missing    # default: True
"""

import time

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from movies.models import Movie

TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
TMDB_MOVIE_URL = "https://api.themoviedb.org/3/movie/{tmdb_id}"


class Command(BaseCommand):
    help = "Ambil poster film dari TMDB berdasarkan tmdb_id"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Batasi jumlah film yang diproses (0 = semua)",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Proses ulang semua film, termasuk yang sudah punya poster",
        )
        parser.add_argument(
            "--sleep",
            type=float,
            default=0.05,
            help="Jeda antar request (detik) supaya tidak kena rate limit",
        )

    def handle(self, *args, **options):
        api_key = getattr(settings, "TMDB_API_KEY", "") or ""
        if not api_key:
            raise CommandError(
                "TMDB_API_KEY belum diset. Tambahkan di settings.py atau "
                "environment variable TMDB_API_KEY."
            )

        qs = Movie.objects.exclude(tmdb_id__isnull=True).exclude(tmdb_id="")
        if not options["all"]:
            from django.db.models import Q
            missing_poster = Q(poster__isnull=True) | Q(poster="")
            missing_overview = Q(overview__isnull=True) | Q(overview="")
            qs = qs.filter(missing_poster | missing_overview)

        if options["limit"]:
            qs = qs[: options["limit"]]

        total = qs.count()
        self.stdout.write(f"Memproses {total} film...")

        updated, failed = 0, 0
        session = requests.Session()

        for i, movie in enumerate(qs.iterator(), start=1):
            tmdb_id = str(movie.tmdb_id).strip()
            if not tmdb_id:
                continue
            try:
                resp = session.get(
                    TMDB_MOVIE_URL.format(tmdb_id=tmdb_id),
                    params={"api_key": api_key, "language": "id-ID"},
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    poster_path = data.get("poster_path")
                    overview = data.get("overview")

                    fields_to_update = []
                    if poster_path:
                        movie.poster = TMDB_IMAGE_BASE + poster_path
                        fields_to_update.append("poster")
                    if overview:
                        movie.overview = overview
                        fields_to_update.append("overview")

                    if fields_to_update:
                        movie.save(update_fields=fields_to_update)
                        updated += 1
                    else:
                        failed += 1
                else:
                    failed += 1
            except requests.RequestException:
                failed += 1

            if i % 100 == 0:
                self.stdout.write(f"  ... {i}/{total} diproses")

            time.sleep(options["sleep"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Selesai. Poster diupdate: {updated}, gagal/kosong: {failed}"
            )
        )
