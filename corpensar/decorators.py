from django.contrib import messages
from django.shortcuts import redirect



def grupo_required(*group_names):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            # Verificar si el usuario pertenece al grupo 'Es_Super'
            if request.user.groups.filter(name='Es_Super').exists():
                return view_func(request, *args, **kwargs)
            
            # Verificar si el usuario pertenece a alguno de los grupos especificados
            if request.user.groups.filter(name__in=group_names).exists():
                return view_func(request, *args, **kwargs)
            
            # Redirigir si no pertenece a los grupos requeridos
            return redirect('index')
        
        return wrapper
    return decorator

def grupos_required(*group_names):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            # Verificar si el usuario pertenece al grupo 'Es_Super'
            if request.user.groups.filter(name='Es_Super').exists():
                return view_func(request, *args, **kwargs)
            
            # Verificar si el usuario pertenece a todos los grupos especificados
            if all(request.user.groups.filter(name=group).exists() for group in group_names):
                return view_func(request, *args, **kwargs)
            
            # Redirigir si no pertenece a los grupos requeridos
            return redirect('index')
        
        return wrapper
    return decorator