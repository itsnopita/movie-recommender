"""
Logic rekomendasi movie.

Mendukung 2 sumber identitas "rater" pada tabel Rating/Tag:
- user_id (int)        -> user dataset MovieLens (kolom `user_id`)
- account_user_id (int)-> akun login asli di web ini (kolom `account_user`)

Setiap fungsi di bawah menerima salah satu dari keduanya (isi salah satu,
yang lain biarkan None) sehingga logic yang sama persis dipakai untuk:
- Panel admin (selalu pakai `user_id` dataset)
- Halaman "Rekomendasi Saya" milik user yang login (pakai `account_user_id`)

Strategi yang dipakai, urut berdasarkan jumlah rating yang sudah dimiliki:
1. user_baru      -> 0 rating (cold start): movie top rated
2. rating_sekali  -> 1 rating: movie lain dengan genre yang sama
3. hybrid         -> >=2 rating: gabungan
     a) Content-Based Filtering  -> Jaccard Similarity antara genre yang
        disukai user dengan genre tiap movie kandidat
     b) Collaborative Filtering  -> Pearson Correlation antara pola rating
        user dengan user/akun lain, lalu prediksi rating movie yang belum
        pernah ia tonton dari "tetangga" yang paling mirip
   Skor content-based & collaborative dinormalisasi (0..1) lalu digabung
   jadi satu skor akhir (hybrid_score).
4. top_rated      -> fallback kalau hybrid tidak menghasilkan apa-apa
   (misal genre user tidak match movie manapun & tidak ada user yang mirip)
"""

import math
from collections import Counter, defaultdict

from django.db.models import Avg, Count, Q

from movies.models import Movie, Genre
from ratings.models import Rating


MIN_RATINGS_FOR_TOP = 5     # minimal jumlah rating supaya layak masuk "top rated"
DEFAULT_LIMIT = 10
LIKE_THRESHOLD = 4.0        # rating >= ini dianggap "disukai" user
MIN_COMMON_MOVIES = 3       # minimal film yang sama-sama dirating utk hitung Pearson
MAX_NEIGHBORS = 30          # batasi jumlah "tetangga" paling mirip yang dipakai
CONTENT_WEIGHT = 0.5
COLLAB_WEIGHT = 0.5


# --------------------------------------------------------------------- #
# Helper identitas: unify dataset user_id & account_user_id
# --------------------------------------------------------------------- #

def _rating_filter_kwargs(user_id=None, account_user_id=None):
    if account_user_id is not None:
        return {"account_user_id": account_user_id}
    return {"user_id": user_id}


def get_ratings_queryset(user_id=None, account_user_id=None):
    return Rating.objects.filter(**_rating_filter_kwargs(user_id, account_user_id))


def get_ratings_dict(user_id=None, account_user_id=None):
    """{movie_id: rating_value} milik satu user (dataset ATAU akun asli)."""
    qs = get_ratings_queryset(user_id, account_user_id).values_list("movie_id", "rating")
    return dict(qs)


def get_rating_count(user_id=None, account_user_id=None):
    return get_ratings_queryset(user_id, account_user_id).count()


# Nama lama dipertahankan (dipanggil dari admin_views.py)
def get_user_rating_count(user_id=None, account_user_id=None):
    return get_rating_count(user_id=user_id, account_user_id=account_user_id)


# --------------------------------------------------------------------- #
# Top rated (dipakai utk menu "Rate" & sebagai fallback umum)
# --------------------------------------------------------------------- #

def top_rated(limit=DEFAULT_LIMIT, min_ratings=MIN_RATINGS_FOR_TOP, exclude_ids=None):
    qs = Movie.objects.annotate(
        avg_rating=Avg("ratings__rating"),
        rating_count=Count("ratings"),
    ).filter(rating_count__gte=min_ratings)

    if exclude_ids:
        qs = qs.exclude(id__in=exclude_ids)

    return list(qs.order_by("-avg_rating", "-rating_count")[:limit])


def recommend_for_new_user(limit=DEFAULT_LIMIT):
    """Strategi cold-start: user belum pernah rating sama sekali."""
    return top_rated(limit=limit)


