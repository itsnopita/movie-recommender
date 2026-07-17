// ============================================================
// NAVBAR ACTIVE LINK — Animasi underline mengikuti menu yang diklik
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
    const navLinks = document.querySelectorAll('.nav-link');
    const currentPath = window.location.pathname;
    const currentHash = window.location.hash;

    // Fungsi untuk menghapus active dari semua link
    function removeActiveClasses() {
        navLinks.forEach(link => link.classList.remove('active'));
    }

    // Fungsi untuk menambahkan active ke link berdasarkan href
    function setActiveLink() {
        let activeSet = false;

        navLinks.forEach(link => {
            const href = link.getAttribute('href');
            
            // Cek jika href sama dengan current path + hash
            if (href === currentPath + currentHash) {
                removeActiveClasses();
                link.classList.add('active');
                activeSet = true;
            }
            
            // Cek jika href hanya path (tanpa hash)
            if (href === currentPath && !currentHash) {
                removeActiveClasses();
                link.classList.add('active');
                activeSet = true;
            }
        });

        // Jika tidak ada yang cocok, cek berdasarkan hash saja
        if (!activeSet && currentHash) {
            navLinks.forEach(link => {
                const href = link.getAttribute('href');
                if (href === currentHash || href === '#' + currentHash.replace('#', '')) {
                    removeActiveClasses();
                    link.classList.add('active');
                }
            });
        }
    }

    // Set active saat pertama load
    setActiveLink();

    // Event listener untuk setiap link
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            
            // Jika href adalah hash link (anchor)
            if (href.startsWith('#')) {
                e.preventDefault();
                const targetId = href.substring(1);
                const targetElement = document.getElementById(targetId);
                
                if (targetElement) {
                    // Hapus active dari semua link
                    removeActiveClasses();
                    // Tambahkan active ke link yang diklik
                    this.classList.add('active');
                    
                    // Scroll ke target
                    const navbarHeight = document.querySelector('.navbar').offsetHeight;
                    const targetPosition = targetElement.getBoundingClientRect().top + window.pageYOffset - navbarHeight - 20;
                    
                    window.scrollTo({
                        top: targetPosition,
                        behavior: 'smooth'
                    });
                }
            } else {
                // Untuk link ke halaman lain, biarkan default
                // Tapi tetap set active
                removeActiveClasses();
                this.classList.add('active');
            }
        });
    });

    // Update active saat scroll (untuk section highlight)
    const sections = document.querySelectorAll('section[id]');
    
    window.addEventListener('scroll', function() {
        let current = '';
        const scrollY = window.pageYOffset + 120;

        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.offsetHeight;
            
            if (scrollY >= sectionTop && scrollY < sectionTop + sectionHeight) {
                current = section.getAttribute('id');
            }
        });

        navLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href === '#' + current || href === '/#' + current) {
                removeActiveClasses();
                link.classList.add('active');
            }
        });
    });
});