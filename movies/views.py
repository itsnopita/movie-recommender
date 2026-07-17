from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from favorites.models import Favorite
from ratings.models import Rating
from tags.models import Tag
from recommendations import services as reco
from .models import Movie, Genre, ContactMessage


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _top_rated_movies(limit=15):
    """Film dengan rating rata-rata tertinggi (minimal 30 rating)."""
    return (
        Movie.objects.annotate(
            avg_rating=Avg("ratings__rating"),
            rating_count=Count("ratings"),
        )
        .filter(rating_count__gte=30)
        .order_by("-avg_rating", "-rating_count")[:limit]
    )


def home(request):
    movies = _top_rated_movies(limit=15)
    return render(request, "users/home.html", {"movies": movies})


def movie_list(request):
    q = request.GET.get("q", "").strip()
    genre_id = request.GET.get("genre")

    movies = Movie.objects.annotate(
        avg_rating=Avg("ratings__rating"),
        rating_count=Count("ratings"),
    ).order_by("-rating_count", "title")

    if q:
        movies = movies.filter(Q(title__icontains=q) | Q(genres__name__icontains=q)).distinct()

    if genre_id:
        movies = movies.filter(genres__id=genre_id)

    paginator = Paginator(movies, 18)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "users/movie_list.html",
        {
            "page_obj": page_obj,
            "genres": Genre.objects.all().order_by("name"),
            "q": q,
            "selected_genre": genre_id,
        },
    )


@login_required(login_url="login")
def movie_detail(request, pk):
    movie = get_object_or_404(Movie, pk=pk)

    is_favorited = Favorite.objects.filter(user=request.user, movie=movie).exists()
    user_rating = Rating.objects.filter(account_user=request.user, movie=movie).first()
    user_tags = Tag.objects.filter(account_user=request.user, movie=movie).order_by("-id")

    agg = movie.ratings.aggregate(avg=Avg("rating"), count=Count("id"))

    return render(
        request,
        "users/movie_detail.html",
        {
            "movie": movie,
            "is_favorited": is_favorited,
            "user_rating": user_rating,
            "user_tags": user_tags,
            "avg_rating": agg["avg"],
            "rating_count": agg["count"],
        },
    )


@login_required(login_url="login")
@require_POST
def toggle_favorite(request, pk):
    """Tambah/hapus film dari daftar favorit user yang sedang login."""
    movie = get_object_or_404(Movie, pk=pk)
    favorite, created = Favorite.objects.get_or_create(user=request.user, movie=movie)

    if not created:
        favorite.delete()
        is_favorited = False
        text = f'"{movie.title}" dihapus dari favorit.'
        if not _is_ajax(request):
            messages.info(request, text)
    else:
        is_favorited = True
        text = f'"{movie.title}" ditambahkan ke favorit.'
        if not _is_ajax(request):
            messages.success(request, text)

    if _is_ajax(request):
        return JsonResponse({"success": True, "is_favorited": is_favorited, "message": text})

    return redirect("movie_detail", pk=pk)


@login_required(login_url="login")
@require_POST
def submit_rating(request, pk):
    """Simpan/update rating (1-5) dari user yang sedang login untuk film ini."""
    movie = get_object_or_404(Movie, pk=pk)

    try:
        rating_value = float(request.POST.get("rating", ""))
    except (TypeError, ValueError):
        rating_value = None

    if rating_value is None or rating_value < 1 or rating_value > 5:
        error_text = "Rating harus dipilih antara 1 sampai 5."
        if _is_ajax(request):
            return JsonResponse({"success": False, "message": error_text}, status=400)
        messages.error(request, error_text)
        return redirect("movie_detail", pk=pk)

    Rating.objects.update_or_create(
        account_user=request.user,
        movie=movie,
        defaults={"rating": rating_value},
    )
    success_text = "Terima kasih! Rating kamu telah disimpan."

    if _is_ajax(request):
        agg = movie.ratings.aggregate(avg=Avg("rating"), count=Count("id"))
        return JsonResponse(
            {
                "success": True,
                "message": success_text,
                "user_rating": rating_value,
                "avg_rating": round(agg["avg"], 1) if agg["avg"] is not None else None,
                "rating_count": agg["count"],
            }
        )

    messages.success(request, f'Rating {rating_value:.0f} untuk "{movie.title}" tersimpan.')
    return redirect("movie_detail", pk=pk)


@login_required(login_url="login")
@require_POST
def add_tag(request, pk):
    """Tambah tag baru dari user yang sedang login untuk film ini."""
    movie = get_object_or_404(Movie, pk=pk)
    tag_text = request.POST.get("tag", "").strip()

    if not tag_text:
        error_text = "Tag tidak boleh kosong."
        if _is_ajax(request):
            return JsonResponse({"success": False, "message": error_text}, status=400)
        messages.error(request, error_text)
        return redirect("movie_detail", pk=pk)

    tag = Tag.objects.create(account_user=request.user, movie=movie, tag=tag_text)

    if _is_ajax(request):
        return JsonResponse(
            {"success": True, "message": f'Tag "{tag_text}" ditambahkan.', "tag": {"id": tag.pk, "tag": tag.tag}}
        )

    messages.success(request, f'Tag "{tag_text}" ditambahkan.')
    return redirect("movie_detail", pk=pk)


@login_required(login_url="login")
@require_POST
def delete_tag(request, pk, tag_id):
    """Hapus tag milik user yang sedang login untuk film ini."""
    movie = get_object_or_404(Movie, pk=pk)
    tag = get_object_or_404(Tag, pk=tag_id, movie=movie, account_user=request.user)
    tag.delete()

    if _is_ajax(request):
        return JsonResponse({"success": True, "message": f'Tag "{tag.tag}" dihapus.'})

    messages.info(request, f'Tag "{tag.tag}" dihapus.')
    return redirect("movie_detail", pk=pk)


@login_required(login_url="login")
def my_recommendations(request):
    """
    Halaman "Rekomendasi Saya" - hasil rekomendasi personal untuk user yang
    sedang login, otomatis memperhitungkan rating & tag yang baru saja ia
    berikan (bukan lagi dari user_id dataset MovieLens).
    """
    result = reco.recommend_for_user(account_user_id=request.user.id)
    rating_count = reco.get_user_rating_count(account_user_id=request.user.id)

    return render(
        request,
        "users/recommendation.html",
        {
            "result": result,
            "rating_count": rating_count,
        },
    )


@login_required(login_url="login")
def contact(request):
    """Kirim pesan ke developer. Hanya bisa diakses user yang sudah login."""
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        message_text = request.POST.get("message", "").strip()

        if not email or not message_text:
            messages.error(request, "Email dan pesan wajib diisi.")
        else:
            ContactMessage.objects.create(
                user=request.user,
                email=email,
                message=message_text,
            )
            messages.success(
                request,
                "Pesan kamu berhasil terkirim! Kami akan segera menghubungi kamu.",
            )

    return redirect(f"{reverse('home')}#contact")