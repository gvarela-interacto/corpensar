// Función para mejorar los modales, asegurando que el botón X funcione correctamente
document.addEventListener('DOMContentLoaded', function () {
    // Cerrar modales con la X
    document.querySelectorAll('.close, .btn-close, [data-dismiss="modal"]').forEach(function (closeButton) {
        closeButton.addEventListener('click', function () {
            const modal = this.closest('.modal');
            if (modal) {
                // Si estamos usando Bootstrap 5+
                if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                    const modalInstance = bootstrap.Modal.getInstance(modal);
                    if (modalInstance) {
                        modalInstance.hide();
                    }
                }
                // Si estamos usando Bootstrap 4 o anterior
                else if (typeof jQuery !== 'undefined' && jQuery.fn.modal) {
                    $(modal).modal('hide');
                }
                // Fallback manual
                else {
                    modal.style.display = 'none';
                    modal.classList.remove('show');
                    document.body.classList.remove('modal-open');
                    const backdrop = document.querySelector('.modal-backdrop');
                    if (backdrop) {
                        backdrop.remove();
                    }
                }
            }
        });
    });

    // Cerrar mensajes de éxito
    document.querySelectorAll('.message-toast .close-btn').forEach(function (closeButton) {
        closeButton.addEventListener('click', function () {
            const message = this.closest('.message-toast');
            if (message) {
                message.classList.add('fade-out');
                setTimeout(function () {
                    if (message.parentNode) {
                        message.parentNode.removeChild(message);
                    }
                }, 500);
            }
        });
    });
}); 