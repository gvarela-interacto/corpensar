/**
 * Manejo del toggle del menú lateral para Corpensar
 * Este script gestiona la interacción del botón de hamburguesa y el menú lateral
 */

document.addEventListener('DOMContentLoaded', function () {
    // Manejar todos los botones de toggle del sidebar
    const sidebarToggles = document.querySelectorAll('[data-toggle="sidebar"]');
    sidebarToggles.forEach(toggle => {
        toggle.addEventListener('click', function (e) {
            e.preventDefault();
            const body = document.body;
            body.classList.toggle('sidebar-open');

            // Manejar el backdrop
            const backdrop = document.getElementById('sidebarBackdrop');
            if (backdrop) {
                if (body.classList.contains('sidebar-open')) {
                    backdrop.style.display = 'block';
                } else {
                    setTimeout(() => {
                        backdrop.style.display = 'none';
                    }, 300);
                }
            }
        });
    });

    // Cerrar menú al hacer clic en el backdrop
    const backdrop = document.getElementById('sidebarBackdrop');
    if (backdrop) {
        backdrop.addEventListener('click', function () {
            document.body.classList.remove('sidebar-open');
            backdrop.style.display = 'none';
        });
    }

    // Cerrar el menú al hacer clic en un enlace (solo en móvil)
    const navLinks = document.querySelectorAll('.sidebar .nav-link');
    function closeMenuOnMobile() {
        if (window.innerWidth < 992) {
            document.body.classList.remove('sidebar-open');
            const backdrop = document.getElementById('sidebarBackdrop');
            if (backdrop) {
                backdrop.style.display = 'none';
            }
        }
    }

    navLinks.forEach(link => {
        link.addEventListener('click', closeMenuOnMobile);
    });

    // Cerrar menú al cambiar tamaño de ventana a desktop
    window.addEventListener('resize', function () {
        if (window.innerWidth > 991) {
            document.body.classList.remove('sidebar-open');
            const backdrop = document.getElementById('sidebarBackdrop');
            if (backdrop) backdrop.style.display = 'none';
        }
    });

    // Cerrar menú al hacer clic en el contenido principal (en móvil)
    const mainPanel = document.querySelector('.main-panel');
    if (mainPanel && window.innerWidth <= 991) {
        mainPanel.addEventListener('click', function () {
            const body = document.querySelector('body');
            if (body.classList.contains('sidebar-open')) {
                body.classList.remove('sidebar-open');
                const backdrop = document.getElementById('sidebarBackdrop');
                if (backdrop) {
                    setTimeout(() => {
                        backdrop.style.display = 'none';
                    }, 300);
                }
            }
        });
    }
}); 