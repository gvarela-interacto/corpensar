from django import template

register = template.Library()

@register.filter
def get(diccionario, clave):
    return diccionario.get(clave, None)