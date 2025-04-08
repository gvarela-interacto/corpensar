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

