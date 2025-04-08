from decimal import Decimal
import json
import locale
from django.contrib import messages  
from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse, HttpResponseForbidden,HttpResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.contrib.auth.hashers import make_password
from .models import *
from django.contrib.auth.decorators import login_required
locale.setlocale(locale.LC_ALL, 'es_CO.UTF-8')
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth import logout
from django import forms
from django.core.exceptions import ValidationError
import re
from .decorators import *
import csv
from datetime import datetime
from django.contrib.auth.mixins import LoginRequiredMixin

def registro_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)  # Usamos el formulario por defecto
        if form.is_valid():
            user = form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    
    return render(request, 'registration/registro.html', {'form': form})

def custom_logout(request):
    logout(request)
    return redirect('login')

@login_required
def index_view(request):
    
    return render(request, 'index.html')

#views del programa

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.views.generic import ListView
from .models import *
from .forms import *

# Vista para la página de selección de método de creación
def seleccionar_metodo_creacion(request):
    return render(request, 'Encuesta/seleccionar_metodo.html')

# Vista para crear encuesta desde cero
def crear_desde_cero(request):
    if request.method == 'POST':
        form = EncuestaForm(request.POST)
        if form.is_valid():
            encuesta = form.save(commit=False)
            encuesta.creador = request.user
            encuesta.save()
            messages.success(request, 'Encuesta creada exitosamente! Ahora puedes agregar preguntas.')
            return redirect('editar_encuesta', encuesta_id=encuesta.id)
    else:
        form = EncuestaForm()
    
    return render(request, 'Encuesta/crear_desde_cero.html', {'form': form})

# Vista para crear encuesta con IA (versión simplificada)
def crear_con_ia(request):
    if request.method == 'POST':
        # Aquí procesarías la solicitud de IA
        tema = request.POST.get('tema')
        tipo_encuesta = request.POST.get('tipo_encuesta')
        
        # Simulación de creación con IA
        encuesta = Encuesta(
            titulo=f"Encuesta generada por IA sobre {tema}",
            descripcion=f"Encuesta automática sobre {tema}",
            creador=request.user,
            es_publica=False
        )
        encuesta.save()
        
        messages.success(request, 'Encuesta generada por IA creada exitosamente!')
        return redirect('editar_encuesta', encuesta_id=encuesta.id)
    
    return render(request, 'Encuesta/crear_con_ia.html')

# Vista para duplicar encuesta
def duplicar_encuesta(request):
    if request.method == 'POST':
        encuesta_id = request.POST.get('encuesta_a_duplicar')
        encuesta_original = get_object_or_404(Encuesta, id=encuesta_id)
        
        # Duplicar la encuesta
        nueva_encuesta = Encuesta(
            titulo=f"Copia de {encuesta_original.titulo}",
            descripcion=encuesta_original.descripcion,
            creador=request.user,
            es_publica=False
        )
        nueva_encuesta.save()
        
        # Aquí deberías también duplicar las preguntas y opciones
        
        messages.success(request, 'Encuesta duplicada exitosamente!')
        return redirect('editar_encuesta', encuesta_id=nueva_encuesta.id)
    
    # Mostrar listado de encuestas para seleccionar cuál duplicar
    encuestas = Encuesta.objects.filter(creador=request.user)
    return render(request, 'Encuesta/seleccionar_para_duplicar.html', {'encuestas': encuestas})

# Vista para editar encuesta (común para todos los métodos)
def editar_encuesta(request, encuesta_id):
    encuesta = get_object_or_404(Encuesta, id=encuesta_id, creador=request.user)
    
    if request.method == 'POST':
        form = EncuestaForm(request.POST, instance=encuesta)
        if form.is_valid():
            form.save()
            messages.success(request, 'Encuesta actualizada exitosamente!')
            return redirect('editar_encuesta', encuesta_id=encuesta.id)
    else:
        form = EncuestaForm(instance=encuesta)
    
    return render(request, 'Encuesta/editar_encuesta.html', {
        'encuesta': encuesta,
        'form': form
    })

# Vista para listar encuestas del usuario


class ListaEncuestasView(LoginRequiredMixin, ListView):
    model = Encuesta
    template_name = 'Encuesta/lista_encuestas.html'
    context_object_name = 'encuestas'
    paginate_by = 10

    def get_queryset(self):
        return Encuesta.objects.filter(creador=self.request.user).order_by('-fecha_creacion')

    
class TodasEncuestasView(ListView):
    model = Encuesta
    template_name = 'Encuesta/todas_encuestas.html'
    context_object_name = 'encuestas'
    paginate_by = 10

    def get_queryset(self):
        return Encuesta.objects.all().order_by('-fecha_creacion')

