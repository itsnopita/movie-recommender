from django.contrib import admin
from .models import Movie, Genre, ContactMessage


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("id", "name")


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "year", "imdb_id", "tmdb_id")
    search_fields = ("title",)
    list_filter = ("genres",)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "user", "created_at", "is_read")
    list_filter = ("is_read",)
    search_fields = ("email", "message")