def recommend_by_single_rating(user_id=None, account_user_id=None, limit=DEFAULT_LIMIT):
    """
    Strategi untuk user yang baru kasih 1 rating: rekomendasikan film lain
    yang genre-nya sama dengan satu-satunya film yang sudah ia rating.
    """
    rating = get_ratings_queryset(user_id, account_user_id).select_related("movie").first()
    if not rating:
        return recommend_for_new_user(limit=limit), None

    movie = rating.movie
    genres = movie.genres.all()

    if not genres:
        return top_rated(limit=limit), movie

    recs = (
        Movie.objects.filter(genres__in=genres)
        .exclude(id=movie.id)
        .annotate(avg_rating=Avg("ratings__rating"), rating_count=Count("ratings"))
        .order_by("-avg_rating", "-rating_count")
        .distinct()[:limit]
    )
    return list(recs), movie


# --------------------------------------------------------------------- #
# Content-Based Filtering: Jaccard Similarity (profil genre)
# --------------------------------------------------------------------- #

def get_user_genre_profile(user_id=None, account_user_id=None, like_threshold=LIKE_THRESHOLD):
    """
    Kumpulan genre dari film-film yang disukai user (rating >= like_threshold).
    Return (set_genre_id, Counter genre_id -> jumlah kemunculan).
    """
    ratings_dict = get_ratings_dict(user_id, account_user_id)
    liked_movie_ids = [mid for mid, r in ratings_dict.items() if r >= like_threshold]

    genre_counter = Counter()
    for movie in Movie.objects.filter(id__in=liked_movie_ids).prefetch_related("genres"):
        for genre in movie.genres.all():
            genre_counter[genre.id] += 1

    return set(genre_counter.keys()), genre_counter


def get_user_favorite_genres(user_id=None, account_user_id=None, top_n=3,
                              like_threshold=LIKE_THRESHOLD):
    """Top-N genre favorit user, dikembalikan sebagai list object Genre."""
    _, genre_counter = get_user_genre_profile(user_id, account_user_id, like_threshold)
    if not genre_counter:
        return []

    top_ids = [gid for gid, _ in genre_counter.most_common(top_n)]
    genres = list(Genre.objects.filter(id__in=top_ids))
    genres.sort(key=lambda g: genre_counter[g.id], reverse=True)
    return genres


def jaccard_similarity(set_a, set_b):
    """J(A,B) = |A ∩ B| / |A ∪ B|"""
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def content_based_scores(user_id=None, account_user_id=None, like_threshold=LIKE_THRESHOLD):
    """
    Skor content-based per movie kandidat (yang belum pernah dirating user)
    = Jaccard Similarity antara profil genre user dengan genre movie tsb.
    Return dict {movie_id: skor 0..1}
    """
    user_genres, _ = get_user_genre_profile(user_id, account_user_id, like_threshold)
    if not user_genres:
        return {}

    rated_ids = get_ratings_dict(user_id, account_user_id).keys()
    candidates = Movie.objects.exclude(id__in=rated_ids).prefetch_related("genres")

    scores = {}
    for movie in candidates:
        movie_genres = {g.id for g in movie.genres.all()}
        score = jaccard_similarity(user_genres, movie_genres)
        if score > 0:
            scores[movie.id] = score
    return scores


# --------------------------------------------------------------------- #
# Collaborative Filtering: Pearson Correlation (antar user)
# --------------------------------------------------------------------- #

def pearson_correlation(ratings_a, ratings_b, min_common=MIN_COMMON_MOVIES):
    """
    ratings_a, ratings_b: dict {movie_id: rating}.
    Return None kalau jumlah film yang sama-sama dirating < min_common,
    atau kalau salah satu varians-nya 0 (rating konstan, tidak bisa dihitung).
    """
    common = set(ratings_a) & set(ratings_b)
    n = len(common)
    if n < min_common:
        return None

    a_vals = [ratings_a[m] for m in common]
    b_vals = [ratings_b[m] for m in common]

    mean_a = sum(a_vals) / n
    mean_b = sum(b_vals) / n

    num = sum((a - mean_a) * (b - mean_b) for a, b in zip(a_vals, b_vals))
    den_a = math.sqrt(sum((a - mean_a) ** 2 for a in a_vals))
    den_b = math.sqrt(sum((b - mean_b) ** 2 for b in b_vals))

    if den_a == 0 or den_b == 0:
        return None

    return num / (den_a * den_b)


