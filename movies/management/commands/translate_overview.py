"""
Terjemahkan sinopsis (overview) film yang masih dalam Bahasa Inggris ke
Bahasa Indonesia.

Kenapa ada yang masih Inggris? Karena `fetch_posters` sudah minta
overview bahasa Indonesia ke TMDB (language=id-ID), tapi TMDB tidak punya
terjemahan Indonesia untuk semua film -> kalau tidak ada, TMDB otomatis
fallback mengirim overview bahasa Inggris.

Command ini mendeteksi overview mana yang kemungkinan besar masih Inggris
(pakai library `langdetect`), lalu menerjemahkannya pakai Google Translate
(lewat library `deep-translator`, gratis & tanpa API key).

Instalasi paket yang dibutuhkan (sekali saja):
    pip install langdetect deep-translator

Cara pakai:
    python manage.py translate_overview
    python manage.py translate_overview --limit 200      # coba sebagian dulu
    python manage.py translate_overview --sleep 0.3       # jeda antar request
"""

import time

from django.core.management.base import BaseCommand, CommandError

from movies.models import Movie


class Command(BaseCommand):
    help = "Terjemahkan overview film yang masih Bahasa Inggris ke Bahasa Indonesia"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, default=0,
            help="Batasi jumlah film yang diproses (0 = semua)",
        )
        parser.add_argument(
            "--sleep", type=float, default=0.2,
            help="Jeda antar request ke Google Translate (detik)",
        )

    def handle(self, *args, **options):
        try:
            from langdetect import detect
        except ImportError:
            raise CommandError(
                "Package 'langdetect' belum terinstall. Jalankan:\n"
                "    pip install langdetect deep-translator"
            )
        try:
            from deep_translator import GoogleTranslator
        except ImportError:
            raise CommandError(
                "Package 'deep-translator' belum terinstall. Jalankan:\n"
                "    pip install langdetect deep-translator"
            )

        translator = GoogleTranslator(source="en", target="id")

        qs = Movie.objects.exclude(overview__isnull=True).exclude(overview="")
        if options["limit"]:
            qs = qs[: options["limit"]]

        total = qs.count()
        self.stdout.write(f"Mengecek {total} film...")

        translated, skipped, failed = 0, 0, 0

        for i, movie in enumerate(qs.iterator(), start=1):
            text = movie.overview.strip()

            try:
                lang = detect(text)
            except Exception:
                lang = None

            if lang != "en":
                skipped += 1
            else:
                try:
                    new_text = translator.translate(text)
                    if new_text:
                        movie.overview = new_text
                        movie.save(update_fields=["overview"])
                        translated += 1
                        self.stdout.write(f"  [{i}/{total}] '{movie.title}' -> diterjemahkan")
                    else:
                        failed += 1
                except Exception as e:
                    failed += 1
                    self.stdout.write(self.style.WARNING(f"  Gagal '{movie.title}': {e}"))

                time.sleep(options["sleep"])

            if i % 100 == 0:
                self.stdout.write(f"  ... {i}/{total} diproses")

        self.stdout.write(self.style.SUCCESS(
            f"Selesai. Diterjemahkan: {translated}, sudah Indonesia (skip): {skipped}, gagal: {failed}"
        ))
