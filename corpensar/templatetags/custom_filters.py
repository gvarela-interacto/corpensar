from django import template

register = template.Library()

@register.filter
def times(value):
    """Genera un rango de números desde 1 hasta el valor especificado"""
    try:
        return range(1, int(value) + 1)
    except (ValueError, TypeError):
        return range(1, 6)  # valor por defecto si hay error 