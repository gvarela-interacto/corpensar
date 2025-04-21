from decimal import Decimal
from itertools import chain
from collections import Counter, defaultdict
import json
import locale
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.contrib.auth import logout
from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms import modelform_factory, formset_factory, Form
from django.db.models import Count, Avg, F, Sum, ExpressionWrapper, FloatField
from django.db.models.functions import TruncDate, Coalesce
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse, Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods
from django import forms
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from .models import (Encuesta, PreguntaTexto, PreguntaTextoMultiple, PreguntaOpcionMultiple,
                    PreguntaCasillasVerificacion, PreguntaMenuDesplegable, PreguntaEstrellas,
                    PreguntaEscala, PreguntaMatriz, PreguntaFecha, OpcionMultiple,
                    OpcionCasillaVerificacion, OpcionMenuDesplegable, Region, Municipio,
                    RespuestaEncuesta, RespuestaTexto, RespuestaTextoMultiple,
                    RespuestaOpcionMultiple, RespuestaCasillasVerificacion,
                    RespuestaOpcionMenuDesplegable, RespuestaEscala, RespuestaMatriz,
                    RespuestaFecha, RespuestaEstrellas, ItemMatrizPregunta, Categoria)
from .decorators import *
import locale
import re
import csv
from datetime import datetime, timedelta
from django.template.defaulttags import register

locale.setlocale(locale.LC_ALL, 'es_CO.UTF-8')


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
    now = timezone.now()
    
    # Estadísticas básicas
    total_encuestas = Encuesta.objects.count()
    encuestas_activas = Encuesta.objects.filter(
        activa=True,
        fecha_inicio__lte=now,
        fecha_fin__gte=now
    ).count()

    total_respuestas = RespuestaEncuesta.objects.count()
    avg_respuestas = Encuesta.objects.annotate(
        num_respuestas=Count('respuestas')
    ).aggregate(avg=Avg('num_respuestas'))['avg'] or 0

    # Alertas
    encuestas_proximo_fin = Encuesta.objects.filter(
        fecha_fin__gte=now,
        fecha_fin__lte=now + timezone.timedelta(days=3)
    )
    
    encuestas_sin_respuestas = Encuesta.objects.filter(
        activa=True
    ).annotate(
        num_respuestas=Count('respuestas')
    ).filter(num_respuestas=0).count()

    # Distribución por categoría
    distribucion_categoria = Encuesta.objects.values('categoria__nombre').annotate(
        total=Count('id')
    ).order_by('-total')

    # Distribución por región
    distribucion_region = Encuesta.objects.values(
        'region__nombre'
    ).annotate(
        total=Count('id')
    ).order_by('-total')

    # Tendencia de respuestas últimos 7 días
    una_semana_atras = now - timedelta(days=7)
    tendencia_respuestas = RespuestaEncuesta.objects.filter(
        fecha_respuesta__gte=una_semana_atras
    ).annotate(
        fecha=TruncDate('fecha_respuesta')
    ).values('fecha').annotate(
        total=Count('id')
    ).order_by('fecha')

    # Top municipios con más respuestas
    top_municipios = RespuestaEncuesta.objects.values(
        'municipio__nombre'
    ).annotate(
        total=Count('id')
    ).order_by('-total')[:5]

    # Tasa de finalización
    encuestas_stats = Encuesta.objects.annotate(
        total_preguntas=Count('preguntatexto_relacionadas') + 
                        Count('preguntaopcionmultiple_relacionadas') + 
                        Count('preguntacasillasverificacion_relacionadas') + 
                        Count('preguntamenudesplegable_relacionadas') + 
                        Count('preguntaestrellas_relacionadas') + 
                        Count('preguntaescala_relacionadas') + 
                        Count('preguntamatriz_relacionadas') + 
                        Count('preguntafecha_relacionadas'),
        respuestas_completas=Count('respuestas', distinct=True)
    ).aggregate(
        tasa_finalizacion=Avg(F('respuestas_completas') * 100.0 / F('total_preguntas'))
    )

    # Tipos de preguntas
    tipos_preguntas = []
    
    # Contar cada tipo de pregunta
    texto_count = PreguntaTexto.objects.count()
    if texto_count > 0:
        tipos_preguntas.append({'tipo': 'Texto', 'total': texto_count})
    
    texto_multiple_count = PreguntaTextoMultiple.objects.count()
    if texto_multiple_count > 0:
        tipos_preguntas.append({'tipo': 'Texto Múltiple', 'total': texto_multiple_count})
    
    opcion_multiple_count = PreguntaOpcionMultiple.objects.count()
    if opcion_multiple_count > 0:
        tipos_preguntas.append({'tipo': 'Opción Múltiple', 'total': opcion_multiple_count})
    
    casillas_count = PreguntaCasillasVerificacion.objects.count()
    if casillas_count > 0:
        tipos_preguntas.append({'tipo': 'Casillas', 'total': casillas_count})
    
    menu_count = PreguntaMenuDesplegable.objects.count()
    if menu_count > 0:
        tipos_preguntas.append({'tipo': 'Menú Desplegable', 'total': menu_count})
    
    estrellas_count = PreguntaEstrellas.objects.count()
    if estrellas_count > 0:
        tipos_preguntas.append({'tipo': 'Estrellas', 'total': estrellas_count})
    
    escala_count = PreguntaEscala.objects.count()
    if escala_count > 0:
        tipos_preguntas.append({'tipo': 'Escala', 'total': escala_count})
    
    matriz_count = PreguntaMatriz.objects.count()
    if matriz_count > 0:
        tipos_preguntas.append({'tipo': 'Matriz', 'total': matriz_count})
    
    fecha_count = PreguntaFecha.objects.count()
    if fecha_count > 0:
        tipos_preguntas.append({'tipo': 'Fecha', 'total': fecha_count})

    ultimas_respuestas = RespuestaEncuesta.objects.select_related(
        'encuesta', 'usuario'
    ).order_by('-fecha_respuesta')[:10]

    encuestas_detalle = Encuesta.objects.annotate(
        cantidad_respuestas=Count('respuestas'),
        promedio_respuestas=Avg('respuestas__id')
    ).order_by('-fecha_creacion')

    context = {
        'total_encuestas': total_encuestas,
        'encuestas_activas': encuestas_activas,
        'total_respuestas': total_respuestas,
        'avg_respuestas': round(avg_respuestas, 1),
        'encuestas_proximo_fin': encuestas_proximo_fin,
        'encuestas_sin_respuestas': encuestas_sin_respuestas,
        'distribucion_region': distribucion_region,
        'tendencia_respuestas': tendencia_respuestas,
        'top_municipios': top_municipios,
        'tasa_finalizacion': round(encuestas_stats['tasa_finalizacion'] or 0, 1),
        'tipos_preguntas': tipos_preguntas,
        'ultimas_respuestas': ultimas_respuestas,
        'encuestas_detalle': encuestas_detalle,
        'distribucion_categoria': distribucion_categoria,
    }

    return render(request, 'index.html', context)

#views del programa

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.views.generic import ListView, DetailView
from .models import *
from .forms import *

# Vista para la página de selección de método de creación
def seleccionar_metodo_creacion(request):
    return render(request, 'Encuesta/seleccionar_metodo.html')