def _rater_keys_for_movies(movie_ids):
    """
    Semua "rater" lain (dataset ATAU akun asli) yang pernah kasih rating
    ke salah satu film di movie_ids. Dikembalikan sbg set key unik:
    ("acc", account_user_id) atau ("uid", user_id)
    """
    rows = Rating.objects.filter(movie_id__in=movie_ids).values_list(
        "user_id", "account_user_id"
    )
    keys = set()
    for uid, acc_id in rows:
        if acc_id is not None:
            keys.add(("acc", acc_id))
        elif uid is not None:
            keys.add(("uid", uid))
    return keys


def find_similar_users(user_id=None, account_user_id=None, max_neighbors=MAX_NEIGHBORS,
                        min_common=MIN_COMMON_MOVIES):
    """
    Cari "tetangga" (user dataset ATAU akun asli lain) dengan pola rating
    paling mirip (Pearson Correlation tertinggi & positif).
    Return list of (ratings_dict_tetangga, correlation), urut paling mirip dulu.
    """
    target_ratings = get_ratings_dict(user_id, account_user_id)
    if not target_ratings:
        return []

    candidate_keys = _rater_keys_for_movies(target_ratings.keys())
    self_key = ("acc", account_user_id) if account_user_id is not None else ("uid", user_id)
    candidate_keys.discard(self_key)

    if not candidate_keys:
        return []

    acc_ids = [ident for kind, ident in candidate_keys if kind == "acc"]
    uid_ids = [ident for kind, ident in candidate_keys if kind == "uid"]

    other_rows = Rating.objects.filter(
        Q(account_user_id__in=acc_ids) | Q(user_id__in=uid_ids, account_user_id__isnull=True)
    ).values_list("user_id", "account_user_id", "movie_id", "rating")

    grouped = defaultdict(dict)
    for uid, acc_id, movie_id, rating in other_rows:
        key = ("acc", acc_id) if acc_id is not None else ("uid", uid)
        grouped[key][movie_id] = rating

    similarities = []
    for key, ratings in grouped.items():
        corr = pearson_correlation(target_ratings, ratings, min_common=min_common)
        if corr is not None and corr > 0:
            similarities.append((ratings, corr))

    similarities.sort(key=lambda pair: pair[1], reverse=True)
    return similarities[:max_neighbors]


def collaborative_scores(user_id=None, account_user_id=None, max_neighbors=MAX_NEIGHBORS):
    """
    Prediksi skor (skala rating asli, ~1..5) untuk movie yang BELUM pernah
    dirating user, berdasarkan rating para "tetangga" (weighted average,
    ditimbang oleh besarnya korelasi Pearson).
    Return dict {movie_id: predicted_score}
    """
    target_ratings = get_ratings_dict(user_id, account_user_id)
    neighbors = find_similar_users(user_id, account_user_id, max_neighbors=max_neighbors)
    if not neighbors:
        return {}

    numerator = defaultdict(float)
    denominator = defaultdict(float)

    for ratings, corr in neighbors:
        for movie_id, r in ratings.items():
            if movie_id in target_ratings:
                continue
            numerator[movie_id] += corr * r
            denominator[movie_id] += abs(corr)

    return {
        movie_id: numerator[movie_id] / total
        for movie_id, total in denominator.items()
        if total > 0
    }


# --------------------------------------------------------------------- #
# Hybrid: gabungan Content-Based (Jaccard) + Collaborative (Pearson)
# --------------------------------------------------------------------- #

def _normalize(scores_dict):
    """Min-max normalize skor ke rentang 0..1."""
    if not scores_dict:
        return {}
    values = scores_dict.values()
    lo, hi = min(values), max(values)
    if hi == lo:
        return {k: 1.0 for k in scores_dict}
    return {k: (v - lo) / (hi - lo) for k, v in scores_dict.items()}