def responder_encuesta(request, slug):
    encuesta = get_object_or_404(Encuesta, slug=slug)

    if not encuesta.activa or encuesta.fecha_inicio > timezone.now() or encuesta.fecha_fin < timezone.now():
        return render(request, 'encuestas/encuesta_no_disponible.html', {'encuesta': encuesta})

    if request.method == 'POST':
        form = RespuestaForm(encuesta, request.POST)
        if form.is_valid():
            respuesta_encuesta = RespuestaEncuesta.objects.create(
                encuesta=encuesta,
                usuario=request.user if request.user.is_authenticated else None,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                completada=True
            )
            for name, value in form.cleaned_data.items():
                if name.startswith('pregunta_'):
                    pregunta_id = int(name.split('_')[1])
                    try:
                        pregunta_texto = PreguntaTexto.objects.get(id=pregunta_id, encuesta=encuesta)
                        RespuestaTexto.objects.create(respuesta_encuesta=respuesta_encuesta, pregunta=pregunta_texto, valor=value)
                    except PreguntaTexto.DoesNotExist:
                        pass
                    try:
                        pregunta_mtexto = PreguntaTextoMultiple.objects.get(id=pregunta_id, encuesta=encuesta)
                        RespuestaTexto.objects.create(respuesta_encuesta=respuesta_encuesta, pregunta=pregunta_mtexto, valor=value)
                    except PreguntaTextoMultiple.DoesNotExist:
                        pass
                    try:
                        pregunta_radio = PreguntaOpcionMultiple.objects.get(id=pregunta_id, encuesta=encuesta)
                        if value == 'otro':
                            otro_valor = form.cleaned_data.get(f'otro_{pregunta_id}', '')
                            RespuestaOpcionMultiple.objects.create(respuesta_encuesta=respuesta_encuesta, pregunta=pregunta_radio, texto_otro=otro_valor)
                        else:
                            opcion = OpcionMultiple.objects.get(id=value, pregunta=pregunta_radio)
                            RespuestaOpcionMultiple.objects.create(respuesta_encuesta=respuesta_encuesta, pregunta=pregunta_radio, opcion=opcion)
                    except PreguntaOpcionMultiple.DoesNotExist:
                        pass
                    try:
                        pregunta_check = PreguntaCasillasVerificacion.objects.get(id=pregunta_id, encuesta=encuesta)
                        if isinstance(value, list):
                            for opcion_id in value:
                                if opcion_id == 'otro':
                                    otro_valor = form.cleaned_data.get(f'otro_{pregunta_id}', '')
                                    RespuestaCasillasVerificacion.objects.create(respuesta_encuesta=respuesta_encuesta, pregunta=pregunta_check, texto_otro=otro_valor)
                                else:
                                    opcion = OpcionCasillaVerificacion.objects.get(id=opcion_id, pregunta=pregunta_check)
                                    RespuestaCasillasVerificacion.objects.create(respuesta_encuesta=respuesta_encuesta, pregunta=pregunta_check, opcion=opcion)
                        elif value == 'otro':
                            otro_valor = form.cleaned_data.get(f'otro_{pregunta_id}', '')
                            RespuestaCasillasVerificacion.objects.create(respuesta_encuesta=respuesta_encuesta, pregunta=pregunta_check, texto_otro=otro_valor)
                        else:
                            opcion = OpcionCasillaVerificacion.objects.get(id=value, pregunta=pregunta_check)
                            RespuestaCasillasVerificacion.objects.create(respuesta_encuesta=respuesta_encuesta, pregunta=pregunta_check, opcion=opcion)
                    except PreguntaCasillasVerificacion.DoesNotExist:
                        pass
                    try:
                        pregunta_select = PreguntaMenuDesplegable.objects.get(id=pregunta_id, encuesta=encuesta)
                        if value:
                            opcion = OpcionMenuDesplegable.objects.get(id=value, pregunta=pregunta_select)
                            # You might need a RespuestaMenuDesplegable model if you want to store the selected option
                            # For now, we'll assume storing the OpcionMenuDesplegable directly
                            # If you need the raw value, you might adjust this.
                            class RespuestaMenuDesplegable(RespuestaBase):
                                pregunta = models.ForeignKey(PreguntaMenuDesplegable, on_delete=models.CASCADE)
                                opcion = models.ForeignKey(OpcionMenuDesplegable, on_delete=models.CASCADE)
                            RespuestaMenuDesplegable.objects.create(respuesta_encuesta=respuesta_encuesta, pregunta=pregunta_select, opcion=opcion)
                    except PreguntaMenuDesplegable.DoesNotExist:
                        pass
                    try:
                        pregunta_star = PreguntaEstrellas.objects.get(id=pregunta_id, encuesta=encuesta)
                        RespuestaEstrellas.objects.create(respuesta_encuesta=respuesta_encuesta, pregunta=pregunta_star, valor=int(value))
                    except PreguntaEstrellas.DoesNotExist:
                        pass
                    try:
                        pregunta_scale = PreguntaEscala.objects.get(id=pregunta_id, encuesta=encuesta)
                        RespuestaEscala.objects.create(respuesta_encuesta=respuesta_encuesta, pregunta=pregunta_scale, valor=int(value))
                    except PreguntaEscala.DoesNotExist:
                        pass
                    try:
                        pregunta_fecha = PreguntaFecha.objects.get(id=pregunta_id, encuesta=encuesta)
                        RespuestaFecha.objects.create(respuesta_encuesta=respuesta_encuesta, pregunta=pregunta_fecha, valor=value)
                    except PreguntaFecha.DoesNotExist:
                        pass
                elif name.startswith(f'pregunta_') and '_item_' in name:
                    parts = name.split('_')
                    pregunta_id = int(parts[1])
                    item_id = int(parts[3])
                    try:
                        pregunta_matriz = PreguntaMatriz.objects.get(id=pregunta_id, encuesta=encuesta)
                        item_matriz = ItemMatrizPregunta.objects.get(id=item_id, pregunta=pregunta_matriz)
                        RespuestaMatriz.objects.create(respuesta_encuesta=respuesta_encuesta, pregunta=pregunta_matriz, item=item_matriz, valor=int(value))
                    except (PreguntaMatriz.DoesNotExist, ItemMatrizPregunta.DoesNotExist):
                        pass

            return redirect('encuestas_lista') # Replace 'encuestas_lista' with your actual success URL
    else:
        form = RespuestaForm(encuesta)

    return render(request, 'encuesta/responder_encuesta.html', {'form': form, 'encuesta': encuesta})
