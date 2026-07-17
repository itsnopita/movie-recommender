from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("movies/", views.movie_list, name="movie_list"),
    path("movie/<int:pk>/", views.movie_detail, name="movie_detail"),
    path("movie/<int:pk>/favorite/", views.toggle_favorite, name="toggle_favorite"),
    path("movie/<int:pk>/rate/", views.submit_rating, name="submit_rating"),
    path("movie/<int:pk>/tag/", views.add_tag, name="add_tag"),
    path("movie/<int:pk>/tag/<int:tag_id>/delete/", views.delete_tag, name="delete_tag"),
    path("recommendations/", views.my_recommendations, name="my_recommendations"),
    path("contact/", views.contact, name="contact"),
]