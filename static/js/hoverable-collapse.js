(function ($) {
  'use strict';

  // Función para manejar el hover y touch en el menú
  function handleMenuItemInteraction(ev) {
    var body = $('body');
    var sidebarIconOnly = body.hasClass("sidebar-icon-only");
    var sidebarFixed = body.hasClass("sidebar-fixed");
    var $menuItem = $(this);

    if (!('ontouchstart' in document.documentElement)) {
      // Comportamiento para mouse
      if (sidebarIconOnly) {
        if (sidebarFixed) {
          if (ev.type === 'mouseenter') {
            body.removeClass('sidebar-icon-only');
          }
        } else {
          if (ev.type === 'mouseenter') {
            $menuItem.addClass('hover-open');
          } else {
            $menuItem.removeClass('hover-open');
          }
        }
      }
    } else {
      // Comportamiento para touch
      if (ev.type === 'click') {
        if ($menuItem.hasClass('hover-open')) {
          $menuItem.removeClass('hover-open');
        } else {
          $('.sidebar .nav-item').removeClass('hover-open');
          $menuItem.addClass('hover-open');
        }
      }
    }
  }

  // Eventos para el menú
  $(document).on('mouseenter mouseleave', '.sidebar .nav-item', handleMenuItemInteraction);
  $(document).on('click', '.sidebar .nav-item', handleMenuItemInteraction);

  // Cerrar menú al hacer clic fuera
  $(document).on('click', function (ev) {
    if (!$(ev.target).closest('.sidebar').length && !$(ev.target).closest('.navbar-toggler').length && !$(ev.target).closest('[data-toggle="sidebar"]').length) {
      $('.sidebar .nav-item').removeClass('hover-open');
      $('body').removeClass('sidebar-open');
    }
  });

  // Manejo del menú móvil - corregido para usar data-toggle="sidebar"
  $(document).on('click', '[data-toggle="sidebar"]', function (e) {
    e.preventDefault();
    $('body').toggleClass('sidebar-open');
  });

  // Asegurarse de que el backdrop funcione
  $(document).on('click', '.sidebar-backdrop', function () {
    $('body').removeClass('sidebar-open');
  });

  // Cerrar menú al hacer clic en un enlace (solo en móvil)
  $(document).on('click', '.sidebar .nav-link', function () {
    if (window.innerWidth < 992) {
      $('body').removeClass('sidebar-open');
    }
  });

  // Ajustar el menú al cambiar el tamaño de la ventana
  $(window).on('resize', function () {
    if (window.innerWidth >= 992) {
      $('body').removeClass('sidebar-open');
      $('.sidebar .nav-item').removeClass('hover-open');
    }
  });
})(jQuery);