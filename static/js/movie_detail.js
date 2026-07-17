// static/js/movie_detail.js
// Interaksi halaman detail film: favorite, rating bintang, dan tag — semua tanpa reload halaman.

(function () {
    "use strict";

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(";").shift();
        return null;
    }

    const csrftoken = getCookie("csrftoken");

    function postJSON(url, body) {
        return fetch(url, {
            method: "POST",
            headers: {
                "X-CSRFToken": csrftoken,
                "X-Requested-With": "XMLHttpRequest",
            },
            body: body,
        }).then(async (res) => {
            let data = {};
            try {
                data = await res.json();
            } catch (e) {
                data = {};
            }
            return { ok: res.ok, data: data };
        });
    }

    function showAlert(el, text) {
        if (!el) return;
        el.textContent = text;
        el.style.display = "flex";
        window.clearTimeout(el._hideTimer);
        el._hideTimer = window.setTimeout(() => {
            el.style.display = "none";
        }, 4000);
    }

    function showSuccessAlert(el, text) {
        if (!el) return;
        const span = el.querySelector("span");
        if (span) {
            span.textContent = text;
        } else {
            el.textContent = text;
        }
        el.style.display = "flex";
        window.clearTimeout(el._hideTimer);
        el._hideTimer = window.setTimeout(() => {
            el.style.display = "none";
        }, 4000);
    }

    /* ================= FAVORITE ================= */
    const favBtn = document.getElementById("favBtn");
    if (favBtn) {
        favBtn.addEventListener("click", function () {
            const url = favBtn.dataset.url;
            favBtn.disabled = true;
            postJSON(url).then(({ ok, data }) => {
                favBtn.disabled = false;
                if (!ok || !data.success) return;
                const textEl = document.getElementById("favBtnText");
                if (data.is_favorited) {
                    favBtn.classList.add("is-active");
                    if (textEl) textEl.textContent = "Favorited";
                } else {
                    favBtn.classList.remove("is-active");
                    if (textEl) textEl.textContent = "Favorite";
                }
            });
        });
    }

    /* ================= STAR RATING ================= */
    const starPicker = document.getElementById("starPicker");
    const submitRatingBtn = document.getElementById("submitRatingBtn");
    const ratingSuccessAlert = document.getElementById("ratingSuccessAlert");
    const ratingErrorAlert = document.getElementById("ratingErrorAlert");

    if (starPicker) {
        const stars = Array.from(starPicker.querySelectorAll(".star-icon"));
        let selected = parseInt(starPicker.dataset.selected, 10) || 0;

        function paintStars(upTo) {
            stars.forEach((star) => {
                const value = parseInt(star.dataset.value, 10);
                if (value <= upTo) {
                    star.classList.remove("bi-star");
                    star.classList.add("bi-star-fill");
                } else {
                    star.classList.remove("bi-star-fill");
                    star.classList.add("bi-star");
                }
            });
        }

        function refreshSubmitState() {
            if (submitRatingBtn) submitRatingBtn.disabled = selected < 1;
        }

        paintStars(selected);
        refreshSubmitState();

        stars.forEach((star) => {
            star.addEventListener("mouseenter", () => paintStars(parseInt(star.dataset.value, 10)));
            star.addEventListener("click", () => {
                selected = parseInt(star.dataset.value, 10);
                paintStars(selected);
                refreshSubmitState();
            });
        });

        starPicker.addEventListener("mouseleave", () => paintStars(selected));

        if (submitRatingBtn) {
            submitRatingBtn.addEventListener("click", function () {
                if (selected < 1) return;
                const url = starPicker.dataset.url;
                const body = new URLSearchParams({ rating: selected });

                submitRatingBtn.disabled = true;
                submitRatingBtn.textContent = "Menyimpan...";

                postJSON(url, body).then(({ ok, data }) => {
                    submitRatingBtn.disabled = false;
                    submitRatingBtn.textContent = "Submit Rating";

                    if (!ok || !data.success) {
                        showAlert(ratingErrorAlert, (data && data.message) || "Gagal menyimpan rating.");
                        return;
                    }

                    showSuccessAlert(ratingSuccessAlert, data.message || "Terima kasih! Rating kamu telah disimpan.");

                    const avgText = document.getElementById("avgRatingText");
                    if (avgText) {
                        if (data.rating_count) {
                            avgText.textContent = `${data.avg_rating} (${data.rating_count} rating)`;
                        } else {
                            avgText.textContent = "Belum ada rating";
                        }
                    }

                    const userRatingText = document.getElementById("userRatingText");
                    const userRatingValue = document.getElementById("userRatingValue");
                    if (userRatingValue) userRatingValue.textContent = Math.round(data.user_rating);
                    if (userRatingText) userRatingText.style.display = "inline";
                });
            });
        }
    }

    /* ================= TAG ================= */
    const tagForm = document.getElementById("tagForm");
    const tagInput = document.getElementById("tagInput");
    const tagList = document.getElementById("tagList");
    const noTagsText = document.getElementById("noTagsText");
    const tagErrorAlert = document.getElementById("tagErrorAlert");

    function makeTagPill(tag) {
        const span = document.createElement("span");
        span.className = "tag-pill";
        span.dataset.tagId = tag.id;

        const label = document.createTextNode(tag.tag + " ");
        span.appendChild(label);

        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "tag-pill-remove";
        btn.setAttribute("aria-label", "Hapus tag");
        btn.innerHTML = "&times;";
        btn.dataset.url = `${window.location.pathname}tag/${tag.id}/delete/`;
        span.appendChild(btn);

        return span;
    }

    function bindRemoveButton(btn) {
        btn.addEventListener("click", function () {
            const url = btn.dataset.url;
            const pill = btn.closest(".tag-pill");
            btn.disabled = true;

            postJSON(url).then(({ ok, data }) => {
                if (!ok || !data.success) {
                    btn.disabled = false;
                    return;
                }
                if (pill) pill.remove();
                if (tagList && !tagList.querySelector(".tag-pill") && noTagsText) {
                    noTagsText.style.display = "block";
                }
            });
        });
    }

    if (tagList) {
        tagList.querySelectorAll(".tag-pill-remove").forEach(bindRemoveButton);
    }

    if (tagForm) {
        tagForm.addEventListener("submit", function (e) {
            e.preventDefault();
            const value = tagInput.value.trim();
            if (!value) return;

            const url = tagForm.dataset.url;
            const body = new URLSearchParams({ tag: value });
            const submitBtn = tagForm.querySelector("button[type=submit]");

            if (submitBtn) submitBtn.disabled = true;

            postJSON(url, body).then(({ ok, data }) => {
                if (submitBtn) submitBtn.disabled = false;

                if (!ok || !data.success) {
                    showAlert(tagErrorAlert, (data && data.message) || "Gagal menambahkan tag.");
                    return;
                }

                tagInput.value = "";
                if (noTagsText) noTagsText.style.display = "none";
                if (tagList) {
                    const pill = makeTagPill(data.tag);
                    tagList.appendChild(pill);
                    bindRemoveButton(pill.querySelector(".tag-pill-remove"));
                }
            });
        });
    }
})();