# Vista para crear encuesta desde cero
@login_required
def crear_desde_cero(request):
    # Inicializar el formulario fuera del bloque if/else
    form = EncuestaForm()
    regiones = Region.objects.all()
    categorias = Categoria.objects.all()

    if request.method == 'POST':
        # Imprimir todos los datos del POST para debug
        # #print("Datos del POST completo:", request.POST)
        
        titulo = request.POST.get('titulo')
        slug = request.POST.get('slug')
        descripcion = request.POST.get('descripcion')
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')
        activa = bool(request.POST.get('activa'))
        es_publica = bool(request.POST.get('es_publica'))
        
        # Procesar region_id con más logs
        region_id = request.POST.get('region')
        categoria_id = request.POST.get('categoria')
        
        region = None
        categoria = None
        try:
            if region_id and region_id.strip():
                region_id = int(region_id)
                region = Region.objects.get(id=region_id)
            else:
                print("No se proporcionó region_id o estaba vacío")

            if categoria_id and categoria_id.strip():
                categoria_id = int(categoria_id)
                categoria = Categoria.objects.get(id=categoria_id)
            
        except (ValueError, Region.DoesNotExist, Categoria.DoesNotExist) as e:
            messages.error(request, f"Error al procesar la región o categoría seleccionada: {e}")
            return render(request, 'Encuesta/crear_desde_cero.html', {
                'form': form,
                'regiones': regiones,
                'categorias': categorias
            })
        
        tema = request.POST.get('tema', 'default')

        try:
            # Crear la encuesta y guardarla en una variable
            encuesta = Encuesta.objects.create(
                titulo=titulo,
                slug=slug,
                descripcion=descripcion,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                activa=activa,
                es_publica=es_publica,
                creador=request.user,
                region=region,
                categoria=categoria,
                municipio=None,
                tema=tema
            )
            
        except Exception as e:
            messages.error(request, f"Error al crear la encuesta: {e}")
            return render(request, 'Encuesta/crear_desde_cero.html', {
                'form': form,
                'regiones': regiones,
                'categorias': categorias
            })
        
        # Obtener preguntas del formulario
        preguntas_ids = set()
        
        # Identificar todos los IDs de preguntas
        for key in request.POST:
            if key.startswith('questions[') and '][text]' in key:
                pregunta_id = key.split('[')[1].split(']')[0]
                preguntas_ids.add(pregunta_id)
        
        # Si no hay preguntas, crear una por defecto
        if not preguntas_ids:
            preguntas_ids = {'1'}
            request.POST = request.POST.copy()
            request.POST.update({
                'questions[1][text]': "¿Cuál es su opinión sobre esta encuesta?",
                'questions[1][type]': 'TEXT',
                'questions[1][required]': 'true',
                'questions[1][order]': '1',
                'questions[1][section]': 'General'  # Asignar a la sección por defecto
            })
        
        # Procesar cada pregunta
        for pregunta_id in preguntas_ids:
            # Extraer atributos comunes
            texto = request.POST.get(f'questions[{pregunta_id}][text]', '')
            tipo = request.POST.get(f'questions[{pregunta_id}][type]', 'TEXT')
            requerida = request.POST.get(f'questions[{pregunta_id}][required]', 'true') == 'true'
            orden = int(request.POST.get(f'questions[{pregunta_id}][order]', pregunta_id))
            ayuda = request.POST.get(f'questions[{pregunta_id}][help]', '')
            seccion = request.POST.get(f'questions[{pregunta_id}][section]', 'General')  # Usar 'General' como valor por defecto
            
            # Crear el tipo específico de pregunta según el valor de 'tipo'
            if tipo == 'TEXT':
                PreguntaTexto.objects.create(
                    encuesta=encuesta,
                    texto=texto,
                    tipo=tipo,
                    requerida=requerida,
                    orden=orden,
                    ayuda=ayuda,
                    seccion=seccion,
                    max_longitud=request.POST.get(f'questions[{pregunta_id}][max_length]', '250'),
                    placeholder=request.POST.get(f'questions[{pregunta_id}][placeholder]', '')
                )
            elif tipo == 'MTEXT':
                PreguntaTextoMultiple.objects.create(
                    encuesta=encuesta,
                    texto=texto,
                    tipo=tipo,
                    requerida=requerida,
                    orden=orden,
                    ayuda=ayuda,
                    seccion=seccion,
                    max_longitud=request.POST.get(f'questions[{pregunta_id}][max_length]', '1000'),
                    filas=int(request.POST.get(f'questions[{pregunta_id}][rows]', '4')),
                    placeholder=request.POST.get(f'questions[{pregunta_id}][placeholder]', '')
                )
            elif tipo == 'RADIO':
                pregunta_obj = PreguntaOpcionMultiple.objects.create(
                    encuesta=encuesta,
                    texto=texto,
                    tipo=tipo,
                    requerida=requerida,
                    orden=orden,
                    ayuda=ayuda,
                    seccion=seccion
                )
                # Procesar opciones si están disponibles
                for key in request.POST:
                    if key.startswith(f'questions[{pregunta_id}][opciones][') and '][texto]' in key:
                        opcion_index = key.split('[')[3].split(']')[0]
                        opcion_texto = request.POST.get(f'questions[{pregunta_id}][opciones][{opcion_index}][texto]', '')
                        opcion_orden = int(request.POST.get(f'questions[{pregunta_id}][opciones][{opcion_index}][orden]', opcion_index))
                        OpcionMultiple.objects.create(
                            pregunta=pregunta_obj,
                            texto=opcion_texto,
                            orden=opcion_orden
                        )
                
            elif tipo == 'CHECK':
                pregunta_obj = PreguntaCasillasVerificacion.objects.create(
                    encuesta=encuesta,
                    texto=texto,
                    tipo=tipo,
                    requerida=requerida,
                    orden=orden,
                    ayuda=ayuda,
                    seccion=seccion,
                    min_selecciones=int(request.POST.get(f'questions[{pregunta_id}][min_selections]', '1')),
                    max_selecciones=request.POST.get(f'questions[{pregunta_id}][max_selections]', '') or None
                )
                # Procesar opciones si están disponibles
                for key in request.POST:
                    if key.startswith(f'questions[{pregunta_id}][opciones][') and '][texto]' in key:
                        opcion_index = key.split('[')[3].split(']')[0]
                        opcion_texto = request.POST.get(f'questions[{pregunta_id}][opciones][{opcion_index}][texto]', '')
                        opcion_orden = int(request.POST.get(f'questions[{pregunta_id}][opciones][{opcion_index}][orden]', opcion_index))
                        OpcionCasillaVerificacion.objects.create(
                            pregunta=pregunta_obj,
                            texto=opcion_texto,
                            orden=opcion_orden
                        )
                
            elif tipo == 'SELECT':
                pregunta_obj = PreguntaMenuDesplegable.objects.create(
                    encuesta=encuesta,
                    texto=texto,
                    tipo=tipo,
                    requerida=requerida,
                    orden=orden,
                    ayuda=ayuda,
                    seccion=seccion,
                    opcion_vacia=request.POST.get(f'questions[{pregunta_id}][empty_option]', 'true') == 'true',
                    texto_vacio=request.POST.get(f'questions[{pregunta_id}][empty_text]', 'Seleccione...')
                )
                # Procesar opciones si están disponibles
                for key in request.POST:
                    if key.startswith(f'questions[{pregunta_id}][opciones][') and '][texto]' in key:
                        opcion_index = key.split('[')[3].split(']')[0]
                        opcion_texto = request.POST.get(f'questions[{pregunta_id}][opciones][{opcion_index}][texto]', '')
                        opcion_orden = int(request.POST.get(f'questions[{pregunta_id}][opciones][{opcion_index}][orden]', opcion_index))
                        OpcionMenuDesplegable.objects.create(
                            pregunta=pregunta_obj,
                            texto=opcion_texto,
                            orden=opcion_orden
                        )
                
            elif tipo == 'STAR':
                PreguntaEstrellas.objects.create(
                    encuesta=encuesta,
                    texto=texto,
                    tipo=tipo,
                    requerida=requerida,
                    orden=orden,
                    ayuda=ayuda,
                    seccion=seccion,
                    max_estrellas=int(request.POST.get(f'questions[{pregunta_id}][max_stars]', '5')),
                    etiqueta_inicio=request.POST.get(f'questions[{pregunta_id}][label_start]', 'Muy malo'),
                    etiqueta_fin=request.POST.get(f'questions[{pregunta_id}][label_end]', 'Excelente')
                )
                
            elif tipo == 'SCALE':
                PreguntaEscala.objects.create(
                    encuesta=encuesta,
                    texto=texto,
                    tipo=tipo,
                    requerida=requerida,
                    orden=orden,
                    ayuda=ayuda,
                    seccion=seccion,
                    min_valor=int(request.POST.get(f'questions[{pregunta_id}][min_value]', '1')),
                    max_valor=int(request.POST.get(f'questions[{pregunta_id}][max_value]', '5')),
                    paso=int(request.POST.get(f'questions[{pregunta_id}][step]', '1')),
                    etiqueta_min=request.POST.get(f'questions[{pregunta_id}][label_min]', 'Muy en desacuerdo'),
                    etiqueta_max=request.POST.get(f'questions[{pregunta_id}][label_max]', 'Muy de acuerdo')
                )
                
            elif tipo == 'MATRIX':
                # Crear la escala para la matriz
                escala = PreguntaEscala.objects.create(
                    encuesta=encuesta,
                    texto="Escala para matriz",
                    tipo='SCALE',
                    requerida=True,
                    orden=0,
                    min_valor=int(request.POST.get(f'questions[{pregunta_id}][scale][min_valor]', '1')),
                    max_valor=int(request.POST.get(f'questions[{pregunta_id}][scale][max_valor]', '5')),
                    paso=int(request.POST.get(f'questions[{pregunta_id}][scale][paso]', '1')),
                    etiqueta_min=request.POST.get(f'questions[{pregunta_id}][scale][etiqueta_min]', 'Muy en desacuerdo'),
                    etiqueta_max=request.POST.get(f'questions[{pregunta_id}][scale][etiqueta_max]', 'Muy de acuerdo')
                )
                
                pregunta_obj = PreguntaMatriz.objects.create(
                    encuesta=encuesta,
                    texto=texto,
                    tipo=tipo,
                    requerida=requerida,
                    orden=orden,
                    ayuda=ayuda,
                    seccion=seccion,
                    escala=escala
                )
                
                # Procesar los ítems de la matriz
                for key in request.POST:
                    if key.startswith(f'questions[{pregunta_id}][items][') and '][texto]' in key:
                        item_index = key.split('[')[3].split(']')[0]
                        item_texto = request.POST.get(f'questions[{pregunta_id}][items][{item_index}][texto]', '')
                        item_orden = int(request.POST.get(f'questions[{pregunta_id}][items][{item_index}][orden]', item_index))
                        ItemMatrizPregunta.objects.create(
                            pregunta=pregunta_obj,
                            texto=item_texto,
                            orden=item_orden
                        )
                
            elif tipo == 'DATE':
                PreguntaFecha.objects.create(
                    encuesta=encuesta,
                    texto=texto,
                    tipo=tipo,
                    requerida=requerida,
                    orden=orden,
                    ayuda=ayuda,
                    seccion=seccion,
                    incluir_hora=False
                )
                
            elif tipo == 'DATETIME':
                PreguntaFecha.objects.create(
                    encuesta=encuesta,
                    texto=texto,
                    tipo=tipo,
                    requerida=requerida,
                    orden=orden,
                    ayuda=ayuda,
                    seccion=seccion,
                    incluir_hora=True
                )
                
            else:
                # Si el tipo no es reconocido, crear una pregunta base
                PreguntaBase.objects.create(
                    encuesta=encuesta,
                    texto=texto,
                    tipo=tipo,
                    requerida=requerida,
                    orden=orden,
                    ayuda=ayuda,
                    seccion=seccion
                )

        # Redirigir a alguna vista después de crear la encuesta
        return redirect('lista_encuestas')
    
    return render(request, 'Encuesta/crear_desde_cero.html', {
        'form': form,
        'regiones': regiones,
        'categorias': categorias
    })

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
@login_required
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
    
    # Obtener todas las preguntas de la encuesta
    preguntas = []
    preguntas.extend(encuesta.preguntatexto_relacionadas.all())
    preguntas.extend(encuesta.preguntatextomultiple_relacionadas.all())
    preguntas.extend(encuesta.preguntaopcionmultiple_relacionadas.all())
    preguntas.extend(encuesta.preguntacasillasverificacion_relacionadas.all())
    preguntas.extend(encuesta.preguntamenudesplegable_relacionadas.all())
    preguntas.extend(encuesta.preguntaestrellas_relacionadas.all())
    preguntas.extend(encuesta.preguntaescala_relacionadas.all())
    preguntas.extend(encuesta.preguntamatriz_relacionadas.all())
    preguntas.extend(encuesta.preguntafecha_relacionadas.all())
    
    # Ordenar preguntas por orden
    preguntas.sort(key=lambda x: x.orden)
    
    return render(request, 'Encuesta/editar_encuesta.html', {
        'encuesta': encuesta,
        'form': form,
        'preguntas': preguntas
    })

