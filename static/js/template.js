(function ($) {
  'use strict';
  $(function () {
    var body = $('body');
    var contentWrapper = $('.content-wrapper');
    var scroller = $('.container-scroller');
    var footer = $('.footer');
    var sidebar = $('.sidebar');

    //Add active class to nav-link based on url dynamically
    //Active class can be hard coded directly in html file also as required

    function addActiveClass(element) {
      if (current === "") {
        //for root url
        if (element.attr('href').indexOf("index.html") !== -1 || element.attr('href') === "/") {
          element.parents('.nav-item').last().addClass('active');
          if (element.parents('.sub-menu').length) {
            element.closest('.collapse').addClass('show');
            element.addClass('active');
          }
        }
      } else {
        //for other url
        if (element.attr('href').indexOf(current) !== -1) {
          element.parents('.nav-item').last().addClass('active');
          if (element.parents('.sub-menu').length) {
            element.closest('.collapse').addClass('show');
            element.addClass('active');
          }
          if (element.parents('.submenu-item').length) {
            element.addClass('active');
          }
        }
      }
    }

    var current = location.pathname.split("/").slice(-1)[0].replace(/^\/|\/$/g, '');
    $('.nav li a', sidebar).each(function () {
      var $this = $(this);
      addActiveClass($this);
    });

    $('.horizontal-menu .nav li a').each(function () {
      var $this = $(this);
      addActiveClass($this);
    });

    //Close other submenu in sidebar on opening any
    sidebar.on('show.bs.collapse', '.collapse', function () {
      sidebar.find('.collapse.show').collapse('hide');
    });

    // Mejorar la navegación móvil - cerrar sidebar al hacer clic
    if (window.innerWidth <= 991) {
      $('.sidebar .nav .nav-item .nav-link').on('click', function () {
        setTimeout(function () {
          body.removeClass('sidebar-open');
        }, 150);
      });
    }

    // Cerrar el menú sidebar cuando se hace clic en el backdrop
    $(document).on('click', '.sidebar-backdrop', function () {
      body.removeClass('sidebar-open');
    });

    // Manejar el botón de toggle del sidebar
    $(document).on('click', '[data-toggle="sidebar"]', function (e) {
      e.preventDefault();
      body.toggleClass('sidebar-open');

      // Ajustar el backdrop
      const backdrop = document.getElementById('sidebarBackdrop');
      if (backdrop) {
        if (body.hasClass('sidebar-open')) {
          backdrop.style.display = 'block';
          // Pequeño retraso para asegurar que la transición sea suave
          setTimeout(function () {
            backdrop.style.opacity = '1';
            backdrop.style.visibility = 'visible';
          }, 10);
        } else {
          backdrop.style.opacity = '0';
          backdrop.style.visibility = 'hidden';
          // Esperar a que termine la transición para ocultar
          setTimeout(function () {
            backdrop.style.display = 'none';
          }, 300);
        }
      }
    });

    // Manejar la adaptación de sidebar/main-panel en resize
    $(window).on('resize', function () {
      if (window.innerWidth > 991) {
        body.removeClass('sidebar-open');

        // Ocultar backdrop en pantallas grandes
        const backdrop = document.getElementById('sidebarBackdrop');
        if (backdrop) {
          backdrop.style.opacity = '0';
          backdrop.style.visibility = 'hidden';
          backdrop.style.display = 'none';
        }
      }
    });

    // Inicializar dropdowns de Bootstrap
    var dropdownElementList = [].slice.call(document.querySelectorAll('.dropdown-toggle'))
    dropdownElementList.map(function (dropdownToggleEl) {
      return new bootstrap.Dropdown(dropdownToggleEl)
    });

    // Cerrar navbar móvil cuando se hace clic en un enlace
    $('.navbar-collapse a').click(function () {
      if (window.innerWidth <= 991) {
        $('.navbar-collapse').collapse('hide');
      }
    });

    //Change sidebar and content-wrapper height
    applyStyles();

    function applyStyles() {
      //Applying perfect scrollbar
      if (!body.hasClass("rtl")) {
        if ($('.settings-panel .tab-content .tab-pane.scroll-wrapper').length) {
          const settingsPanelScroll = new PerfectScrollbar('.settings-panel .tab-content .tab-pane.scroll-wrapper');
        }
        if ($('.chats').length) {
          const chatsScroll = new PerfectScrollbar('.chats');
        }
        if (body.hasClass("sidebar-fixed")) {
          if ($('#sidebar').length) {
            var fixedSidebarScroll = new PerfectScrollbar('#sidebar .nav');
          }
        }
      }
    }

    $('[data-bs-toggle="minimize"]').on("click", function () {
      if ((body.hasClass('sidebar-toggle-display')) || (body.hasClass('sidebar-absolute'))) {
        body.toggleClass('sidebar-hidden');
      } else {
        body.toggleClass('sidebar-icon-only');
      }
    });

    //checkbox and radios
    $(".form-check label,.form-radio label").append('<i class="input-helper"></i>');

    //Horizontal menu in mobile
    $('[data-toggle="horizontal-menu-toggle"]').on("click", function () {
      $(".horizontal-menu .bottom-navbar").toggleClass("header-toggled");
    });
    // Horizontal menu navigation in mobile menu on click
    var navItemClicked = $('.horizontal-menu .page-navigation >.nav-item');
    navItemClicked.on("click", function (event) {
      if (window.matchMedia('(max-width: 991px)').matches) {
        if (!($(this).hasClass('show-submenu'))) {
          navItemClicked.removeClass('show-submenu');
        }
        $(this).toggleClass('show-submenu');
      }
    });

    // Ajustar navbar public en scroll
    $(window).scroll(function () {
      // Para menú horizontal
      if (window.matchMedia('(min-width: 992px)').matches) {
        var header = $('.horizontal-menu');
        if ($(window).scrollTop() >= 70) {
          $(header).addClass('fixed-on-scroll');
        } else {
          $(header).removeClass('fixed-on-scroll');
        }
      }

      // Para navbar público
      var publicNavbar = $('.public-navbar');
      if (publicNavbar.length && $(window).scrollTop() > 50) {
        publicNavbar.addClass('scrolled');
      } else if (publicNavbar.length) {
        publicNavbar.removeClass('scrolled');
      }
    });
  });

  // focus input when clicking on search icon
  $('#navbar-search-icon').click(function () {
    $("#navbar-search-input").focus();
  });

})(jQuery);

// Código adicional para asegurar que el toggle del sidebar funcione incluso si jQuery falla
document.addEventListener('DOMContentLoaded', function () {
  // Agregar manejador directo al botón de toggle
  const sidebarToggles = document.querySelectorAll('[data-toggle="sidebar"]');
  if (sidebarToggles.length > 0) {
    sidebarToggles.forEach(function (toggle) {
      toggle.addEventListener('click', function (e) {
        e.preventDefault();
        document.body.classList.toggle('sidebar-open');

        // Asegurarse de que el backdrop se muestre/oculte
        const backdrop = document.getElementById('sidebarBackdrop');
        if (backdrop) {
          if (document.body.classList.contains('sidebar-open')) {
            backdrop.style.display = 'block';
          } else {
            backdrop.style.display = 'none';
          }
        }
      });
    });
  }

  // Cerrar el menú cuando se hace clic en el backdrop
  const backdrop = document.getElementById('sidebarBackdrop');
  if (backdrop) {
    backdrop.addEventListener('click', function () {
      document.body.classList.remove('sidebar-open');
      backdrop.style.display = 'none';
    });
  }
});