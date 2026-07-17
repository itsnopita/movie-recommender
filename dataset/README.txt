Taruh 4 file ini di folder ini (dari ml-latest-small.zip, https://grouplens.org/datasets/movielens/):
- movies.csv
- links.csv
- ratings.csv
- tags.csv

Lalu jalankan dari root project:
    python manage.py makemigrations
    python manage.py migrate
    python manage.py import_movielens --flush