# Vista para listar encuestas del usuario

class ListaEncuestasView(LoginRequiredMixin, ListView):
    model = Encuesta
    template_name = 'Encuesta/lista_encuestas.html'
    context_object_name = 'encuestas'
    paginate_by = 10

    def get_queryset(self):
        # Usar select_related para cargar la región en la misma consulta
        return Encuesta.objects.select_related('region').filter(
            creador=self.request.user
        ).order_by('-fecha_creacion')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar debug info
        
        return context

    
class TodasEncuestasView(ListView):
    model = Encuesta
    template_name = 'Encuesta/todas_encuestas.html'
    context_object_name = 'encuestas'
    paginate_by = 10

    def get_queryset(self):
        return Encuesta.objects.select_related('region', 'creador').order_by('-fecha_creacion')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar debug info
        
        return context

class ResultadosEncuestaView(DetailView):
    model = Encuesta
    template_name = 'Encuesta/resultados_encuesta.html'
    context_object_name = 'encuesta'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        encuesta = self.object
        total_respuestas = encuesta.respuestas.count()

        preguntas = sorted(
            chain(
                encuesta.preguntatexto_relacionadas.all(),
                encuesta.preguntatextomultiple_relacionadas.all(),
                encuesta.preguntaopcionmultiple_relacionadas.all(),
                encuesta.preguntacasillasverificacion_relacionadas.all(),
                encuesta.preguntamenudesplegable_relacionadas.all(),
                encuesta.preguntaestrellas_relacionadas.all(),
                encuesta.preguntaescala_relacionadas.all(),
                encuesta.preguntamatriz_relacionadas.all(),
                encuesta.preguntafecha_relacionadas.all(),
            ),
            key=lambda x: x.orden
        )

        preguntas_con_datos = []

        for pregunta in preguntas:
            tipo = pregunta.__class__.__name__.lower()
            datos_pregunta = {
                'pregunta': pregunta,
                'tipo': tipo,
                'total_respuestas': total_respuestas
            }

            if tipo == 'preguntaopcionmultiple':
                respuestas = RespuestaOpcionMultiple.objects.filter(pregunta=pregunta)
                opciones = {op.texto: {'cantidad': 0, 'porcentaje': 0} for op in pregunta.opciones.all()}
                total_respuestas_pregunta = respuestas.count()  # Total de respuestas para esta pregunta
                
                for r in respuestas:
                    opciones[r.opcion.texto]['cantidad'] += 1
                
                for opcion, datos in opciones.items():
                    datos['porcentaje'] = (datos['cantidad'] / total_respuestas_pregunta * 100) if total_respuestas_pregunta > 0 else 0
                
                datos_pregunta['datos'] = opciones
                datos_pregunta['total_respuestas_pregunta'] = total_respuestas_pregunta

            elif tipo == 'preguntacasillasverificacion':
                respuestas = RespuestaCasillasVerificacion.objects.filter(pregunta=pregunta)
                opciones = {op.texto: {'cantidad': 0, 'porcentaje': 0} for op in pregunta.opciones.all()}
                
                # Contar todas las selecciones (no respuestas)
                total_selecciones = respuestas.count()
                
                for r in respuestas:
                    opciones[r.opcion.texto]['cantidad'] += 1
                
                # Calcular porcentaje basado en total de selecciones
                for opcion, datos in opciones.items():
                    datos['porcentaje'] = (datos['cantidad'] / total_selecciones * 100) if total_selecciones > 0 else 0
                
                datos_pregunta['datos'] = opciones
                datos_pregunta['total_selecciones'] = total_selecciones  # Agregar esto para el template

            elif tipo == 'preguntamenudesplegable':
                # Similar a opción múltiple
                respuestas = RespuestaOpcionMenuDesplegable.objects.filter(pregunta=pregunta)
                opciones = {op.texto: {'cantidad': 0, 'porcentaje': 0} for op in pregunta.opciones.all()}
                
                for r in respuestas:
                    opciones[r.opcion.texto]['cantidad'] += 1
                
                for opcion, datos in opciones.items():
                    datos['porcentaje'] = (datos['cantidad'] / total_respuestas * 100) if total_respuestas > 0 else 0
                
                datos_pregunta['datos'] = opciones

            elif tipo == 'preguntaestrellas':
                respuestas = RespuestaEstrellas.objects.filter(pregunta=pregunta).select_related('respuesta_encuesta')
                
                # Invertir los valores (1->5, 2->4, 3->3, 4->2, 5->1)
                valores = [6 - r.valor for r in respuestas]  # Esto invierte los valores (1->5, 5->1)
                
                promedio = sum(valores) / len(valores) if valores else 0
                counter = Counter(valores)
                
                # Asegurarnos de incluir todas las estrellas posibles (1-5)
                valores_completos = {i: counter.get(i, 0) for i in range(1, 6)}
                
                datos_pregunta['datos'] = {
                    'promedio': promedio,
                    'valores': valores_completos
                }
                datos_pregunta['respuestas_individuales'] = respuestas.order_by('-respuesta_encuesta__fecha_respuesta')

            elif tipo == 'preguntaescala':
                respuestas = RespuestaEscala.objects.filter(pregunta=pregunta).select_related('respuesta_encuesta')
                valores = [r.valor for r in respuestas]
                promedio = sum(valores) / len(valores) if valores else 0
                counter = Counter(valores)
                
                datos = {}
                for valor, cantidad in counter.items():
                    datos[valor] = {
                        'cantidad': cantidad,
                        'porcentaje': (cantidad / len(valores) * 100) if valores else 0
                    }
                
                datos_pregunta['datos'] = {
                    'valores': dict(sorted(datos.items())),
                    'promedio': promedio
                }
                datos_pregunta['respuestas_individuales'] = respuestas.order_by('-respuesta_encuesta__fecha_respuesta')

            elif tipo == 'preguntamatriz':
                respuestas = RespuestaMatriz.objects.filter(pregunta=pregunta)
                datos = defaultdict(Counter)
                
                for r in respuestas:
                    datos[r.item.texto][r.valor] += 1
                
                min_val = pregunta.escala.min_valor
                max_val = pregunta.escala.max_valor
                paso = pregunta.escala.paso
                
                valores_escala = []
                current = min_val
                while current <= max_val:
                    valores_escala.append(current)
                    current += paso
                if max_val not in valores_escala:
                    valores_escala.append(max_val)
                
                datos_para_template = {}
                for fila, contador in datos.items():
                    total = sum(contador.values())
                    valores_fila = {}
                    
                    for valor in valores_escala:
                        cantidad = contador.get(valor, 0)
                        valores_fila[valor] = {
                            'cantidad': cantidad,
                            'porcentaje': (cantidad / total * 100) if total > 0 else 0
                        }
                    
                    datos_para_template[fila] = {
                        'valores': valores_fila,
                        'total': total
                    }
                
                datos_pregunta['datos'] = datos_para_template
                datos_pregunta['valores_escala'] = valores_escala
            elif tipo == 'preguntafecha':
                respuestas = RespuestaFecha.objects.filter(pregunta=pregunta)
                fechas = [r.valor for r in respuestas]
                datos_pregunta['datos'] = dict(Counter(fechas))

            elif tipo == 'preguntatexto':
                respuestas = RespuestaTexto.objects.filter(pregunta=pregunta)
                datos_pregunta['datos'] = [r.valor for r in respuestas]

            elif tipo == 'preguntatextomultiple':
                respuestas = RespuestaTextoMultiple.objects.filter(pregunta=pregunta)
                datos_pregunta['datos'] = [r.valor for r in respuestas]

            preguntas_con_datos.append(datos_pregunta)

        context['preguntas_con_datos'] = preguntas_con_datos
        return context


