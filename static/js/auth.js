document.addEventListener("DOMContentLoaded", function () {

    const toggles = document.querySelectorAll(".toggle-password");

    toggles.forEach(toggle => {

        toggle.addEventListener("click", function () {

            const target = this.getAttribute("data-target");

            const input = document.getElementById(target);

            const icon = this.querySelector("i");

            if (!input) return;

            if (input.type === "password") {

                input.type = "text";

                icon.classList.remove("bi-eye-fill");
                icon.classList.add("bi-eye-slash-fill");

            } else {

                input.type = "password";

                icon.classList.remove("bi-eye-slash-fill");
                icon.classList.add("bi-eye-fill");

            }

        });

    });

    // Cegah tombol submit di-klik dobel (bikin request registrasi/login
    // ganda yang bisa nabrak constraint unik di database).
    document.querySelectorAll("form").forEach(form => {
        form.addEventListener("submit", function () {
            const btn = form.querySelector("button[type='submit']");
            if (btn && !btn.disabled) {
                btn.disabled = true;
                btn.dataset.originalText = btn.innerHTML;
                btn.innerHTML = "Memproses...";
            }
        });
    });

});