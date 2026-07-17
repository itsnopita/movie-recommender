from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.shortcuts import render, redirect, get_object_or_404

from movies.models import Movie, Genre, ContactMessage
from tags.models import Tag
from ratings.models import Rating
from recommendations import services as reco


PAGE_SIZE = 10


# --------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------- #

@login_required(login_url="admin_login")
def admin_dashboard(request):
    total_movies = Movie.objects.count()
    total_tags = Tag.objects.count()
    total_ratings = Rating.objects.count()
    total_users = Rating.objects.values("user_id").distinct().count()
    total_messages = ContactMessage.objects.count()
    unread_messages = ContactMessage.objects.filter(is_read=False).count()

    latest_movies = Movie.objects.order_by("-id")[:5]

    return render(request, "admin/dashboard.html", {
        "total_movies": total_movies,
        "total_tags": total_tags,
        "total_ratings": total_ratings,
        "total_users": total_users,
        "total_messages": total_messages,
        "unread_messages": unread_messages,
        "latest_movies": latest_movies,
    })


# --------------------------------------------------------------------- #
# Movie CRUD
# --------------------------------------------------------------------- #

@login_required(login_url="admin_login")
def admin_movie(request):
    query = request.GET.get("q", "").strip()

    movies = Movie.objects.all().prefetch_related("genres").order_by("id")
    if query:
        movies = movies.filter(title__icontains=query)

    paginator = Paginator(movies, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page"))

    return render(request, "admin/movie.html", {
        "page_obj": page,
        "query": query,
        "total": paginator.count,
    })


@login_required(login_url="admin_login")
def admin_movie_form(request, pk=None):
    movie = get_object_or_404(Movie, pk=pk) if pk else None
    all_genres = Genre.objects.all().order_by("name")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        year = request.POST.get("year") or None
        poster = request.POST.get("poster", "").strip()
        overview = request.POST.get("overview", "").strip()
        imdb_id = request.POST.get("imdb_id", "").strip()
        tmdb_id = request.POST.get("tmdb_id", "").strip()
        genre_ids = request.POST.getlist("genres")

        if not title:
            messages.error(request, "Judul movie wajib diisi.")
        else:
            if movie is None:
                # ID baru dibuat manual (mengikuti pola movieId dataset);
                # ambil ID tertinggi + 1 supaya tidak bentrok
                next_id = (Movie.objects.order_by("-id").values_list("id", flat=True).first() or 0) + 1
                movie = Movie(id=next_id)

            movie.title = title
            movie.year = int(year) if year else None
            movie.poster = poster or None
            movie.overview = overview or None
            movie.imdb_id = imdb_id or None
            movie.tmdb_id = tmdb_id or None
            movie.save()
            movie.genres.set(genre_ids)

            messages.success(request, f"Movie '{movie.title}' berhasil disimpan.")
            return redirect("admin_movie")

    return render(request, "admin/movie_form.html", {
        "movie": movie,
        "all_genres": all_genres,
        "selected_genre_ids": list(movie.genres.values_list("id", flat=True)) if movie else [],
    })


@login_required(login_url="admin_login")
def admin_movie_delete(request, pk):
    movie = get_object_or_404(Movie, pk=pk)
    if request.method == "POST":
        title = movie.title
        movie.delete()
        messages.success(request, f"Movie '{title}' berhasil dihapus.")
    return redirect("admin_movie")


# --------------------------------------------------------------------- #
# Tag CRUD
# --------------------------------------------------------------------- #

@login_required(login_url="admin_login")
def admin_tag(request):
    query = request.GET.get("q", "").strip()

    tags = Tag.objects.select_related("movie").order_by("-id")
    if query:
        tags = tags.filter(tag__icontains=query)

    paginator = Paginator(tags, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page"))

    return render(request, "admin/tag.html", {
        "page_obj": page,
        "query": query,
        "total": paginator.count,
    })


@login_required(login_url="admin_login")
def admin_tag_form(request, pk=None):
    tag = get_object_or_404(Tag, pk=pk) if pk else None

    if request.method == "POST":
        movie_id = request.POST.get("movie_id")
        user_id = request.POST.get("user_id")
        tag_text = request.POST.get("tag", "").strip()

        movie = Movie.objects.filter(id=movie_id).first()

        if not movie or not tag_text or not user_id:
            messages.error(request, "Movie, User ID, dan Tag wajib diisi.")
        else:
            if tag is None:
                tag = Tag()
            tag.movie = movie
            tag.user_id = int(user_id)
            tag.tag = tag_text
            tag.save()

            messages.success(request, "Tag berhasil disimpan.")
            return redirect("admin_tag")

    return render(request, "admin/tag_form.html", {"tag": tag})


@login_required(login_url="admin_login")
def admin_tag_delete(request, pk):
    tag = get_object_or_404(Tag, pk=pk)
    if request.method == "POST":
        tag.delete()
        messages.success(request, "Tag berhasil dihapus.")
    return redirect("admin_tag")


# --------------------------------------------------------------------- #
# Rate (Tambah / Edit / Hapus rating dataset - sama pattern dengan Tag)
# --------------------------------------------------------------------- #

@login_required(login_url="admin_login")
def admin_rating(request):
    query = request.GET.get("q", "").strip()

    ratings = Rating.objects.select_related("movie", "account_user").order_by("-id")
    if query:
        ratings = ratings.filter(movie__title__icontains=query)

    paginator = Paginator(ratings, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page"))

    return render(request, "admin/rating.html", {
        "page_obj": page,
        "query": query,
        "total": paginator.count,
    })


@login_required(login_url="admin_login")
def admin_rating_form(request, pk=None):
    rating_obj = get_object_or_404(Rating, pk=pk) if pk else None

    if request.method == "POST":
        movie_id = request.POST.get("movie_id")
        user_id = request.POST.get("user_id")
        rating_value = request.POST.get("rating")

        movie = Movie.objects.filter(id=movie_id).first()

        error = None
        if not movie or not user_id or not rating_value:
            error = "Movie, User ID, dan Rating wajib diisi."
        else:
            try:
                rating_value = float(rating_value)
                if not (0.5 <= rating_value <= 5):
                    error = "Rating harus di antara 0.5 - 5."
            except ValueError:
                error = "Rating harus berupa angka."

        if error:
            messages.error(request, error)
        else:
            if rating_obj is None:
                rating_obj = Rating()
            rating_obj.movie = movie
            rating_obj.user_id = int(user_id)
            rating_obj.rating = rating_value
            rating_obj.save()

            messages.success(request, "Rating berhasil disimpan.")
            return redirect("admin_rating")

    return render(request, "admin/rating_form.html", {"rating_obj": rating_obj})


@login_required(login_url="admin_login")
def admin_rating_delete(request, pk):
    rating_obj = get_object_or_404(Rating, pk=pk)
    if request.method == "POST":
        rating_obj.delete()
        messages.success(request, "Rating berhasil dihapus.")
    return redirect("admin_rating")


# --------------------------------------------------------------------- #
# Recommendation
#
# Ada 2 sumber "user" yang ditampilkan terpisah di halaman ini:
# - User Dataset (MovieLens)  -> dikenali lewat `user_id` (integer)
# - User Aplikasi (akun asli) -> dikenali lewat `account_user` (akun login)
# Keduanya dihitung pakai fungsi yang SAMA di recommendations/services.py,
# cuma beda parameter (user_id= vs account_user_id=).
# --------------------------------------------------------------------- #

@login_required(login_url="admin_login")
def admin_recommendation(request):
    query = request.GET.get("q", "").strip()

    # -- User dataset MovieLens --
    dataset_users = (
        Rating.objects.filter(user_id__isnull=False)
        .values("user_id")
        .annotate(rating_count=Count("id", distinct=True))
        .order_by("user_id")
    )
    dataset_tag_counts = dict(
        Tag.objects.filter(user_id__isnull=False)
        .values("user_id").annotate(c=Count("id")).values_list("user_id", "c")
    )
    dataset_rows = []
    for u in dataset_users:
        uid = u["user_id"]
        if query and query.lower() not in str(uid).lower():
            continue
        dataset_rows.append({
            "user_id": uid,
            "rating_count": u["rating_count"],
            "tag_count": dataset_tag_counts.get(uid, 0),
        })

    dataset_paginator = Paginator(dataset_rows, PAGE_SIZE)
    dataset_page = dataset_paginator.get_page(request.GET.get("page"))

    # -- User aplikasi (akun asli yang login & sudah pernah rating/tag) --
    account_users = (
        Rating.objects.filter(account_user__isnull=False)
        .values("account_user_id", "account_user__username")
        .annotate(rating_count=Count("id", distinct=True))
        .order_by("account_user__username")
    )
    account_tag_counts = dict(
        Tag.objects.filter(account_user__isnull=False)
        .values("account_user_id").annotate(c=Count("id")).values_list("account_user_id", "c")
    )
    account_rows = []
    for u in account_users:
        acc_id = u["account_user_id"]
        username = u["account_user__username"]
        if query and query.lower() not in username.lower():
            continue
        account_rows.append({
            "account_user_id": acc_id,
            "username": username,
            "rating_count": u["rating_count"],
            "tag_count": account_tag_counts.get(acc_id, 0),
        })

    account_paginator = Paginator(account_rows, PAGE_SIZE)
    account_page = account_paginator.get_page(request.GET.get("account_page"))

    return render(request, "admin/recommendation.html", {
        "page_obj": dataset_page,
        "account_page_obj": account_page,
        "query": query,
        "total": dataset_paginator.count,
        "account_total": account_paginator.count,
    })


def _genre_favorit_context(request, user_id=None, account_user_id=None, display_name=None):
    """Helper bersama untuk halaman Genre Favorit, dipakai baik untuk user
    dataset maupun akun asli."""
    _, genre_counter = reco.get_user_genre_profile(user_id=user_id, account_user_id=account_user_id)

    all_genres = list(Genre.objects.all().order_by("name"))
    genre_rows = [{"name": g.name, "count": genre_counter.get(g.id, 0)} for g in all_genres]

    top_genre = None
    if genre_counter:
        top_genre_id = genre_counter.most_common(1)[0][0]
        top_genre = Genre.objects.filter(id=top_genre_id).first()

    movies = Movie.objects.none()
    if top_genre:
        rated_ids = reco.get_ratings_dict(user_id=user_id, account_user_id=account_user_id).keys()
        movies = (
            Movie.objects.filter(genres=top_genre)
            .exclude(id__in=rated_ids)
            .annotate(avg_rating=Avg("ratings__rating"), rating_count=Count("ratings"))
            .order_by("-avg_rating", "-rating_count")
            .distinct()
        )

    query = request.GET.get("q", "").strip()
    if query and top_genre:
        movies = movies.filter(title__icontains=query)

    paginator = Paginator(movies, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page"))

    return {
        "display_name": display_name,
        "genre_rows": genre_rows,
        "top_genre": top_genre,
        "page_obj": page,
        "query": query,
        "total": paginator.count,
    }


@login_required(login_url="admin_login")
def admin_genre_favorit(request, user_id):
    context = _genre_favorit_context(request, user_id=user_id, display_name=f"User {user_id} (Dataset)")
    return render(request, "admin/genre_favorit.html", context)


@login_required(login_url="admin_login")
def admin_genre_favorit_account(request, account_user_id):
    account_user = get_object_or_404(User, pk=account_user_id)
    context = _genre_favorit_context(
        request, account_user_id=account_user_id,
        display_name=f"{account_user.username} (Akun Aplikasi)",
    )
    return render(request, "admin/genre_favorit.html", context)


def _recommendation_detail_context(request, user_id=None, account_user_id=None, display_name=None):
    """Helper bersama untuk halaman detail Rekomendasi (hybrid)."""
    result = reco.recommend_for_user(user_id=user_id, account_user_id=account_user_id, limit=30)
    favorite_genres = reco.get_user_favorite_genres(user_id=user_id, account_user_id=account_user_id)

    hybrid_scores = {}
    if result.get("method") == "hybrid":
        hybrid_scores = result.get("detail", {}).get("hybrid_scores", {})

    rows = []
    for movie in result["recommendations"]:
        score = hybrid_scores.get(movie.id, movie.avg_rating)
        rows.append({"movie": movie, "score": score})

    query = request.GET.get("q", "").strip()
    if query:
        rows = [r for r in rows if query.lower() in r["movie"].title.lower()]

    paginator = Paginator(rows, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page"))

    return {
        "display_name": display_name,
        "result": result,
        "favorite_genres": favorite_genres,
        "rating_count": reco.get_user_rating_count(user_id=user_id, account_user_id=account_user_id),
        "page_obj": page,
        "query": query,
        "total": paginator.count,
    }


@login_required(login_url="admin_login")
def admin_recommendation_detail(request, user_id):
    context = _recommendation_detail_context(request, user_id=user_id, display_name=f"User {user_id} (Dataset)")
    return render(request, "admin/recommendation_detail.html", context)


@login_required(login_url="admin_login")
def admin_recommendation_detail_account(request, account_user_id):
    account_user = get_object_or_404(User, pk=account_user_id)
    context = _recommendation_detail_context(
        request, account_user_id=account_user_id,
        display_name=f"{account_user.username} (Akun Aplikasi)",
    )
    return render(request, "admin/recommendation_detail.html", context)


# --------------------------------------------------------------------- #
# Contact Message (pesan dari user untuk developer)
# --------------------------------------------------------------------- #

@login_required(login_url="admin_login")
def admin_message(request):
    query = request.GET.get("q", "").strip()

    contact_messages = ContactMessage.objects.select_related("user").order_by("-created_at")
    if query:
        contact_messages = contact_messages.filter(
            Q(email__icontains=query) | Q(message__icontains=query)
        )

    paginator = Paginator(contact_messages, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page"))

    return render(request, "admin/message.html", {
        "page_obj": page,
        "query": query,
        "total": paginator.count,
    })


@login_required(login_url="admin_login")
def admin_message_read(request, pk):
    msg = get_object_or_404(ContactMessage, pk=pk)
    if not msg.is_read:
        msg.is_read = True
        msg.save(update_fields=["is_read"])
    return redirect("admin_message")


@login_required(login_url="admin_login")
def admin_message_delete(request, pk):
    msg = get_object_or_404(ContactMessage, pk=pk)
    if request.method == "POST":
        msg.delete()
        messages.success(request, "Pesan berhasil dihapus.")
    return redirect("admin_message")