@register.filter
def percentage(value):
    """Filtro para formatear un valor como porcentaje (0-100) con 1 decimal"""
    try:
        return f"{float(value):.1f}%"
    except (ValueError, TypeError):
        return "0%"

@register.filter
def calculate_percentage(value, total):
    """Filtro para calcular el porcentaje de value sobre total"""
    try:
        # Si el valor es un diccionario, sumar sus valores
        if isinstance(value, dict):
            value = sum(value.values())
        return (float(value) / float(total)) * 100
    except (ValueError, ZeroDivisionError, TypeError):
        return 0
    
@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, 0)

@register.filter
def divide(value, arg):
    try:
        return float(value) / float(arg) * 100
    except (ValueError, ZeroDivisionError):
        return 0

def get_client_ip(request):
    """Obtiene la dirección IP del cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

class BaseEncuestaForm(Form):
    """Formulario base para todas las preguntas de encuesta"""
    def __init__(self, *args, pregunta=None, requerida=False, **kwargs):
        self.pregunta = pregunta
        self.requerida = requerida
        super().__init__(*args, **kwargs)


class TextoForm(BaseEncuestaForm):
    respuesta = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False
    )
    
    def __init__(self, *args, pregunta=None, requerida=False, **kwargs):
        super().__init__(*args, pregunta=pregunta, requerida=requerida, **kwargs)
        self.fields['respuesta'].required = requerida
        self.fields['respuesta'].widget.attrs['placeholder'] = pregunta.placeholder
        self.fields['respuesta'].widget.attrs['maxlength'] = pregunta.max_longitud


class TextoMultipleForm(BaseEncuestaForm):
    respuesta = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control'}),
        required=False
    )
    
    def __init__(self, *args, pregunta=None, requerida=False, **kwargs):
        super().__init__(*args, pregunta=pregunta, requerida=requerida, **kwargs)
        self.fields['respuesta'].required = requerida
        self.fields['respuesta'].widget.attrs['placeholder'] = pregunta.placeholder
        self.fields['respuesta'].widget.attrs['maxlength'] = pregunta.max_longitud
        self.fields['respuesta'].widget.attrs['rows'] = pregunta.filas


class OpcionMultipleForm(BaseEncuestaForm):
    opcion = forms.ModelChoiceField(
        queryset=None,
        widget=forms.RadioSelect(),
        required=False
    )
    texto_otro = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False
    )
    
    def __init__(self, *args, pregunta=None, requerida=False, **kwargs):
        super().__init__(*args, pregunta=pregunta, requerida=requerida, **kwargs)
        self.fields['opcion'].queryset = pregunta.opciones.all()
        self.fields['opcion'].required = requerida
        self.fields['opcion'].label = ""
        self.opcion_otro = pregunta.opcion_otro


class CasillasVerificacionForm(BaseEncuestaForm):
    opciones = forms.ModelMultipleChoiceField(
        queryset=None,
        widget=forms.CheckboxSelectMultiple(),
        required=False
    )
    texto_otro = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False
    )
    
    def __init__(self, *args, pregunta=None, requerida=False, **kwargs):
        super().__init__(*args, pregunta=pregunta, requerida=requerida, **kwargs)
        self.fields['opciones'].queryset = pregunta.opciones.all()
        self.fields['opciones'].required = requerida
        self.fields['opciones'].label = ""
        self.opcion_otro = pregunta.opcion_otro
        self.min_selecciones = pregunta.min_selecciones
        self.max_selecciones = pregunta.max_selecciones
    
    def clean_opciones(self):
        opciones = self.cleaned_data.get('opciones')
        if self.requerida and not opciones:
            raise ValidationError("Debes seleccionar al menos una opción.")
        
        if self.min_selecciones and len(opciones) < self.min_selecciones:
            raise ValidationError(f"Debes seleccionar al menos {self.min_selecciones} opciones.")
        
        if self.max_selecciones and len(opciones) > self.max_selecciones:
            raise ValidationError(f"Puedes seleccionar como máximo {self.max_selecciones} opciones.")
        
        return opciones


class MenuDesplegableForm(BaseEncuestaForm):
    opcion = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )
    
    def __init__(self, *args, pregunta=None, requerida=False, **kwargs):
        super().__init__(*args, pregunta=pregunta, requerida=requerida, **kwargs)
        self.fields['opcion'].queryset = pregunta.opciones.all()
        self.fields['opcion'].required = requerida
        
        # Añadir opción vacía si está configurada en la pregunta
        if pregunta.opcion_vacia:
            self.fields['opcion'].empty_label = pregunta.texto_vacio


class EstrellasForm(BaseEncuestaForm):
    valor = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'type': 'range'}),
        required=False,
        min_value=1
    )
    
    def __init__(self, *args, pregunta=None, requerida=False, **kwargs):
        super().__init__(*args, pregunta=pregunta, requerida=requerida, **kwargs)
        self.fields['valor'].required = requerida
        self.fields['valor'].min_value = 1
        self.fields['valor'].max_value = pregunta.max_estrellas
        self.fields['valor'].widget.attrs['min'] = 1
        self.fields['valor'].widget.attrs['max'] = pregunta.max_estrellas
        self.max_estrellas = pregunta.max_estrellas
        self.etiqueta_inicio = pregunta.etiqueta_inicio
        self.etiqueta_fin = pregunta.etiqueta_fin


class EscalaForm(BaseEncuestaForm):
    valor = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'type': 'range'}),
        required=False
    )
    
    def __init__(self, *args, pregunta=None, requerida=False, **kwargs):
        super().__init__(*args, pregunta=pregunta, requerida=requerida, **kwargs)
        self.fields['valor'].required = requerida
        self.fields['valor'].min_value = pregunta.min_valor
        self.fields['valor'].max_value = pregunta.max_valor
        self.fields['valor'].widget.attrs['min'] = pregunta.min_valor
        self.fields['valor'].widget.attrs['max'] = pregunta.max_valor
        self.fields['valor'].widget.attrs['step'] = pregunta.paso
        self.min_valor = pregunta.min_valor
        self.max_valor = pregunta.max_valor
        self.etiqueta_min = pregunta.etiqueta_min
        self.etiqueta_max = pregunta.etiqueta_max


class MatrizForm(BaseEncuestaForm):
    def __init__(self, *args, pregunta=None, requerida=False, **kwargs):
        super().__init__(*args, pregunta=pregunta, requerida=requerida, **kwargs)
        self.items = pregunta.items.all()
        self.escala = pregunta.escala
        
        # Crear campos dinámicamente para cada item
        for item in self.items:
            field_name = f"item_{item.id}"
            self.fields[field_name] = forms.IntegerField(
                widget=forms.NumberInput(attrs={
                    'class': 'form-control',
                    'type': 'range',
                    'min': self.escala.min_valor,
                    'max': self.escala.max_valor,
                    'step': self.escala.paso
                }),
                required=requerida,
                min_value=self.escala.min_valor,
                max_value=self.escala.max_valor,
                label=item.texto
            )


class FechaForm(BaseEncuestaForm):
    valor = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        required=False
    )
    
    def __init__(self, *args, pregunta=None, requerida=False, **kwargs):
        super().__init__(*args, pregunta=pregunta, requerida=requerida, **kwargs)
        self.fields['valor'].required = requerida
        
        # Ajustar el widget según si se incluye hora o no
        if not pregunta.incluir_hora:
            self.fields['valor'] = forms.DateField(
                widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
                required=requerida
            )


def responder_encuesta(request, slug):
    encuesta = get_object_or_404(Encuesta, slug=slug)
    preguntas = []
    secciones_unicas = []
    
    # Obtener todas las preguntas de la encuesta
    preguntas.extend(encuesta.preguntatexto_relacionadas.all())
    preguntas.extend(encuesta.preguntatextomultiple_relacionadas.all())
    preguntas.extend(encuesta.preguntaopcionmultiple_relacionadas.all())
    preguntas.extend(encuesta.preguntacasillasverificacion_relacionadas.all())
    preguntas.extend(encuesta.preguntamenudesplegable_relacionadas.all())
    preguntas.extend(encuesta.preguntaestrellas_relacionadas.all())
    preguntas.extend(encuesta.preguntaescala_relacionadas.all())
    preguntas.extend(encuesta.preguntamatriz_relacionadas.all())
    preguntas.extend(encuesta.preguntafecha_relacionadas.all())
    
    # Ordenar preguntas por orden
    preguntas.sort(key=lambda x: x.orden)
    
    # Obtener secciones únicas manteniendo el orden
    for pregunta in preguntas:
        if pregunta.seccion and pregunta.seccion not in secciones_unicas:
            secciones_unicas.append(pregunta.seccion)
    
    # Obtener municipios disponibles filtrados por la región de la encuesta
    municipios = Municipio.objects.filter(region=encuesta.region)
    
    context = {
        'encuesta': encuesta,
        'preguntas': preguntas,
        'secciones_unicas': secciones_unicas,
        'municipios': municipios,
        'tema': encuesta.tema,
    }
    
    return render(request, 'Encuesta/responder_encuesta.html', context)

def encuesta_completada(request, slug):
    """Vista de agradecimiento después de completar una encuesta"""
    encuesta = get_object_or_404(Encuesta, slug=slug)
    return render(request, 'Encuesta/encuesta_completada.html', {
        'encuesta': encuesta
    })
    

@login_required
def guardar_respuesta(request, encuesta_id):
    encuesta = get_object_or_404(Encuesta, id=encuesta_id)

    if request.method == 'POST':
        municipio_id = request.POST.get('municipio')
        municipio = Municipio.objects.filter(id=municipio_id).first() if municipio_id else None

        respuesta = RespuestaEncuesta.objects.create(
            encuesta=encuesta,
            usuario=request.user,
            municipio=municipio,  # ✅ aquí lo guardas
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            completada=True
        )

        # Procesar las respuestas
        procesar_preguntas_texto(request, respuesta)
        procesar_preguntas_opcion_multiple(request, respuesta)
        procesar_preguntas_casillas(request, respuesta)
        procesar_preguntas_desplegable(request, respuesta)
        procesar_preguntas_escala(request, respuesta)
        procesar_preguntas_matriz(request, respuesta)
        procesar_preguntas_fecha(request, respuesta)
        procesar_preguntas_estrellas(request, respuesta)

        return redirect('index')

    return redirect('todas_encuestas')

def procesar_preguntas_texto(request, respuesta):
    # Para texto simple
    for pregunta in PreguntaTexto.objects.filter(encuesta=respuesta.encuesta):
        valor = request.POST.get(f'pregunta_texto_{pregunta.id}')
        if valor:
            RespuestaTexto.objects.create(
                respuesta_encuesta=respuesta,
                pregunta=pregunta,
                valor=str(valor)  # Forzar conversión a string
            )
    
    # Para texto múltiple
    for pregunta in PreguntaTextoMultiple.objects.filter(encuesta=respuesta.encuesta):
        valor = request.POST.get(f'pregunta_textomultiple_{pregunta.id}')
        if valor:
            RespuestaTextoMultiple.objects.create(
                respuesta_encuesta=respuesta,
                pregunta=pregunta,
                valor=str(valor)  # Forzar conversión a string
            )

def procesar_preguntas_opcion_multiple(request, respuesta):
    for pregunta in PreguntaOpcionMultiple.objects.filter(encuesta=respuesta.encuesta):
        opcion_id = request.POST.get(f'pregunta_{pregunta.id}')
        if opcion_id:
            try:
                # Verificar si es una opción "otro"
                if opcion_id == 'otro':
                    texto_otro = request.POST.get(f'pregunta_otro_{pregunta.id}', '')
                    opcion = OpcionMultiple.objects.filter(pregunta=pregunta, texto='Otro').first()
                    if opcion:
                        RespuestaOpcionMultiple.objects.create(
                            respuesta_encuesta=respuesta,
                            pregunta=pregunta,
                            opcion=opcion,
                            texto_otro=texto_otro
                        )
                else:
                    # Convertir el ID a entero antes de buscar la opción
                    opcion_id = int(opcion_id)
                    opcion = OpcionMultiple.objects.get(id=opcion_id)
                    RespuestaOpcionMultiple.objects.create(
                        respuesta_encuesta=respuesta,
                        pregunta=pregunta,
                        opcion=opcion
                    )
            except (ValueError, OpcionMultiple.DoesNotExist) as e:
                #print(f"Error al procesar opción múltiple: {str(e)}")
                continue

def procesar_preguntas_casillas(request, respuesta):
    for pregunta in PreguntaCasillasVerificacion.objects.filter(encuesta=respuesta.encuesta):
        opciones = request.POST.getlist(f'pregunta_{pregunta.id}[]')
        for opcion_id in opciones:
            if opcion_id == 'otro':
                texto_otro = request.POST.get(f'pregunta_otro_{pregunta.id}', '')
                opcion = OpcionCasillaVerificacion.objects.filter(pregunta=pregunta, texto='Otro').first()
                if opcion:
                    RespuestaCasillasVerificacion.objects.create(
                        respuesta_encuesta=respuesta,
                        pregunta=pregunta,
                        opcion=opcion,
                        texto_otro=texto_otro
                    )
            else:
                opcion = OpcionCasillaVerificacion.objects.get(id=opcion_id)
                RespuestaCasillasVerificacion.objects.create(
                    respuesta_encuesta=respuesta,
                    pregunta=pregunta,
                    opcion=opcion
                )

def procesar_preguntas_desplegable(request, respuesta):
    for pregunta in PreguntaMenuDesplegable.objects.filter(encuesta=respuesta.encuesta):
        opcion_id = request.POST.get(f'pregunta_{pregunta.id}')
        if opcion_id:
            opcion = OpcionMenuDesplegable.objects.get(id=opcion_id)
            RespuestaOpcionMenuDesplegable.objects.create(
                respuesta_encuesta=respuesta,
                pregunta=pregunta,
                opcion=opcion
            )

def procesar_preguntas_escala(request, respuesta):
    for pregunta in PreguntaEscala.objects.filter(encuesta=respuesta.encuesta):
        valor = request.POST.get(f'scale_{pregunta.id}')
        if valor:
            RespuestaEscala.objects.create(
                respuesta_encuesta=respuesta,
                pregunta=pregunta,
                valor=int(valor)
            )

def procesar_preguntas_matriz(request, respuesta):
    for pregunta in PreguntaMatriz.objects.filter(encuesta=respuesta.encuesta):
        for item in pregunta.items.all():
            valor = request.POST.get(f'matrix_{pregunta.id}_{item.id}')
            if valor:
                RespuestaMatriz.objects.create(
                    respuesta_encuesta=respuesta,
                    pregunta=pregunta,
                    item=item,
                    valor=int(valor)
                )

def procesar_preguntas_fecha(request, respuesta):
    for pregunta in PreguntaFecha.objects.filter(encuesta=respuesta.encuesta):
        valor = request.POST.get(f'pregunta_{pregunta.id}')
        if valor:
            try:
                if pregunta.tipo == 'DATE':
                    valor = timezone.datetime.strptime(valor, '%Y-%m-%d').date()
                else:
                    # Intentar diferentes formatos de fecha/hora
                    try:
                        valor = timezone.datetime.strptime(valor, '%Y-%m-%dT%H:%M')
                    except ValueError:
                        try:
                            valor = timezone.datetime.strptime(valor, '%Y-%m-%d %H:%M')
                        except ValueError:
                            # Si no es un formato de fecha válido, usar la fecha actual
                            valor = timezone.now()
                
                RespuestaFecha.objects.create(
                    respuesta_encuesta=respuesta,
                    pregunta=pregunta,
                    valor=valor
                )
            except Exception as e:
                #print(f"Error al procesar fecha para pregunta {pregunta.id}: {str(e)}")
                # En caso de error, usar la fecha actual
                RespuestaFecha.objects.create(
                    respuesta_encuesta=respuesta,
                    pregunta=pregunta,
                    valor=timezone.now()
                )

def procesar_preguntas_estrellas(request, respuesta):
    for pregunta in PreguntaEstrellas.objects.filter(encuesta=respuesta.encuesta):
        valor = request.POST.get(f'rating_{pregunta.id}')
        if valor:
            RespuestaEstrellas.objects.create(
                respuesta_encuesta=respuesta,
                pregunta=pregunta,
                valor=int(valor)
            )


def regiones_y_municipios(request):
    regiones = Region.objects.prefetch_related('municipios').all()
    return render(request, 'Encuesta/regiones_y_municipios.html', {'regiones': regiones})

@login_required
def crear_region(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        if nombre:
            Region.objects.get_or_create(nombre=nombre)
            messages.success(request, f"Región '{nombre}' creada correctamente.")
            return redirect('crear_region')
        else:
            messages.error(request, "El nombre no puede estar vacío.")

    return render(request, "Encuesta/crear_region.html")

def municipios_por_region(request):
    region_id = request.GET.get('region_id')
    municipios = Municipio.objects.filter(region_id=region_id).values('id', 'nombre')
    return JsonResponse(list(municipios), safe=False)

@login_required
def crear_municipio(request):
    regiones = Region.objects.all()
    
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        region_id = request.POST.get("region")
        
        if nombre and region_id:
            region = Region.objects.filter(id=region_id).first()
            if region:
                Municipio.objects.get_or_create(nombre=nombre, region=region)
                messages.success(request, f"Municipio '{nombre}' creado en región '{region.nombre}'.")
                return redirect('crear_municipio')
            else:
                messages.error(request, "Región no encontrada.")
        else:
            messages.error(request, "Todos los campos son obligatorios.")

    return render(request, "Encuesta/crear_municipio.html", {"regiones": regiones})



@login_required
def crear_categoria(request):
    categorias = Categoria.objects.all()
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        if nombre:
            Categoria.objects.get_or_create(nombre=nombre)
            messages.success(request, f"Categoría '{nombre}' creada correctamente.")
            return redirect('crear_categoria')
        
    return render(request, "Encuesta/crear_categoria.html", {"categorias": categorias})

@login_required
def eliminar_categoria(request, categoria_id):
    """Vista para eliminar una categoría"""
    try:
        categoria = Categoria.objects.get(id=categoria_id)
        nombre = categoria.nombre
        
        # Verificar si hay encuestas asociadas a esta categoría
        encuestas_asociadas = Encuesta.objects.filter(categoria=categoria).count()
        
        if encuestas_asociadas > 0:
            messages.error(request, f"No se puede eliminar la categoría '{nombre}' porque está siendo utilizada en {encuestas_asociadas} encuesta(s).")
        else:
            categoria.delete()
            messages.success(request, f"Categoría '{nombre}' eliminada correctamente.")
    except Categoria.DoesNotExist:
        messages.error(request, "La categoría no existe.")
    
    return redirect('crear_categoria')

@login_required
def eliminar_encuesta(request, encuesta_id):
    encuesta = get_object_or_404(Encuesta, id=encuesta_id, creador=request.user)
    
    if request.method == 'POST':
        # Guardar el título para el mensaje
        titulo = encuesta.titulo
        # Eliminar la encuesta
        encuesta.delete()
        messages.success(request, f'La encuesta "{titulo}" ha sido eliminada exitosamente.')
        return redirect('lista_encuestas')
    
    return redirect('editar_encuesta', encuesta_id=encuesta_id)

@login_required
@require_http_methods(["POST"])
def editar_pregunta(request, pregunta_id):
    # Buscar la pregunta específica basada en el tipo
    pregunta = None
    for modelo in [PreguntaTexto, PreguntaTextoMultiple, PreguntaOpcionMultiple, 
                  PreguntaCasillasVerificacion, PreguntaMenuDesplegable, 
                  PreguntaEstrellas, PreguntaEscala, PreguntaMatriz, PreguntaFecha]:
        try:
            pregunta = modelo.objects.get(id=pregunta_id)
            break
        except modelo.DoesNotExist:
            continue
    
    if not pregunta:
        messages.error(request, "Pregunta no encontrada.")
        return redirect('editar_encuesta', encuesta_id=pregunta.encuesta.id)
    
    # Verificar que el usuario es el creador de la encuesta
    if pregunta.encuesta.creador != request.user:
        messages.error(request, "No tienes permiso para editar esta pregunta.")
        return redirect('editar_encuesta', encuesta_id=pregunta.encuesta.id)
    
    try:
        with transaction.atomic():
            # Actualizar campos comunes
            pregunta.texto = request.POST.get('texto')
            pregunta.orden = int(request.POST.get('orden'))
            pregunta.requerida = request.POST.get('requerida') == 'on'
            
            # Actualizar campos específicos según el tipo de pregunta
            if isinstance(pregunta, (PreguntaTexto, PreguntaTextoMultiple)):
                pregunta.placeholder = request.POST.get('placeholder', '')
                pregunta.max_longitud = int(request.POST.get('max_longitud', 250))
            
            elif isinstance(pregunta, (PreguntaOpcionMultiple, PreguntaCasillasVerificacion, PreguntaMenuDesplegable)):
                # Obtener las opciones actualizadas
                nuevas_opciones = request.POST.getlist('opciones[]')
                
                # Eliminar opciones existentes
                if isinstance(pregunta, PreguntaOpcionMultiple):
                    pregunta.opciones.all().delete()
                    OpcionModel = OpcionMultiple
                elif isinstance(pregunta, PreguntaCasillasVerificacion):
                    pregunta.opciones.all().delete()
                    OpcionModel = OpcionCasillaVerificacion
                else:
                    pregunta.opciones.all().delete()
                    OpcionModel = OpcionMenuDesplegable
                
                # Crear nuevas opciones
                for i, texto in enumerate(nuevas_opciones):
                    if texto.strip():  # Solo crear si no está vacío
                        OpcionModel.objects.create(
                            pregunta=pregunta,
                            texto=texto,
                            orden=i+1
                        )
            
            pregunta.save()
            messages.success(request, "Pregunta actualizada exitosamente.")
            
    except Exception as e:
        messages.error(request, f"Error al actualizar la pregunta: {str(e)}")
    
    return redirect('editar_encuesta', encuesta_id=pregunta.encuesta.id)

@login_required
@require_http_methods(["POST"])
def eliminar_pregunta(request, pregunta_id):
    # Buscar la pregunta específica basada en el tipo
    pregunta = None
    for modelo in [PreguntaTexto, PreguntaTextoMultiple, PreguntaOpcionMultiple, 
                  PreguntaCasillasVerificacion, PreguntaMenuDesplegable, 
                  PreguntaEstrellas, PreguntaEscala, PreguntaMatriz, PreguntaFecha]:
        try:
            pregunta = modelo.objects.get(id=pregunta_id)
            break
        except modelo.DoesNotExist:
            continue
    
    if not pregunta:
        messages.error(request, "Pregunta no encontrada.")
        return redirect('lista_encuestas')
    
    # Verificar que el usuario es el creador de la encuesta
    if pregunta.encuesta.creador != request.user:
        messages.error(request, "No tienes permiso para eliminar esta pregunta.")
        return redirect('editar_encuesta', encuesta_id=pregunta.encuesta.id)
    
    try:
        encuesta_id = pregunta.encuesta.id
        pregunta.delete()
        messages.success(request, "Pregunta eliminada exitosamente.")
    except Exception as e:
        messages.error(request, f"Error al eliminar la pregunta: {str(e)}")
    
    return redirect('editar_encuesta', encuesta_id=encuesta_id)

@login_required
def actualizar_diseno(request, encuesta_id):
    # Buscar la encuesta
    encuesta = get_object_or_404(Encuesta, id=encuesta_id)
    
    # Verificar que el usuario es el creador de la encuesta
    if encuesta.creador != request.user:
        messages.error(request, "No tienes permiso para editar esta encuesta.")
        return redirect('editar_encuesta', encuesta_id=encuesta.id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Actualizar el tema
                encuesta.tema = request.POST.get('tema', 'default')
                
                # Procesar la imagen de encabezado
                if 'eliminar_imagen' in request.POST:
                    # Si se marca la casilla de eliminar, eliminar la imagen
                    if encuesta.imagen_encabezado:
                        encuesta.imagen_encabezado.delete()
                    encuesta.imagen_encabezado = None
                elif 'imagen_encabezado' in request.FILES:
                    # Si se sube una nueva imagen, actualizar
                    encuesta.imagen_encabezado = request.FILES['imagen_encabezado']
                
                # Procesar el logotipo
                if 'eliminar_logo' in request.POST:
                    if encuesta.logotipo:
                        encuesta.logotipo.delete()
                    encuesta.logotipo = None
                elif 'logotipo' in request.FILES:
                    encuesta.logotipo = request.FILES['logotipo']
                
                # Actualizar opciones de logotipo
                encuesta.mostrar_logo = 'mostrar_logo' in request.POST
                
                # Actualizar estilos de texto y bordes
                encuesta.estilo_fuente = request.POST.get('estilo_fuente', 'default')
                encuesta.tamano_fuente = request.POST.get('tamano_fuente', 'normal')
                encuesta.estilo_bordes = request.POST.get('estilo_bordes', 'redondeado')
                
                # Actualizar opciones de fondo
                encuesta.tipo_fondo = request.POST.get('tipo_fondo', 'color')
                encuesta.color_fondo = request.POST.get('color_fondo', '#f0f2f5')
                encuesta.color_gradiente_1 = request.POST.get('color_gradiente_1', '#4361ee')
                encuesta.color_gradiente_2 = request.POST.get('color_gradiente_2', '#3a0ca3')
                
                # Procesar imagen de fondo
                if 'eliminar_imagen_fondo' in request.POST:
                    if encuesta.imagen_fondo:
                        encuesta.imagen_fondo.delete()
                    encuesta.imagen_fondo = None
                elif 'imagen_fondo' in request.FILES:
                    encuesta.imagen_fondo = request.FILES['imagen_fondo']
                
                # Actualizar patrón de fondo
                if encuesta.tipo_fondo == 'patron':
                    encuesta.patron_fondo = request.POST.get('patron_fondo', 'patron1')
                
                # Guardar los cambios
                encuesta.save()
                
                messages.success(request, "Diseño actualizado exitosamente.")
        except Exception as e:
            messages.error(request, f"Error al actualizar el diseño: {str(e)}")
    
    return redirect('editar_encuesta', encuesta_id=encuesta.id)

@login_required
def preview_diseno(request, encuesta_id):
    encuesta = get_object_or_404(Encuesta, id=encuesta_id, creador=request.user)
    
    # Obtener la primera pregunta de cada tipo para mostrar en la vista previa
    preguntas_ejemplo = []
    
    # Obtener una pregunta de texto
    pregunta_texto = PreguntaTexto.objects.filter(encuesta=encuesta).first()
    if pregunta_texto:
        preguntas_ejemplo.append(pregunta_texto)
    
    # Obtener una pregunta de opción múltiple
    pregunta_opciones = PreguntaOpcionMultiple.objects.filter(encuesta=encuesta).first()
    if pregunta_opciones:
        preguntas_ejemplo.append(pregunta_opciones)
    
    # Si no hay suficientes preguntas, crear una pregunta de ejemplo
    if not preguntas_ejemplo:
        pregunta_ejemplo = {
            'texto': 'Esta es una pregunta de ejemplo para mostrar el diseño',
            'tipo': 'TEXT',
            'requerida': True,
            'ayuda': 'Este texto es solo para mostrar cómo se verá la encuesta con el diseño seleccionado.'
        }
        preguntas_ejemplo.append(pregunta_ejemplo)
    
    # Si se proporciona un tema en la URL, usarlo para la vista previa
    tema_preview = request.GET.get('tema', encuesta.tema)
    
    context = {
        'encuesta': encuesta,
        'preguntas': preguntas_ejemplo,
        'tema_preview': tema_preview,
        'es_preview': True
    }
    
    return render(request, 'Encuesta/preview_diseno.html', context)

@login_required
@require_http_methods(["POST"])
def agregar_pregunta(request, encuesta_id):
    try:
        encuesta = Encuesta.objects.get(id=encuesta_id)
        
        # Verificar que el usuario sea el propietario de la encuesta
        if encuesta.usuario != request.user:
            return JsonResponse({'error': 'No tienes permiso para modificar esta encuesta'}, status=403)
        
        # Obtener datos del formulario
        texto = request.POST.get('texto')
        tipo = request.POST.get('tipo')
        orden = request.POST.get('orden')
        requerida = request.POST.get('requerida') == 'on'
        ayuda = request.POST.get('ayuda', '')
        
        # Crear la pregunta según el tipo
        if tipo == 'TEXT':
            pregunta = PreguntaTexto.objects.create(
                encuesta=encuesta,
                texto=texto,
                orden=orden,
                requerida=requerida,
                ayuda=ayuda
            )
        elif tipo == 'MTEXT':
            pregunta = PreguntaTextoMultiple.objects.create(
                encuesta=encuesta,
                texto=texto,
                orden=orden,
                requerida=requerida,
                ayuda=ayuda
            )
        elif tipo in ['RADIO', 'CHECK', 'SELECT']:
            # Crear pregunta de opción múltiple
            if tipo == 'RADIO':
                pregunta = PreguntaOpcionMultiple.objects.create(
                    encuesta=encuesta,
                    texto=texto,
                    orden=orden,
                    requerida=requerida,
                    ayuda=ayuda
                )
            elif tipo == 'CHECK':
                pregunta = PreguntaCasillasVerificacion.objects.create(
                    encuesta=encuesta,
                    texto=texto,
                    orden=orden,
                    requerida=requerida,
                    ayuda=ayuda
                )
            else:  # SELECT
                pregunta = PreguntaMenuDesplegable.objects.create(
                    encuesta=encuesta,
                    texto=texto,
                    orden=orden,
                    requerida=requerida,
                    ayuda=ayuda
                )
            
            # Agregar opciones
            opciones = request.POST.getlist('opciones[]')
            for i, opcion_texto in enumerate(opciones):
                if opcion_texto.strip():  # Solo crear si no está vacío
                    if tipo == 'RADIO':
                        OpcionMultiple.objects.create(
                            pregunta=pregunta,
                            texto=opcion_texto,
                            orden=i+1
                        )
                    elif tipo == 'CHECK':
                        OpcionCasillaVerificacion.objects.create(
                            pregunta=pregunta,
                            texto=opcion_texto,
                            orden=i+1
                        )
                    else:  # SELECT
                        OpcionMenuDesplegable.objects.create(
                            pregunta=pregunta,
                            texto=opcion_texto,
                            orden=i+1
                        )
                    
        elif tipo == 'SCALE':
            # Crear pregunta de escala
            escala_min = request.POST.get('escala_min', 1)
            escala_max = request.POST.get('escala_max', 5)
            escala_paso = request.POST.get('escala_paso', 1)
            
            pregunta = PreguntaEscala.objects.create(
                encuesta=encuesta,
                texto=texto,
                orden=orden,
                requerida=requerida,
                ayuda=ayuda,
                valor_minimo=escala_min,
                valor_maximo=escala_max,
                paso=escala_paso
            )
            
        elif tipo == 'MATRIX':
            # Crear pregunta de matriz
            pregunta = PreguntaMatriz.objects.create(
                encuesta=encuesta,
                texto=texto,
                orden=orden,
                requerida=requerida,
                ayuda=ayuda
            )
            
            # Agregar filas y columnas
            filas = request.POST.getlist('filas[]')
            columnas = request.POST.getlist('columnas[]')
            
            for i, fila_texto in enumerate(filas):
                if fila_texto.strip():
                    ItemMatrizPregunta.objects.create(
                        pregunta=pregunta,
                        texto=fila_texto,
                        orden=i+1
                    )
            
            for i, columna_texto in enumerate(columnas):
                if columna_texto.strip():
                    ColumnaMatriz.objects.create(
                        pregunta=pregunta,
                        texto=columna_texto,
                        orden=i+1
                    )
                    
        elif tipo == 'DATE':
            pregunta = PreguntaFecha.objects.create(
                encuesta=encuesta,
                texto=texto,
                orden=orden,
                requerida=requerida,
                ayuda=ayuda
            )
            
        elif tipo == 'STARS':
            pregunta = PreguntaEstrellas.objects.create(
                encuesta=encuesta,
                texto=texto,
                orden=orden,
                requerida=requerida,
                ayuda=ayuda
            )
            
        # Reordenar las preguntas si es necesario
        preguntas = encuesta.obtener_preguntas().filter(orden__gte=orden)
        for p in preguntas:
            if p != pregunta:
                p.orden += 1
                p.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Pregunta agregada correctamente',
            'pregunta_id': pregunta.id
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=400)

@login_required
def estadisticas_municipios(request):
    """
    Vista que retorna estadísticas de encuestas por municipio
    """
    # Obtener estadísticas por municipio
    estadisticas = {}
    
    # Obtener todos los municipios
    municipios = Municipio.objects.all()
    
    for municipio in municipios:
        # Obtener encuestas por municipio
        total_encuestas = Encuesta.objects.filter(municipio=municipio).count()
        
        # Obtener respuestas por municipio
        total_respuestas = RespuestaEncuesta.objects.filter(encuesta__municipio=municipio).count()
        
        # Calcular tasa de finalización
        tasa_finalizacion = 0
        if total_encuestas > 0:
            encuestas_con_respuestas = Encuesta.objects.filter(
                municipio=municipio,
                respuesta__isnull=False
            ).distinct().count()
            tasa_finalizacion = round((encuestas_con_respuestas / total_encuestas) * 100, 2)
        
        estadisticas[municipio.id] = {
            'id': municipio.id,
            'nombre': municipio.nombre,
            'totalEncuestas': total_encuestas,
            'totalRespuestas': total_respuestas,
            'tasaFinalizacion': tasa_finalizacion,
            'region': municipio.region.nombre if municipio.region else 'Sin región'
        }
    
    return JsonResponse({
        'estadisticas': estadisticas
    })