def recommend_hybrid(user_id=None, account_user_id=None, limit=DEFAULT_LIMIT,
                      content_weight=CONTENT_WEIGHT, collab_weight=COLLAB_WEIGHT):
    """
    Skor akhir = (content_weight x Jaccard_ternormalisasi)
               + (collab_weight  x Pearson_prediksi_ternormalisasi)

    Return (list_movie_terurut, detail_dict) - detail_dict berisi skor
    mentah tiap komponen, dipakai untuk ditampilkan di halaman
    "Rekomendasi Saya" / admin (transparansi kenapa film itu direkomendasikan).
    """
    content_scores = content_based_scores(user_id, account_user_id)
    collab_scores = collaborative_scores(user_id, account_user_id)

    content_norm = _normalize(content_scores)
    collab_norm = _normalize(collab_scores)

    all_movie_ids = set(content_norm) | set(collab_norm)
    hybrid_scores = {
        mid: content_weight * content_norm.get(mid, 0.0) + collab_weight * collab_norm.get(mid, 0.0)
        for mid in all_movie_ids
    }

    if not hybrid_scores:
        return [], {"content_scores": {}, "collab_scores": {}, "hybrid_scores": {}}

    ranked_ids = sorted(hybrid_scores, key=lambda m: hybrid_scores[m], reverse=True)[:limit]

    movies = Movie.objects.filter(id__in=ranked_ids).prefetch_related("genres").annotate(
        avg_rating=Avg("ratings__rating"), rating_count=Count("ratings")
    )
    movies_by_id = {m.id: m for m in movies}
    ordered_movies = [movies_by_id[mid] for mid in ranked_ids if mid in movies_by_id]

    detail = {
        "content_scores": content_norm,
        "collab_scores": collab_norm,
        "hybrid_scores": hybrid_scores,
    }
    return ordered_movies, detail


# --------------------------------------------------------------------- #
# Entry point utama - dipanggil dari admin_views.py & movies/views.py
# --------------------------------------------------------------------- #

def recommend_for_user(user_id=None, account_user_id=None, limit=DEFAULT_LIMIT):
    """
    Fungsi utama, generik: isi salah satu `user_id` (dataset MovieLens)
    ATAU `account_user_id` (akun login asli web ini).

    Otomatis memilih strategi berdasarkan jumlah rating yang sudah dimiliki
    user tersebut, dan mengembalikan dict berisi:
    - method / method_label : strategi yang dipakai
    - recommendations       : list Movie
    - info                  : data tambahan (genre favorit / film acuan)
    - detail                : (khusus method="hybrid") skor mentah tiap komponen
    """
    rating_count = get_rating_count(user_id, account_user_id)

    if rating_count == 0:
        return {
            "method": "user_baru",
            "method_label": "User Baru (Cold Start)",
            "recommendations": recommend_for_new_user(limit=limit),
            "info": None,
        }

    if rating_count == 1:
        recs, base_movie = recommend_by_single_rating(user_id, account_user_id, limit=limit)
        return {
            "method": "rating_sekali",
            "method_label": "Rating Satu Kali",
            "recommendations": recs,
            "info": base_movie,
        }

    recs, detail = recommend_hybrid(user_id, account_user_id, limit=limit)
    favorite_genres = get_user_favorite_genres(user_id, account_user_id)

    if not recs:
        # Fallback: hybrid tidak menghasilkan apa pun (genre user tidak match
        # movie manapun & tidak ada user lain yang mirip pola ratingnya)
        rated_ids = get_ratings_dict(user_id, account_user_id).keys()
        return {
            "method": "top_rated",
            "method_label": "Top Rated (Fallback)",
            "recommendations": top_rated(limit=limit, exclude_ids=rated_ids),
            "info": favorite_genres,
        }

    return {
        "method": "hybrid",
        "method_label": "Hybrid (Content-Based + Collaborative)",
        "recommendations": recs,
        "info": favorite_genres,
        "detail": detail,
    }
