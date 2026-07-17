from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.contrib import admin as django_admin

urlpatterns = [

    path("", include("movies.urls")),

    path("", include("accounts.urls")),

    # Panel admin custom milik kita sendiri (bukan django.contrib.admin)
    path("dashboard/", include("movies.admin_urls")),

    # Django admin bawaan (opsional, untuk debug data lewat /django-admin/)
    path("django-admin/", django_admin.site.urls),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)