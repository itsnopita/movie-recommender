from django.urls import path
from .admin_views import *

urlpatterns = [
    path("", admin_dashboard, name="admin_dashboard"),

    # Movie
    path("movie/", admin_movie, name="admin_movie"),
    path("movie/add/", admin_movie_form, name="admin_movie_add"),
    path("movie/<int:pk>/edit/", admin_movie_form, name="admin_movie_edit"),
    path("movie/<int:pk>/delete/", admin_movie_delete, name="admin_movie_delete"),

    # Tag
    path("tag/", admin_tag, name="admin_tag"),
    path("tag/add/", admin_tag_form, name="admin_tag_add"),
    path("tag/<int:pk>/edit/", admin_tag_form, name="admin_tag_edit"),
    path("tag/<int:pk>/delete/", admin_tag_delete, name="admin_tag_delete"),

    # Rate
    path("rating/", admin_rating, name="admin_rating"),
    path("rating/add/", admin_rating_form, name="admin_rating_add"),
    path("rating/<int:pk>/edit/", admin_rating_form, name="admin_rating_edit"),
    path("rating/<int:pk>/delete/", admin_rating_delete, name="admin_rating_delete"),

    # Recommendation - user dataset (MovieLens)
    path("recommendation/", admin_recommendation, name="admin_recommendation"),
    path("genre-favorit/<int:user_id>/", admin_genre_favorit, name="admin_genre_favorit"),
    path("recommendation/<int:user_id>/", admin_recommendation_detail, name="admin_recommendation_detail"),

    # Recommendation - user aplikasi (akun asli)
    path("genre-favorit/account/<int:account_user_id>/", admin_genre_favorit_account, name="admin_genre_favorit_account"),
    path("recommendation/account/<int:account_user_id>/", admin_recommendation_detail_account, name="admin_recommendation_detail_account"),

    # Message (pesan dari user untuk developer)
    path("message/", admin_message, name="admin_message"),
    path("message/<int:pk>/read/", admin_message_read, name="admin_message_read"),
    path("message/<int:pk>/delete/", admin_message_delete, name="admin_message_delete"),
]
