from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter
def times(value):
    """Genera un rango de números desde 1 hasta el valor especificado"""
    try:
        return range(1, int(value) + 1)
    except (ValueError, TypeError):
        return range(1, 6)  # valor por defecto si hay error 

@register.filter
def get_item(dictionary, key):
    """Obtiene un elemento de un diccionario por su clave"""
    return dictionary.get(key, '') 

@register.filter
def unique(value, arg):
    """
    Filtra un QuerySet o lista para devolver solo los elementos con valores únicos para el campo especificado.
    Uso: {{ queryset|unique:"campo" }}
    """
    if not value:
        return []
    
    seen = set()
    unique_items = []
    
    for item in value:
        val = getattr(item, arg, None)
        if val not in seen:
            seen.add(val)
            unique_items.append(item)
    
    return unique_items 