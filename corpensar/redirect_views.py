from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

@login_required
def login_redirect_view(request):
    """
    Vista personalizada para redirigir después del login según el tipo de usuario.
    Los administradores (superuser o grupo Es_Super) van al dashboard.
    Los usuarios normales van a la página de todas las encuestas.
    """
    # Verificar si el usuario es administrador
    if request.user.is_superuser or request.user.groups.filter(name="Es_Super").exists():
        # Redirigir administradores al dashboard
        return redirect("index")
    else:
        # Redirigir usuarios normales a todas las encuestas
        return redirect("todas_encuestas") 