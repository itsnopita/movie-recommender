from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.shortcuts import render, redirect

from .models import Profile


def login_view(request):
    if request.user.is_authenticated:
        return redirect("admin_dashboard" if request.user.is_staff else "home")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if user.is_staff:
                return redirect("admin_dashboard")
            messages.success(request, f"Selamat datang kembali, {user.first_name or user.username}!")
            return redirect(request.POST.get("next") or request.GET.get("next") or "home")

        return render(request, "users/login.html", {
            "error": "Username atau password salah.",
            "username": username,
        })

    return render(request, "users/login.html")


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        password2 = request.POST.get("password2", "")
        form_data = {"username": username, "email": email}

        if not username or not email or not password:
            return render(request, "users/register.html", {"error": "Semua kolom wajib diisi.", **form_data})
        if password != password2:
            return render(request, "users/register.html", {"error": "Konfirmasi password tidak cocok.", **form_data})
        if len(password) < 6:
            return render(request, "users/register.html", {"error": "Password minimal 6 karakter.", **form_data})
        if User.objects.filter(username=username).exists():
            return render(request, "users/register.html", {"error": "Username sudah digunakan.", **form_data})
        if User.objects.filter(email=email).exists():
            return render(request, "users/register.html", {"error": "Email sudah terdaftar.", **form_data})

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username, email=email, password=password,
                )
        except IntegrityError:
            # Jaring pengaman: kejadian kalau ada 2 request registrasi dengan
            # username/email yang sama nyaris bersamaan (misal tombol Daftar
            # ke-klik dobel), jadi cek di atas sama-sama lolos tapi salah satu
            # gagal pas disimpan ke database karena constraint unik.
            return render(request, "users/register.html", {
                "error": "Username atau email sudah digunakan. Coba pakai yang lain.",
                **form_data,
            })

        login(request, user)
        messages.success(request, "Akun berhasil dibuat. Selamat menikmati MovieHub!")
        return redirect("home")

    return render(request, "users/register.html")


def logout_view(request):
    logout(request)
    return redirect("home")


@login_required(login_url="admin_login")
def profile_edit(request):
    """Edit profil admin - upload foto yang tampil di pojok kanan panel admin."""
    if not request.user.is_staff:
        return redirect("home")

    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        photo = request.FILES.get("photo")
        if photo:
            profile.photo = photo
            profile.save()
            messages.success(request, "Foto profil berhasil diperbarui.")
        else:
            messages.error(request, "Pilih file foto terlebih dahulu.")
        return redirect("admin_profile_edit")

    return render(request, "admin/profile_edit.html", {"profile": profile})
