# encuestas/templatetags/diccionario.py
from django import template

register = template.Library()

@register.filter
def dict_get(diccionario, clave):
    return diccionario.get(clave, None)
