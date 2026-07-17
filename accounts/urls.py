from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),

    # alias supaya @login_required(login_url="admin_login") di admin_views.py tetap jalan,
    # tapi mengarah ke halaman login yang sama
    path("dashboard/login/", views.login_view, name="admin_login"),

    path("dashboard/profile/", views.profile_edit, name="admin_profile_edit"),
]