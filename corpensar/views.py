from itertools import chain
from collections import Counter, defaultdict
import json
import locale
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth import logout
from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms import Form
from django.db.models import Count, Avg, F, Max, Q # Añadir Q
from django.db.models.functions import TruncDate
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods
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
                    RespuestaFecha, RespuestaEstrellas, ItemMatrizPregunta, Categoria,
                    PQRSFD, Subcategoria, ArchivoRespuesta, ArchivoAdjuntoPQRSFD,
                    GrupoInteres)
from .decorators import *
import locale
from datetime import timedelta
from django.template.defaulttags import register
import os
from django.urls import reverse
from django.core.serializers.json import DjangoJSONEncoder

locale.setlocale(locale.LC_ALL, 'es_CO.UTF-8')


def registro_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)  # Usamos el formulario por defecto
        if form.is_valid():
            user = form.save()
            # Autenticar al usuario automáticamente después del registro
            from django.contrib.auth import login as auth_login
            from django.contrib.auth import authenticate
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            auth_login(request, user)
            # Redirigir a todas las encuestas
            return redirect('todas_encuestas')
    else:
        form = UserCreationForm()
    
    return render(request, 'registration/registro.html', {'form': form})

def custom_logout(request):
    logout(request)
    return redirect('login')



@login_required
def index_view(request):
    """
    Vista principal del dashboard que muestra estadísticas y métricas del sistema.
    Esta función recopila y procesa datos para mostrar:
    - Estadísticas generales de encuestas
    - Distribución de respuestas
    - Tendencias y métricas de participación
    - Alertas y estados de PQRSFD
    """
    now = timezone.now()
    one_week_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    # ===== ESTADÍSTICAS GENERALES ENCUESTAS =====
    total_encuestas = Encuesta.objects.count()
    total_respuestas = RespuestaEncuesta.objects.count()
    encuestas_activas_qs = Encuesta.objects.filter(
        activa=True,
        fecha_inicio__lte=now,
        fecha_fin__gte=now
    )
    encuestas_activas = encuestas_activas_qs.count()
    encuestas_publicas_activas_qs = encuestas_activas_qs.filter(es_publica=True)
    encuestas_publicas_activas = list(encuestas_publicas_activas_qs) # Mantener lista para otras partes
    encuestas_publicas_count = len(encuestas_publicas_activas) # Conteo específico de públicas y activas

    # Grupos de interes
    grupos_interes = GrupoInteres.objects.all()
    # Regiones para el filtro
    regiones = Region.objects.all()
    # Categorías para el filtro
    categorias = Categoria.objects.all()

    # Conteo Total Públicas vs Privadas
    conteo_publicas_privadas = Encuesta.objects.aggregate(
        publicas=Count('id', filter=Q(es_publica=True)),
        privadas=Count('id', filter=Q(es_publica=False))
    )

    # Encuestas creadas recientemente
    encuestas_creadas_7d = Encuesta.objects.filter(fecha_creacion__gte=one_week_ago).count()
    encuestas_creadas_30d = Encuesta.objects.filter(fecha_creacion__gte=thirty_days_ago).count()

    # ===== CÁLCULO DE ENCUESTAS RESPONDIDAS =====
    encuestas_con_respuestas_ids = RespuestaEncuesta.objects.values_list('encuesta_id', flat=True).distinct()
    total_encuesta_respondidas = len(encuestas_con_respuestas_ids)

    # Encuestas respondidas activas (contar respuestas de encuestas públicas y activas)
    total_encuestas_respondidas_activas_count = RespuestaEncuesta.objects.filter(
        encuesta__in=encuestas_publicas_activas_qs # Usar el queryset ya filtrado
    ).count()

    # ===== MÉTRICAS DE PARTICIPACIÓN =====
    avg_respuestas = Encuesta.objects.annotate(
        num_respuestas=Count('respuestas')
    ).aggregate(avg=Avg('num_respuestas'))['avg'] or 0

    # Encuestas activas SIN respuestas
    encuestas_activas_ids = encuestas_activas_qs.values_list('id', flat=True) # Usar queryset ya filtrado
    encuestas_activas_con_respuestas_ids = set(RespuestaEncuesta.objects.filter(
        encuesta_id__in=encuestas_activas_ids
    ).values_list('encuesta_id', flat=True).distinct())
    encuestas_sin_respuestas_count = len(encuestas_activas_ids) - len(encuestas_activas_con_respuestas_ids)
    

    tasa_finalizacion = (total_encuesta_respondidas / total_encuestas) * 100 if total_encuestas > 0 else 0

    # ===== ALERTAS Y NOTIFICACIONES =====
    encuestas_proximo_fin = Encuesta.objects.filter(
        activa=True,
        fecha_fin__gte=now,
        fecha_fin__lte=now + timezone.timedelta(days=3)
    ).order_by('fecha_fin')

    # ===== DISTRIBUCIONES Y TENDENCIAS (ENCUESTAS) =====

    # --- Colores base para gráficos (más opciones) ---
    base_colors = ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b', '#858796', '#5a5c69', '#6f42c1', '#20c997', '#6610f2', '#fd7e14', '#dc3545', '#6c757d', '#28a745', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    # --- Distribución por categoría ---
    distribucion_categoria_qs = Encuesta.objects.values('categoria__nombre').annotate(
        total=Count('id')
    ).order_by('-total')
    categoria_labels = [item['categoria__nombre'] or 'Sin Categoría' for item in distribucion_categoria_qs]
    categoria_data = [item['total'] for item in distribucion_categoria_qs]
    distribucion_categoria_chart_data = {
        'labels': categoria_labels,
        'datasets': [{
            'label': 'Encuestas por Categoría',
            'data': categoria_data,
            'backgroundColor': base_colors[:len(categoria_labels)],
            'borderColor': 'rgba(255, 255, 255, 0.8)',
            'borderWidth': 1
        }]
    }
    distribucion_categoria_json = json.dumps(distribucion_categoria_chart_data)

    # --- Distribución por Subcategoría ---
    distribucion_subcategoria_qs = Encuesta.objects.values('subcategoria__nombre').annotate(
        total=Count('id')
    ).exclude(subcategoria__nombre__isnull=True).order_by('-total') # Excluir nulos
    subcategoria_labels = [item['subcategoria__nombre'] for item in distribucion_subcategoria_qs]
    subcategoria_data = [item['total'] for item in distribucion_subcategoria_qs]
    distribucion_subcategoria_chart_data = {
        'labels': subcategoria_labels,
        'datasets': [{
            'label': 'Encuestas por Subcategoría',
            'data': subcategoria_data,
            'backgroundColor': base_colors[len(categoria_labels):len(categoria_labels)+len(subcategoria_labels)], # Usar colores diferentes
            'borderColor': 'rgba(255, 255, 255, 0.8)',
            'borderWidth': 1
        }]
    }
    distribucion_subcategoria_json = json.dumps(distribucion_subcategoria_chart_data)


    # --- Distribución por Tema ---
    distribucion_tema_qs = Encuesta.objects.values('tema').annotate(
        total=Count('id')
    ).order_by('-total')
    # Mapear códigos de tema a nombres legibles si es necesario (usando TEMAS del modelo Encuesta)
    tema_dict = dict(Encuesta.TEMAS)
    tema_labels = [str(tema_dict.get(item['tema'], item['tema'] or 'Sin Tema')) for item in distribucion_tema_qs]
    tema_data = [item['total'] for item in distribucion_tema_qs]
    distribucion_tema_chart_data = {
        'labels': tema_labels,
        'datasets': [{
            'label': 'Encuestas por Tema',
            'data': tema_data,
            'backgroundColor': base_colors[len(subcategoria_labels):len(subcategoria_labels)+len(tema_labels)], # Usar colores diferentes
            'borderColor': 'rgba(255, 255, 255, 0.8)',
            'borderWidth': 1
        }]
    }
    distribucion_tema_json = json.dumps(distribucion_tema_chart_data)

    # --- Distribución por región ---
    distribucion_region_qs = Encuesta.objects.values('region__nombre').annotate(
        total=Count('id')
    ).order_by('-total')
    region_labels = [item['region__nombre'] or 'Sin Región' for item in distribucion_region_qs]
    region_data = [item['total'] for item in distribucion_region_qs]
    distribucion_region_chart_data = {
        'labels': region_labels,
        'datasets': [{
            'label': 'Encuestas por Región',
            'data': region_data,
            'backgroundColor': base_colors[:len(region_labels)], # Reusar colores si es necesario
            'borderColor': 'rgba(255, 255, 255, 0.8)',
            'borderWidth': 1
        }]
    }
    distribucion_region_json = json.dumps(distribucion_region_chart_data)

    # --- Tendencia de respuestas últimos 7 días ---
    tendencia_respuestas_qs = RespuestaEncuesta.objects.filter(
        fecha_respuesta__gte=one_week_ago # Usar variable
    ).annotate(
        fecha=TruncDate('fecha_respuesta')
    ).values('fecha').annotate(
        total=Count('id')
    ).order_by('fecha')
    # (Estos datos se usan directamente en la plantilla o se podrían formatear para un gráfico)

    # --- Top municipios con más respuestas ---
    top_municipios_qs = RespuestaEncuesta.objects.values('municipio__nombre').annotate(
        total=Count('id')
    ).order_by('-total')[:5] # Mantener top 5

    # ===== TIPOS DE PREGUNTAS =====
    tipos_preguntas = []
    tipos_preguntas_data_map = [
        ('Texto', PreguntaTexto), ('Texto Múltiple', PreguntaTextoMultiple),
        ('Opción Múltiple', PreguntaOpcionMultiple), ('Casillas', PreguntaCasillasVerificacion),
        ('Menú Desplegable', PreguntaMenuDesplegable), ('Estrellas', PreguntaEstrellas),
        ('Escala', PreguntaEscala), ('Matriz', PreguntaMatriz), ('Fecha', PreguntaFecha)
    ]
    tipos_labels = []
    tipos_data = []
    for tipo_nombre, modelo in tipos_preguntas_data_map:
        count = modelo.objects.count()
        if count > 0:
            tipos_preguntas.append({'tipo': tipo_nombre, 'total': count})
            tipos_labels.append(tipo_nombre)
            tipos_data.append(count)

    tipos_preguntas_chart_data = {
        'labels': tipos_labels,
        'datasets': [{
            'data': tipos_data,
            'backgroundColor': base_colors[:len(tipos_labels)], # Ajustar colores
            'hoverOffset': 10
        }]
    }
    tipos_preguntas_json = json.dumps(tipos_preguntas_chart_data)

    # ===== ESTADÍSTICAS PQRSFD =====
    # Conteo por estado (existente)
    conteo_estados_pqrsfd = {
        'P': PQRSFD.objects.filter(estado='P').count(),
        'E': PQRSFD.objects.filter(estado='E').count(),
        'R': PQRSFD.objects.filter(estado='R').count(),
        'C': PQRSFD.objects.filter(estado='C').count(),
        'total': PQRSFD.objects.count(),
        'vencidos': sum(1 for p in PQRSFD.objects.filter(estado__in=['P', 'E']) if p.esta_vencido())
    }

    # Distribución por Tipo
    distribucion_tipo_pqrsfd_qs = PQRSFD.objects.values('tipo').annotate(
        total=Count('id')
    ).order_by('-total')
    tipo_pqrsfd_dict = dict(PQRSFD.TIPO_CHOICES)
    tipo_pqrsfd_labels = [str(tipo_pqrsfd_dict.get(item['tipo'], item['tipo'] or 'Sin Tipo')) for item in distribucion_tipo_pqrsfd_qs]
    tipo_pqrsfd_data = [item['total'] for item in distribucion_tipo_pqrsfd_qs]
    distribucion_tipo_pqrsfd_chart_data = {
        'labels': tipo_pqrsfd_labels,
        'datasets': [{
            'label': 'PQRSFD por Tipo',
            'data': tipo_pqrsfd_data,
            'backgroundColor': base_colors[:len(tipo_pqrsfd_labels)], # Reusar colores si es necesario
            'borderColor': 'rgba(255, 255, 255, 0.8)',
            'borderWidth': 1
        }]
    }
    distribucion_tipo_pqrsfd_json = json.dumps(distribucion_tipo_pqrsfd_chart_data)

    # PQRSFD Recientes
    pqrsfd_creados_7d = PQRSFD.objects.filter(fecha_creacion__gte=one_week_ago).count()
    pqrsfd_creados_30d = PQRSFD.objects.filter(fecha_creacion__gte=thirty_days_ago).count()
    # Usar fecha_actualizacion como proxy para resueltos/cerrados recientes
    pqrsfd_resueltos_cerrados_7d = PQRSFD.objects.filter(estado__in=['R', 'C'], fecha_actualizacion__gte=one_week_ago).count()
    pqrsfd_resueltos_cerrados_30d = PQRSFD.objects.filter(estado__in=['R', 'C'], fecha_actualizacion__gte=thirty_days_ago).count()




    # ===== DATOS ADICIONALES =====
    ultimas_respuestas = RespuestaEncuesta.objects.select_related(
        'encuesta', 'usuario'
    ).order_by('-fecha_respuesta')[:10] # Mantener ultimas 10

    # ===== CONTEXTO PARA LA PLANTILLA =====
    context = {
        # --- Estadísticas generales Encuestas ---
        'total_encuestas': total_encuestas,
        'total_encuesta_respondidas': total_encuesta_respondidas, # Total histórico respondidas
        'total_encuesta_respondidas_activas': total_encuestas_respondidas_activas_count, # Respuestas a encuestas públicas activas
        'total_respuestas': total_respuestas, # Total histórico de objetos RespuestaEncuesta
        'avg_respuestas': round(avg_respuestas, 1),
        'encuestas_activas': encuestas_activas, # Total activas (públicas + privadas)
        'encuestas_publicas': encuestas_publicas_count, # Total públicas y activas
        'conteo_publicas_privadas': conteo_publicas_privadas, # Total públicas vs privadas (histórico)
        'encuestas_creadas_7d': encuestas_creadas_7d,
        'encuestas_creadas_30d': encuestas_creadas_30d,
        'tasa_finalizacion': round(tasa_finalizacion, 1), # Basada en total histórico
        'grupos_interes': grupos_interes,
        'regiones': regiones, # Añadir regiones al contexto
        'categorias': categorias, # Añadir categorías al contexto

        # --- Alertas y notificaciones ---
        'encuestas_proximo_fin': encuestas_proximo_fin,
        'encuestas_sin_respuestas': encuestas_sin_respuestas_count, # Activas sin respuestas

        # --- Datos para tablas y listas (QuerySets/Listas) ---
        'distribucion_region': distribucion_region_qs, # Para posible tabla
        'tendencia_respuestas': tendencia_respuestas_qs, # Para posible tabla
        'top_municipios': top_municipios_qs,
        'distribucion_categoria': distribucion_categoria_qs, # Para posible tabla
        'distribucion_subcategoria': distribucion_subcategoria_qs, # Para posible tabla
        'distribucion_tema': distribucion_tema_qs, # Para posible tabla
        'tipos_preguntas': tipos_preguntas, # Para posible tabla
        'ultimas_respuestas': ultimas_respuestas,
        'encuestas_publicas_activas': encuestas_publicas_activas, # Lista de encuestas públicas activas

        # --- Estadísticas PQRSFD ---
        'conteo_estados_pqrsfd': conteo_estados_pqrsfd, # Renombrado para claridad
        'distribucion_tipo_pqrsfd': distribucion_tipo_pqrsfd_qs, # Para posible tabla
        'pqrsfd_creados_7d': pqrsfd_creados_7d,
        'pqrsfd_creados_30d': pqrsfd_creados_30d,
        'pqrsfd_resueltos_cerrados_7d': pqrsfd_resueltos_cerrados_7d,
        'pqrsfd_resueltos_cerrados_30d': pqrsfd_resueltos_cerrados_30d,

        # --- JSON para Gráficos ---
        'tipos_preguntas_json': tipos_preguntas_json,
        'distribucion_categoria_json': distribucion_categoria_json,
        'distribucion_subcategoria_json': distribucion_subcategoria_json, # Nuevo
        'distribucion_tema_json': distribucion_tema_json, # Nuevo
        'distribucion_region_json': distribucion_region_json,
        'distribucion_tipo_pqrsfd_json': distribucion_tipo_pqrsfd_json, # Nuevo
    }

    return render(request, 'index.html', context)

#views del programa
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, DetailView
from django.contrib.auth.models import User
from .models import *
from .forms import *

# Vista para la página de selección de método de creación
@login_required
def seleccionar_metodo_creacion(request):
    # Obtener las encuestas del usuario actual
    encuestas = Encuesta.objects.filter(creador=request.user).order_by('-fecha_creacion')
    return render(request, 'Encuesta/seleccionar_metodo.html', {
        'encuestas': encuestas
    })

# Vista para crear encuesta desde cero
@login_required
def crear_desde_cero(request):
    # Inicializar el formulario fuera del bloque if/else
    form = EncuestaForm()
    regiones = Region.objects.all()
    categorias = Categoria.objects.all()
    grupos_interes = GrupoInteres.objects.all()

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
        grupo_interes_id = request.POST.get('grupo_interes')
        
        region = None
        categoria = None
        grupo_interes = None
        try:
            if region_id and region_id.strip():
                region_id = int(region_id)
                region = Region.objects.get(id=region_id)
            else:
                print("No se proporcionó region_id o estaba vacío")

            if categoria_id and categoria_id.strip():
                categoria_id = int(categoria_id)
                categoria = Categoria.objects.get(id=categoria_id)
                
            if grupo_interes_id and grupo_interes_id.strip():
                grupo_interes_id = int(grupo_interes_id)
                grupo_interes = GrupoInteres.objects.get(id=grupo_interes_id)
            
        except (ValueError, Region.DoesNotExist, Categoria.DoesNotExist, GrupoInteres.DoesNotExist) as e:
            messages.error(request, f"Error al procesar la región, categoría o grupo de interés seleccionado: {e}")
            return render(request, 'Encuesta/crear_desde_cero.html', {
                'form': form,
                'regiones': regiones,
                'categorias': categorias,
                'grupos_interes': grupos_interes
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
                grupo_interes=grupo_interes,
                municipio=None,
                tema=tema
            )
            
        except Exception as e:
            messages.error(request, f"Error al crear la encuesta: {e}")
            return render(request, 'Encuesta/crear_desde_cero.html', {
                'form': form,
                'regiones': regiones,
                'categorias': categorias,
                'grupos_interes': grupos_interes
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
            permitir_archivos = request.POST.get(f'questions[{pregunta_id}][permitir_archivos]', '') == 'on'
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
                    permitir_archivos=permitir_archivos,
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
                    permitir_archivos=permitir_archivos,
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
                    permitir_archivos=permitir_archivos,
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
                    permitir_archivos=permitir_archivos,
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
                    permitir_archivos=permitir_archivos,
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
                    permitir_archivos=permitir_archivos,
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
                    permitir_archivos=permitir_archivos,
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
                    permitir_archivos=False,
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
                    permitir_archivos=permitir_archivos,
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
                    permitir_archivos=permitir_archivos,
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
                    permitir_archivos=permitir_archivos,
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
        # Comprobar si se solicitó incluir caracterización
        incluir_caracterizacion = request.POST.get('incluir_caracterizacion') == 'true'
        if incluir_caracterizacion:
            requeridas = request.POST.get('preguntas_obligatorias', 'false') == 'true'
            
            # Este bloque de código es similar a la función agregar_caracterizacion
            # Definir orden inicial
            ultimo_orden = 0
            
            # Obtener todas las preguntas ya es una lista ordenada
            preguntas = encuesta.obtener_preguntas()
            if preguntas:
                ultimo_orden = max(p.orden for p in preguntas)
            
            # Crear las preguntas de caracterización
            preguntas = [
            {
                'tipo': 'TEXT',
                'texto': 'Nombre del Entrevistador',
                'orden': ultimo_orden + 1,
                'seccion': 'Caracterización',
                'requerida': requeridas
            },
            {
                'tipo': 'TEXT',
                'texto': '¿Cuál es su nombre completo?',
                'orden': ultimo_orden + 2,
                'seccion': 'Caracterización',
                'requerida': requeridas
            },
            {
                'tipo': 'TEXT',
                'texto': 'Identificación',
                'orden': ultimo_orden + 3,
                'seccion': 'Caracterización',
                'requerida': requeridas
            },
            {
                'tipo': 'TEXT',
                'texto': 'Correo electrónico',
                'orden': ultimo_orden + 4,
                'seccion': 'Caracterización',
                'requerida': False,
                'placeholder': 'ejemplo@correo.com'
            },
            {
                'tipo': 'TEXT',
                'texto': 'Número de teléfono o celular',
                'orden': ultimo_orden + 5,
                'seccion': 'Caracterización',
                'requerida': False,
                'placeholder': 'Ej: 3001234567'
            },
            {
                'tipo': 'RADIO',
                'texto': '¿Cuál es su sexo?',
                'orden': ultimo_orden + 6,
                'seccion': 'Caracterización',
                'requerida': requeridas,
                'opciones': [
                    {'texto': 'Masculino', 'valor': 'a', 'orden': 1},
                    {'texto': 'Femenino', 'valor': 'b', 'orden': 2},
                    {'texto': 'Otro', 'valor': 'c', 'orden': 3},
                    {'texto': 'Prefiero no responder', 'valor': 'd', 'orden': 4}
                ]
            },
            {
                'tipo': 'RADIO',
                'texto': '¿Cuál es su rango de edad?',
                'orden': ultimo_orden + 7,
                'seccion': 'Caracterización',
                'requerida': requeridas,
                'opciones': [
                    {'texto': 'Menos de 18 años', 'valor': 'a', 'orden': 1},
                    {'texto': '18 a 25 años', 'valor': 'b', 'orden': 2},
                    {'texto': '26 a 35 años', 'valor': 'c', 'orden': 3},
                    {'texto': '36 a 45 años', 'valor': 'd', 'orden': 4},
                    {'texto': '46 a 60 años', 'valor': 'e', 'orden': 5},
                    {'texto': 'Más de 60 años', 'valor': 'f', 'orden': 6}
                ]
            },
            {
                'tipo': 'CHECK',
                'texto': '¿A cuál(es) de los siguientes grupos diferenciales pertenece?',
                'orden': ultimo_orden + 8,
                'seccion': 'Caracterización',
                'requerida': requeridas,
                'opciones': [
                    {'texto': 'Comunidad Indígena', 'valor': 'a', 'orden': 1},
                    {'texto': 'Comunidad Afrodescendiente', 'valor': 'b', 'orden': 2},
                    {'texto': 'Comunidad Campesina', 'valor': 'c', 'orden': 3},
                    {'texto': 'Persona con Discapacidad', 'valor': 'd', 'orden': 4},
                    {'texto': 'LGBTIQ+', 'valor': 'e', 'orden': 5},
                    {'texto': 'Victima del conflicto armado', 'valor': 'f', 'orden': 6},
                    {'texto': 'Otro', 'valor': 'g', 'orden': 7},
                    {'texto': 'Ninguno', 'valor': 'h', 'orden': 8}
                ]
            }
        ]
        
            # Crear cada pregunta
            for pregunta_data in preguntas:
                if pregunta_data['tipo'] == 'TEXT':
                    pregunta = PreguntaTexto.objects.create(
                        encuesta=encuesta,
                        texto=pregunta_data['texto'],
                        tipo=pregunta_data['tipo'],
                        requerida=pregunta_data['requerida'],
                        orden=pregunta_data['orden'],
                        seccion=pregunta_data['seccion'],
                        ayuda=pregunta_data.get('ayuda', ''),
                        placeholder=pregunta_data.get('placeholder', '')
                    )
                elif pregunta_data['tipo'] == 'RADIO':
                    pregunta = PreguntaOpcionMultiple.objects.create(
                        encuesta=encuesta,
                        texto=pregunta_data['texto'],
                        tipo=pregunta_data['tipo'],
                        requerida=pregunta_data['requerida'],
                        orden=pregunta_data['orden'],
                        seccion=pregunta_data['seccion']
                    )
                    # Agregar opciones
                    for opcion_data in pregunta_data['opciones']:
                        OpcionMultiple.objects.create(
                            pregunta=pregunta,
                            texto=opcion_data['texto'],
                            valor=opcion_data['valor'],
                            orden=opcion_data['orden']
                        )
                elif pregunta_data['tipo'] == 'CHECK':
                    pregunta = PreguntaCasillasVerificacion.objects.create(
                        encuesta=encuesta,
                        texto=pregunta_data['texto'],
                        tipo=pregunta_data['tipo'],
                        requerida=pregunta_data['requerida'],
                        orden=pregunta_data['orden'],
                        seccion=pregunta_data['seccion']
                    )
                    # Agregar opciones
                    for opcion_data in pregunta_data['opciones']:
                        OpcionCasillaVerificacion.objects.create(
                            pregunta=pregunta,
                            texto=opcion_data['texto'],
                            valor=opcion_data['valor'],
                            orden=opcion_data['orden']
                        )
        
        return redirect('lista_encuestas')
    
    return render(request, 'Encuesta/crear_desde_cero.html', {
        'form': form,
        'regiones': regiones,
        'categorias': categorias,
        'grupos_interes': grupos_interes
    })

# Vista para crear encuesta con IA (versión simplificada)
@login_required
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
@login_required
def duplicar_encuesta(request, encuesta_id):
    encuesta_original = get_object_or_404(Encuesta, id=encuesta_id)
    
    if request.method == 'POST':
        try:
            # Obtener el nuevo título y generar un slug único
            nuevo_titulo = request.POST.get('titulo', f"{encuesta_original.titulo} (Copia)")
            
            # Verificar que el título no esté repetido
            if Encuesta.objects.filter(titulo=nuevo_titulo).exists():
                messages.error(request, 'Ya existe una encuesta con este título. Por favor, elige otro.')
                return redirect('duplicar_encuesta', encuesta_id=encuesta_original.id)
            
            # Generar un slug base desde el título
            from django.utils.text import slugify
            slug_base = slugify(nuevo_titulo)
            
            # Asegurarse de que el slug sea único
            slug = slug_base
            counter = 1
            while Encuesta.objects.filter(slug=slug).exists():
                slug = f"{slug_base}-{counter}"
                counter += 1
            
            # Obtener fechas de inicio y fin desde el formulario
            fecha_inicio = request.POST.get('fecha_inicio')
            fecha_fin = request.POST.get('fecha_fin')
            
            # Crear nueva encuesta con todos los campos necesarios
            nueva_encuesta = Encuesta.objects.create(
                titulo=nuevo_titulo,
                slug=slug,  # Usar el slug único generado
                creador=request.user,
                region_id=request.POST.get('region'),
                categoria_id=request.POST.get('categoria'),
                activa=request.POST.get('activa') == 'on',
                es_publica=request.POST.get('es_publica') == 'on',
                fecha_inicio=fecha_inicio,  # Usar la fecha proporcionada
                fecha_fin=fecha_fin,  # Usar la fecha proporcionada
                tema=encuesta_original.tema,
                imagen_encabezado=encuesta_original.imagen_encabezado,
                logotipo=encuesta_original.logotipo,
                mostrar_logo=encuesta_original.mostrar_logo,
                estilo_fuente=encuesta_original.estilo_fuente,
                tamano_fuente=encuesta_original.tamano_fuente,
                estilo_bordes=encuesta_original.estilo_bordes,
                tipo_fondo=encuesta_original.tipo_fondo,
                color_fondo=encuesta_original.color_fondo,
                color_gradiente_1=encuesta_original.color_gradiente_1,
                color_gradiente_2=encuesta_original.color_gradiente_2,
                imagen_fondo=encuesta_original.imagen_fondo,
                patron_fondo=encuesta_original.patron_fondo
            )
            
            # Duplicar preguntas de texto
            for pregunta in encuesta_original.preguntatexto_relacionadas.all():
                PreguntaTexto.objects.create(
                    encuesta=nueva_encuesta,
                    texto=pregunta.texto,
                    orden=pregunta.orden,
                    requerida=pregunta.requerida
                )
            
            # Duplicar preguntas de texto múltiple
            for pregunta in encuesta_original.preguntatextomultiple_relacionadas.all():
                PreguntaTextoMultiple.objects.create(
                    encuesta=nueva_encuesta,
                    texto=pregunta.texto,
                    orden=pregunta.orden,
                    requerida=pregunta.requerida
                )
            
            # Duplicar preguntas de opción múltiple
            for pregunta in encuesta_original.preguntaopcionmultiple_relacionadas.all():
                nueva_pregunta = PreguntaOpcionMultiple.objects.create(
                    encuesta=nueva_encuesta,
                    texto=pregunta.texto,
                    orden=pregunta.orden,
                    requerida=pregunta.requerida,
                    opcion_otro=pregunta.opcion_otro,
                    texto_otro=pregunta.texto_otro
                )
                
                # Duplicar opciones
                for opcion in pregunta.opciones.all():
                    OpcionMultiple.objects.create(
                        pregunta=nueva_pregunta,
                        texto=opcion.texto,
                        valor=opcion.valor,
                        orden=opcion.orden
                    )
            
            # Duplicar preguntas de casillas de verificación
            for pregunta in encuesta_original.preguntacasillasverificacion_relacionadas.all():
                nueva_pregunta = PreguntaCasillasVerificacion.objects.create(
                    encuesta=nueva_encuesta,
                    texto=pregunta.texto,
                    orden=pregunta.orden,
                    requerida=pregunta.requerida,
                    opcion_otro=pregunta.opcion_otro,
                    texto_otro=pregunta.texto_otro,
                    min_selecciones=pregunta.min_selecciones,
                    max_selecciones=pregunta.max_selecciones
                )
                
                # Duplicar opciones
                for opcion in pregunta.opciones.all():
                    OpcionCasillaVerificacion.objects.create(
                        pregunta=nueva_pregunta,
                        texto=opcion.texto,
                        valor=opcion.valor,
                        orden=opcion.orden
                    )
            
            # Duplicar preguntas de menú desplegable
            for pregunta in encuesta_original.preguntamenudesplegable_relacionadas.all():
                nueva_pregunta = PreguntaMenuDesplegable.objects.create(
                    encuesta=nueva_encuesta,
                    texto=pregunta.texto,
                    orden=pregunta.orden,
                    requerida=pregunta.requerida
                )
                
                # Duplicar opciones
                for opcion in pregunta.opciones.all():
                    OpcionMenuDesplegable.objects.create(
                        pregunta=nueva_pregunta,
                        texto=opcion.texto,
                        valor=opcion.valor,
                        orden=opcion.orden
                    )
            
            # Duplicar preguntas de escala
            for pregunta in encuesta_original.preguntaescala_relacionadas.all():
                PreguntaEscala.objects.create(
                    encuesta=nueva_encuesta,
                    texto=pregunta.texto,
                    orden=pregunta.orden,
                    requerida=pregunta.requerida,
                    valor_minimo=pregunta.valor_minimo,
                    valor_maximo=pregunta.valor_maximo,
                    etiqueta_minima=pregunta.etiqueta_minima,
                    etiqueta_maxima=pregunta.etiqueta_maxima
                )
            
            # Duplicar preguntas de matriz
            for pregunta in encuesta_original.preguntamatriz_relacionadas.all():
                nueva_pregunta = PreguntaMatriz.objects.create(
                    encuesta=nueva_encuesta,
                    texto=pregunta.texto,
                    orden=pregunta.orden,
                    requerida=pregunta.requerida
                )
                
                # Duplicar filas
                for fila in pregunta.filas.all():
                    FilaMatriz.objects.create(
                        pregunta=nueva_pregunta,
                        texto=fila.texto,
                        orden=fila.orden
                    )
                
                # Duplicar columnas
                for columna in pregunta.columnas.all():
                    ColumnaMatriz.objects.create(
                        pregunta=nueva_pregunta,
                        texto=columna.texto,
                        orden=columna.orden
                    )
            
            messages.success(request, 'Encuesta duplicada exitosamente!')
            return redirect('editar_encuesta', encuesta_id=nueva_encuesta.id)
            
        except Exception as e:
            messages.error(request, f'Error al duplicar la encuesta: {str(e)}')
            return redirect('editar_encuesta', encuesta_id=encuesta_original.id)
    
    # Si es GET, mostrar el formulario de duplicación
    regiones = Region.objects.all()
    categorias = Categoria.objects.all()
    
    return render(request, 'Encuesta/duplicar_encuesta.html', {
        'encuesta_original': encuesta_original,
        'regiones': regiones,
        'categorias': categorias,
        'now': timezone.now()  # Pasar la fecha actual para el campo fecha_inicio
    })

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
    
    # Obtener regiones, categorías y grupos de interés
    regiones = Region.objects.all()
    categorias = Categoria.objects.all()
    grupos_interes = GrupoInteres.objects.all()
    
    # Obtener subcategorías si hay una categoría seleccionada
    subcategorias = []
    if encuesta.categoria:
        subcategorias = Subcategoria.objects.filter(categoria=encuesta.categoria)
    
    return render(request, 'Encuesta/editar_encuesta.html', {
        'encuesta': encuesta,
        'form': form,
        'preguntas': preguntas,
        'regiones': regiones,
        'categorias': categorias,
        'subcategorias': subcategorias,
        'grupos_interes': grupos_interes
    })

# Vista para listar encuestas del usuario

class ListaEncuestasView(LoginRequiredMixin, ListView):
    model = Encuesta
    template_name = 'Encuesta/lista_encuestas.html'
    context_object_name = 'encuestas'
    paginate_by = 10

    def get_queryset(self):
        # Obtener todas las encuestas del usuario actual
        queryset = Encuesta.objects.filter(creador=self.request.user)
        
        # Aplicar búsqueda por título
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(titulo__icontains=search)
        
        # Obtener los filtros
        categoria = self.request.GET.get('categoria')
        region = self.request.GET.get('region')
        estado = self.request.GET.get('estado')
        grupo_interes = self.request.GET.get('grupo_interes')
        
        # Aplicar filtros si están presentes
        if categoria:
            queryset = queryset.filter(categoria_id=categoria)
        if region:
            queryset = queryset.filter(region_id=region)
        if estado:
            if estado == 'activa':
                queryset = queryset.filter(activa=True)
            elif estado == 'inactiva':
                queryset = queryset.filter(activa=False)
        if grupo_interes:
            queryset = queryset.filter(grupo_interes_id=grupo_interes)
        
        # Ordenar resultados
        orden = self.request.GET.get('orden', 'fecha_desc')
        if orden == 'fecha_asc':
            queryset = queryset.order_by('fecha_creacion')
        elif orden == 'fecha_desc':
            queryset = queryset.order_by('-fecha_creacion')
        elif orden == 'titulo_asc':
            queryset = queryset.order_by('titulo')
        elif orden == 'titulo_desc':
            queryset = queryset.order_by('-titulo')
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar categorías y regiones al contexto
        context['categorias'] = Categoria.objects.all()
        context['regiones'] = Region.objects.all()
        context['grupos_interes'] = GrupoInteres.objects.all()
        return context
    
class TodasEncuestasView(ListView):
    model = Encuesta
    template_name = 'Encuesta/todas_encuestas.html'
    context_object_name = 'encuestas'
    paginate_by = 10

    def get_queryset(self):
        # Obtener todas las encuestas públicas
        queryset = Encuesta.objects.filter(es_publica=True)
        
        # Aplicar búsqueda por título
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(titulo__icontains=search)
        
        # Obtener los filtros
        categoria = self.request.GET.get('categoria')
        region = self.request.GET.get('region')
        estado = self.request.GET.get('estado')
        creador = self.request.GET.get('creador')
        fecha_desde = self.request.GET.get('fecha_desde')
        fecha_hasta = self.request.GET.get('fecha_hasta')
        temas = self.request.GET.get('temas')
        grupo_interes = self.request.GET.get('grupo_interes')
        
        # Aplicar filtros si están presentes
        if categoria:
            queryset = queryset.filter(categoria_id=categoria)
        if region:
            queryset = queryset.filter(region_id=region)
        if estado:
            if estado == 'activa':
                queryset = queryset.filter(activa=True)
            elif estado == 'inactiva':
                queryset = queryset.filter(activa=False)
        if creador:
            queryset = queryset.filter(creador_id=creador)
        if fecha_desde:
            queryset = queryset.filter(fecha_creacion__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha_creacion__lte=fecha_hasta)
        if temas:
            queryset = queryset.filter(tema_id__in=temas)
        if grupo_interes:
            queryset = queryset.filter(grupo_interes_id=grupo_interes)
        # Ordenar resultados
        orden = self.request.GET.get('orden', 'fecha_desc')
        if orden == 'fecha_asc':
            queryset = queryset.order_by('fecha_creacion')
        elif orden == 'fecha_desc':
            queryset = queryset.order_by('-fecha_creacion')
        elif orden == 'titulo_asc':
            queryset = queryset.order_by('titulo')
        elif orden == 'titulo_desc':
            queryset = queryset.order_by('-titulo')
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar categorías, regiones y usuarios al contexto
        context['categorias'] = Categoria.objects.all()
        context['regiones'] = Region.objects.all()
        context['usuarios'] = User.objects.all()
        context['grupos_interes'] = GrupoInteres.objects.all()

        return context

class ResultadosEncuestaView(DetailView):
    model = Encuesta
    template_name = 'Encuesta/resultados_encuesta.html'
    context_object_name = 'encuesta'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        encuesta = self.object
        total_respuestas = encuesta.respuestas.count()

        # Obtener todas las respuestas completas para esta encuesta
        respuestas_completas = RespuestaEncuesta.objects.filter(encuesta=encuesta)
        context['respuestas_completas'] = respuestas_completas

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
                'total_respuestas': total_respuestas,
                'encuesta': encuesta
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
                datos_pregunta['respuestas'] = list(respuestas)

            elif tipo == 'preguntatextomultiple':
                respuestas = RespuestaTextoMultiple.objects.filter(pregunta=pregunta)
                datos_pregunta['datos'] = [r.valor for r in respuestas]
                datos_pregunta['respuestas'] = list(respuestas)

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


def guardar_respuesta(request, encuesta_id):
    encuesta = get_object_or_404(Encuesta, id=encuesta_id)

    if request.method == 'POST':
        municipio_id = request.POST.get('municipio')
        municipio = Municipio.objects.filter(id=municipio_id).first() if municipio_id else None

        # Si el usuario está autenticado, lo usamos; si no, establecemos usuario como None
        usuario = request.user if request.user.is_authenticated else None

        respuesta = RespuestaEncuesta.objects.create(
            encuesta=encuesta,
            usuario=usuario,
            municipio=municipio,
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
        procesar_archivos_adjuntos(request, respuesta)

        # Verificar si se marcó la opción de generar certificado
        generar_certificado_opcion = request.POST.get('generar_certificado')
        
        if generar_certificado_opcion:
            # Intentamos obtener el nombre de la caracterización
            nombre_completo = None
            documento = None
            correo = None
            telefono = None
            municipio = None
            
            # Buscar en las respuestas de texto el nombre de la persona
            nombre_preguntas = ['nombre completo', '¿cuál es su nombre completo?', 'nombre']
            for pregunta in PreguntaTexto.objects.filter(encuesta=encuesta):
                if any(texto.lower() in pregunta.texto.lower() for texto in nombre_preguntas):
                    respuesta_nombre = RespuestaTexto.objects.filter(
                        respuesta_encuesta=respuesta, 
                        pregunta=pregunta
                    ).first()
                    if respuesta_nombre:
                        nombre_completo = respuesta_nombre.valor
                        break
            
            # Buscar el número de identificación
            doc_preguntas = ['identificación', 'documento', 'cédula', 'número de documento']
            for pregunta in PreguntaTexto.objects.filter(encuesta=encuesta):
                if any(texto.lower() in pregunta.texto.lower() for texto in doc_preguntas):
                    respuesta_doc = RespuestaTexto.objects.filter(
                        respuesta_encuesta=respuesta, 
                        pregunta=pregunta
                    ).first()
                    if respuesta_doc:
                        documento = respuesta_doc.valor
                        break
            
            # Buscar el correo electrónico
            correo_preguntas = ['correo electrónico', 'email', 'e-mail', 'correo']
            for pregunta in PreguntaTexto.objects.filter(encuesta=encuesta):
                if any(texto.lower() in pregunta.texto.lower() for texto in correo_preguntas):
                    respuesta_correo = RespuestaTexto.objects.filter(
                        respuesta_encuesta=respuesta, 
                        pregunta=pregunta
                    ).first()
                    if respuesta_correo:
                        correo = respuesta_correo.valor
                        break
            
            # Buscar el teléfono celular
            telefono_preguntas = ['teléfono', 'celular', 'móvil', 'número de teléfono', 'número telefónico']
            for pregunta in PreguntaTexto.objects.filter(encuesta=encuesta):
                if any(texto.lower() in pregunta.texto.lower() for texto in telefono_preguntas):
                    respuesta_telefono = RespuestaTexto.objects.filter(
                        respuesta_encuesta=respuesta, 
                        pregunta=pregunta
                    ).first()
                    if respuesta_telefono:
                        telefono = respuesta_telefono.valor
                        break
            
            # Buscar el municipio
            municipio_preguntas = ['municipio', 'ciudad', 'municipio de residencia', 'municipio de residencia']
            for pregunta in PreguntaTexto.objects.filter(encuesta=encuesta):
                if any(texto.lower() in pregunta.texto.lower() for texto in municipio_preguntas):
                    respuesta_municipio = RespuestaTexto.objects.filter(
                        respuesta_encuesta=respuesta, 
                        pregunta=pregunta
                    ).first()
                    if respuesta_municipio:
                        municipio = respuesta_municipio.valor
                        break
            
            
                    

            # Si tenemos los datos, enviamos directamente al certificado
            if nombre_completo and documento:
                # Preparar datos para enviar a la plantilla
                fecha_actual = timezone.now().strftime('%d/%m/%Y')
                context = {
                    'encuesta': encuesta,
                    'nombre_completo': nombre_completo,
                    'numero_identificacion': documento,
                    'correo': correo,
                    'telefono': telefono,
                    'fecha_actual': fecha_actual,
                    'municipio': municipio,
                    'guardar_datos': True  # Indicar que se deben guardar los datos
                }
                return render(request, 'certificado_template.html', context)
            else:
                # Si no los encontramos, redirigimos a la página de certificado con los datos que tengamos
                # Crear el contexto para JavaScript con datos escapados correctamente
                import json
                from django.utils.safestring import mark_safe
                fecha_actual = timezone.now().strftime('%d/%m/%Y')
                datos_js = {
                    'encuesta_id': encuesta.id,
                    'nombre_completo': nombre_completo or '',
                    'numero_identificacion': documento or '',
                    'correo': correo or '',
                    'telefono': telefono or '',
                    'municipio': municipio or '',
                    'fecha_actual': fecha_actual or ''
                    

                }
                
                context = {
                    'encuesta': encuesta,
                    'datos_certificado_json': mark_safe(json.dumps(datos_js)),
                    'redirigir_certificado': True
                }
                
                # Renderizar una página intermedia que guardará los datos y redirigirá
                return render(request, 'redirect_certificado.html', context)
        
        # Redirigir a la página de encuesta completada
        # return redirect('encuesta_completada', slug=encuesta.slug)
        
        # En lugar de redirigir directamente a encuesta_completada, redirigimos a la página de la encuesta
        # con el parámetro submitted=true para mostrar el modal de certificado
        responder_url = reverse('responder_encuesta', kwargs={'slug': encuesta.slug})
        return redirect(f"{responder_url}?submitted=true")

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

def procesar_archivos_adjuntos(request, respuesta):
    """Procesa los archivos adjuntos para cada pregunta que los permita"""
    # Recopilar todos los tipos de preguntas que pueden tener archivos adjuntos
    todas_preguntas = []
    todas_preguntas.extend(PreguntaTexto.objects.filter(encuesta=respuesta.encuesta, permitir_archivos=True))
    todas_preguntas.extend(PreguntaTextoMultiple.objects.filter(encuesta=respuesta.encuesta, permitir_archivos=True))
    todas_preguntas.extend(PreguntaOpcionMultiple.objects.filter(encuesta=respuesta.encuesta, permitir_archivos=True))
    todas_preguntas.extend(PreguntaCasillasVerificacion.objects.filter(encuesta=respuesta.encuesta, permitir_archivos=True))
    todas_preguntas.extend(PreguntaMenuDesplegable.objects.filter(encuesta=respuesta.encuesta, permitir_archivos=True))
    todas_preguntas.extend(PreguntaEstrellas.objects.filter(encuesta=respuesta.encuesta, permitir_archivos=True))
    todas_preguntas.extend(PreguntaEscala.objects.filter(encuesta=respuesta.encuesta, permitir_archivos=True))
    todas_preguntas.extend(PreguntaMatriz.objects.filter(encuesta=respuesta.encuesta, permitir_archivos=True))
    todas_preguntas.extend(PreguntaFecha.objects.filter(encuesta=respuesta.encuesta, permitir_archivos=True))
    
    # Procesar cada pregunta
    for pregunta in todas_preguntas:
        # Identificar el tipo específico de respuesta para esta pregunta
        respuesta_especifica = None
        tipo_pregunta = pregunta.__class__.__name__
        
        if isinstance(pregunta, PreguntaTexto):
            respuesta_especifica = RespuestaTexto.objects.filter(respuesta_encuesta=respuesta, pregunta=pregunta).first()
        elif isinstance(pregunta, PreguntaTextoMultiple):
            respuesta_especifica = RespuestaTextoMultiple.objects.filter(respuesta_encuesta=respuesta, pregunta=pregunta).first()
        elif isinstance(pregunta, PreguntaOpcionMultiple):
            respuesta_especifica = RespuestaOpcionMultiple.objects.filter(respuesta_encuesta=respuesta, pregunta=pregunta).first()
        elif isinstance(pregunta, PreguntaCasillasVerificacion):
            respuesta_especifica = RespuestaCasillasVerificacion.objects.filter(respuesta_encuesta=respuesta, pregunta=pregunta).first()
        elif isinstance(pregunta, PreguntaMenuDesplegable):
            respuesta_especifica = RespuestaOpcionMenuDesplegable.objects.filter(respuesta_encuesta=respuesta, pregunta=pregunta).first()
        elif isinstance(pregunta, PreguntaEstrellas):
            respuesta_especifica = RespuestaEstrellas.objects.filter(respuesta_encuesta=respuesta, pregunta=pregunta).first()
        elif isinstance(pregunta, PreguntaEscala):
            respuesta_especifica = RespuestaEscala.objects.filter(respuesta_encuesta=respuesta, pregunta=pregunta).first()
        elif isinstance(pregunta, PreguntaMatriz):
            respuesta_especifica = RespuestaMatriz.objects.filter(respuesta_encuesta=respuesta, pregunta=pregunta).first()
        elif isinstance(pregunta, PreguntaFecha):
            respuesta_especifica = RespuestaFecha.objects.filter(respuesta_encuesta=respuesta, pregunta=pregunta).first()
            
        # Procesar archivos solo si hay una respuesta específica
        if respuesta_especifica:
            archivos = request.FILES.getlist(f'archivos_{pregunta.id}[]')
            for archivo in archivos:
                ArchivoRespuesta.objects.create(
                    respuesta=respuesta,
                    archivo=archivo,
                    nombre_original=archivo.name,
                    tipo_archivo=archivo.content_type,
                    pregunta_id=pregunta.id,
                    tipo_pregunta=tipo_pregunta
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
        latitud = request.POST.get("latitud")
        longitud = request.POST.get("longitud")
        
        if nombre and region_id:
            region = Region.objects.filter(id=region_id).first()
            if region:
                municipio, created = Municipio.objects.get_or_create(
                    nombre=nombre,
                    region=region,
                    defaults={
                        'latitud': latitud if latitud else None,
                        'longitud': longitud if longitud else None
                    }
                )
                if created:
                    messages.success(request, f"Municipio '{nombre}' creado en región '{region.nombre}'.")
                else:
                    messages.info(request, f"El municipio '{nombre}' ya existe en la región '{region.nombre}'.")
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
        
        try:
            # Iniciar transacción para garantizar la integridad
            with transaction.atomic():
                # Obtener todas las respuestas asociadas a la encuesta
                respuestas = RespuestaEncuesta.objects.filter(encuesta=encuesta)
                
                # Para cada respuesta, eliminar los archivos adjuntos primero
                for respuesta in respuestas:
                    # Eliminar archivos adjuntos físicos
                    archivos = ArchivoRespuesta.objects.filter(respuesta=respuesta)
                    for archivo in archivos:
                        if archivo.archivo and os.path.isfile(archivo.archivo.path):
                            os.remove(archivo.archivo.path)
                    
                    # Eliminar todos los tipos de respuestas específicas
                    RespuestaTexto.objects.filter(respuesta_encuesta=respuesta).delete()
                    RespuestaTextoMultiple.objects.filter(respuesta_encuesta=respuesta).delete()
                    RespuestaOpcionMultiple.objects.filter(respuesta_encuesta=respuesta).delete()
                    RespuestaCasillasVerificacion.objects.filter(respuesta_encuesta=respuesta).delete()
                    RespuestaOpcionMenuDesplegable.objects.filter(respuesta_encuesta=respuesta).delete()
                    RespuestaEstrellas.objects.filter(respuesta_encuesta=respuesta).delete()
                    RespuestaEscala.objects.filter(respuesta_encuesta=respuesta).delete()
                    RespuestaMatriz.objects.filter(respuesta_encuesta=respuesta).delete()
                    RespuestaFecha.objects.filter(respuesta_encuesta=respuesta).delete()
                
                # Eliminar todas las respuestas
                respuestas.delete()
                
                # Eliminar la encuesta (esto eliminará en cascada las preguntas gracias a on_delete=CASCADE)
                encuesta.delete()
                
            messages.success(request, f'La encuesta "{titulo}" y todas sus respuestas han sido eliminadas exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al eliminar la encuesta: {str(e)}')
        
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
        return redirect('editar_encuesta', encuesta_id=request.POST.get('encuesta_id', 1))
    
    # Verificar que el usuario sea el dueño de la encuesta
    if pregunta.encuesta.creador != request.user:
        messages.error(request, "No tienes permiso para editar esta pregunta.")
        return redirect('lista_encuestas')
    
    # Actualizar campos comunes a todos los tipos de preguntas
    texto = request.POST.get('texto', '').strip()
    orden = request.POST.get('orden')
    requerida = 'requerida' in request.POST
    permitir_archivos = 'permitir_archivos' in request.POST
    
    if texto and orden:
        pregunta.texto = texto
        pregunta.orden = int(orden)
        pregunta.requerida = requerida
        pregunta.permitir_archivos = permitir_archivos
    
    try:
        with transaction.atomic():
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
        encuesta = get_object_or_404(Encuesta, id=encuesta_id, creador=request.user)
        
        # Obtener datos del formulario
        texto = request.POST.get('texto').strip()
        tipo = request.POST.get('tipo')
        requerida = 'requerida' in request.POST
        permitir_archivos = 'permitir_archivos' in request.POST
        ayuda = request.POST.get('ayuda', '')
        seccion = request.POST.get('seccion', '')
        
        # Calcular el siguiente orden automáticamente
        # Obtener el máximo orden actual y sumar 1
        ultimo_orden = 0
        for modelo in [PreguntaTexto, PreguntaTextoMultiple, PreguntaOpcionMultiple, 
                      PreguntaCasillasVerificacion, PreguntaMenuDesplegable, 
                      PreguntaEstrellas, PreguntaEscala, PreguntaMatriz, PreguntaFecha]:
            max_orden = modelo.objects.filter(encuesta=encuesta).aggregate(Max('orden'))['orden__max'] or 0
            ultimo_orden = max(ultimo_orden, max_orden)
        
        orden = ultimo_orden + 1
        
        # Crear la pregunta según el tipo
        if tipo == 'TEXT':
            pregunta = PreguntaTexto.objects.create(
                encuesta=encuesta,
                texto=texto,
                tipo=tipo,
                orden=orden,
                requerida=requerida,
                permitir_archivos=permitir_archivos,
                ayuda=ayuda,
                seccion=seccion
            )
        elif tipo == 'MTEXT':
            pregunta = PreguntaTextoMultiple.objects.create(
                encuesta=encuesta,
                texto=texto,
                tipo=tipo,
                orden=orden,
                requerida=requerida,
                permitir_archivos=permitir_archivos,
                ayuda=ayuda,
                seccion=seccion
            )
        elif tipo in ['RADIO', 'CHECK', 'SELECT']:
            # Crear pregunta de opción múltiple
            if tipo == 'RADIO':
                pregunta = PreguntaOpcionMultiple.objects.create(
                    encuesta=encuesta,
                    texto=texto,
                    tipo=tipo,
                    orden=orden,
                    requerida=requerida,
                    permitir_archivos=permitir_archivos,
                    ayuda=ayuda,
                    seccion=seccion
                )
            elif tipo == 'CHECK':
                pregunta = PreguntaCasillasVerificacion.objects.create(
                    encuesta=encuesta,
                    texto=texto,
                    tipo=tipo,
                    orden=orden,
                    requerida=requerida,
                    permitir_archivos=permitir_archivos,
                    ayuda=ayuda,
                    seccion=seccion
                )
            else:  # SELECT
                pregunta = PreguntaMenuDesplegable.objects.create(
                    encuesta=encuesta,
                    texto=texto,
                    tipo=tipo,
                    orden=orden,
                    requerida=requerida,
                    permitir_archivos=permitir_archivos,
                    ayuda=ayuda,
                    seccion=seccion
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
                tipo=tipo,
                orden=orden,
                requerida=requerida,
                permitir_archivos=permitir_archivos,
                ayuda=ayuda,
                seccion=seccion,
                valor_minimo=escala_min,
                valor_maximo=escala_max,
                paso=escala_paso
            )
            
        elif tipo == 'MATRIX':
            # Crear pregunta de matriz
            pregunta = PreguntaMatriz.objects.create(
                encuesta=encuesta,
                texto=texto,
                tipo=tipo,
                orden=orden,
                requerida=requerida,
                ayuda=ayuda,
                seccion=seccion
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
                tipo=tipo,
                orden=orden,
                requerida=requerida,
                ayuda=ayuda,
                seccion=seccion
            )
            
        elif tipo == 'STARS':
            pregunta = PreguntaEstrellas.objects.create(
                encuesta=encuesta,
                texto=texto,
                tipo=tipo,
                orden=orden,
                requerida=requerida,
                ayuda=ayuda,
                seccion=seccion
            )
            
        # Reordenar las preguntas si es necesario
        preguntas = [p for p in encuesta.obtener_preguntas() if p.orden >= orden and p != pregunta]
        for p in preguntas:
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
def eliminar_region(request, region_id):
    try:
        region = Region.objects.get(id=region_id)
        nombre_region = region.nombre
        eliminar_municipios = request.GET.get('eliminar_municipios', 'false')
        
        # Verificar si hay municipios asociados
        municipios = Municipio.objects.filter(region=region)
        
        if municipios.exists() and eliminar_municipios != 'true':
            messages.error(request, f'No se puede eliminar la región {nombre_region} porque tiene municipios asociados. Elimine primero los municipios o use la opción para eliminar todo.')
            return redirect('regiones_y_municipios')
        
        # Si se solicita eliminar los municipios también
        if eliminar_municipios == 'true':
            # Eliminar todos los municipios de esta región
            municipios.delete()
            messages.success(request, f'Se han eliminado todos los municipios asociados a la región {nombre_region}.')
        
        region.delete()
        messages.success(request, f'La región {nombre_region} ha sido eliminada exitosamente.')
    except Region.DoesNotExist:
        messages.error(request, 'La región no existe.')
    except Exception as e:
        messages.error(request, f'Error al eliminar la región: {str(e)}')
    return redirect('regiones_y_municipios')

@login_required
def eliminar_municipio(request, municipio_id):
    try:
        municipio = Municipio.objects.get(id=municipio_id)
        nombre_municipio = municipio.nombre
        municipio.delete()
        messages.success(request, f'El municipio {nombre_municipio} ha sido eliminado exitosamente.')
    except Municipio.DoesNotExist:
        messages.error(request, 'El municipio no existe.')
    except Exception as e:
        messages.error(request, f'Error al eliminar el municipio: {str(e)}')
    return redirect('regiones_y_municipios')

@login_required
def estadisticas_municipios(request):
    """Vista para mostrar la página de estadísticas de municipios con datos precargados"""
    
    # Obtener todas las regiones y municipios para los selects
    regiones = Region.objects.all()
    todos_municipios_lista = list(Municipio.objects.values('id', 'nombre', 'region_id')) # Corregido: seleccionar el campo existente
    # Ajustar clave 'region' para JSON de municipios
    for municipio in todos_municipios_lista:
        municipio['region'] = municipio.pop('region_id')
    todos_municipios_json = json.dumps(todos_municipios_lista, cls=DjangoJSONEncoder)

    # --- Filtros --- 
    region_id_str = request.GET.get('region', 'todas')
    municipio_id_str = request.GET.get('municipio', 'todos')
    
    # Convertir IDs a int si no son 'todas' o 'todos'
    region_id = int(region_id_str) if region_id_str.isdigit() else None
    municipio_id = int(municipio_id_str) if municipio_id_str.isdigit() else None

    # --- Cálculo de Estadísticas --- 
    
    # 1. Estadísticas por Municipio (Filtradas)
    municipios_filtrados = Municipio.objects.select_related('region').all()
    if region_id:
        municipios_filtrados = municipios_filtrados.filter(region_id=region_id)
    if municipio_id:
        municipios_filtrados = municipios_filtrados.filter(id=municipio_id)

    datos_municipios_lista = []
    total_respuestas_general = 0
    total_encuestas_completadas_general = 0 # Ojo: Esta lógica puede necesitar revisión
    total_encuestas_aplicables_general = Encuesta.objects.count() # Simplificación inicial, ajustar si las encuestas dependen de región/municipio

    for municipio in municipios_filtrados:
        respuestas_municipio = RespuestaEncuesta.objects.filter(municipio=municipio)
        num_respuestas = respuestas_municipio.count()
        # Contar encuestas únicas respondidas en este municipio
        encuestas_respondidas_ids = respuestas_municipio.values_list('encuesta_id', flat=True).distinct()
        num_encuestas_respondidas = len(encuestas_respondidas_ids)
        
        # Calcular tasa - Necesita el número total de encuestas *aplicables* a este municipio
        # Esta parte es compleja y depende de tu lógica de negocio.
        # Asumiremos un total general por ahora, pero idealmente filtrarías Encuesta por región/municipio si aplica.
        total_encuestas_aplicables_municipio = total_encuestas_aplicables_general # Simplificación
        tasa_finalizacion = 0
        if total_encuestas_aplicables_municipio > 0:
            tasa_finalizacion = (num_encuestas_respondidas / total_encuestas_aplicables_municipio) * 100
        
        datos_municipios_lista.append({
            'id': municipio.id,
            'nombre': municipio.nombre,
            'region': municipio.region.nombre,
            'region_id': municipio.region.id,
            'totalEncuestas': total_encuestas_aplicables_municipio, # Revisar esta lógica
            'totalRespuestas': num_respuestas,
            'encuestasRespondidas': num_encuestas_respondidas,
            'tasaFinalizacion': round(tasa_finalizacion, 1),
            # 'latitud': municipio.latitud, # Descomentar si se necesita para mapas
            # 'longitud': municipio.longitud
        })
        
        total_respuestas_general += num_respuestas
        total_encuestas_completadas_general += num_encuestas_respondidas

    # Calcular tasa de finalización general (basada en filtros)
    tasa_finalizacion_general = 0
    if total_encuestas_aplicables_general > 0: # Usar el total aplicable calculado
        # Necesitamos el total *único* de encuestas respondidas *dentro del filtro*
        respuestas_filtradas_general = RespuestaEncuesta.objects.all()
        if region_id:
            respuestas_filtradas_general = respuestas_filtradas_general.filter(municipio__region_id=region_id)
        if municipio_id:
            respuestas_filtradas_general = respuestas_filtradas_general.filter(municipio_id=municipio_id)
        total_encuestas_completadas_general = respuestas_filtradas_general.values('encuesta_id').distinct().count()

        tasa_finalizacion_general = (total_encuestas_completadas_general / total_encuestas_aplicables_general) * 100

    # 2. Estadísticas por Región (Agregadas)
    datos_regiones_lista = []
    regiones_para_tabla = regiones # Usar todas las regiones o filtrar si es necesario
    if region_id:
        regiones_para_tabla = regiones_para_tabla.filter(id=region_id)
    
    for region in regiones_para_tabla:
        respuestas_region = RespuestaEncuesta.objects.filter(municipio__region=region)
        num_respuestas_region = respuestas_region.count()
        encuestas_respondidas_region_ids = respuestas_region.values_list('encuesta_id', flat=True).distinct()
        num_encuestas_respondidas_region = len(encuestas_respondidas_region_ids)
        
        # Total encuestas aplicables a la región (Simplificación)
        total_encuestas_aplicables_region = Encuesta.objects.filter(region=region).count() if Encuesta._meta.get_field('region') else total_encuestas_aplicables_general

        tasa_finalizacion_region = 0
        if total_encuestas_aplicables_region > 0:
            tasa_finalizacion_region = (num_encuestas_respondidas_region / total_encuestas_aplicables_region) * 100

        datos_regiones_lista.append({
            'id': region.id,
            'nombre': region.nombre,
            'totalEncuestas': total_encuestas_aplicables_region, # Revisar lógica
            'totalRespuestas': num_respuestas_region,
            'encuestasRespondidas': num_encuestas_respondidas_region,
            'tasaFinalizacion': round(tasa_finalizacion_region, 1)
        })

    # 3. Datos para Gráficos
    
    # Historial (últimos 6 meses, filtrado)
    fecha_inicio = timezone.now() - timedelta(days=180)
    respuestas_historial = RespuestaEncuesta.objects.filter(fecha_respuesta__gte=fecha_inicio)
    if region_id:
        respuestas_historial = respuestas_historial.filter(municipio__region_id=region_id)
    if municipio_id:
        respuestas_historial = respuestas_historial.filter(municipio_id=municipio_id)
        
    respuestas_por_mes = {}
    # Crear todos los meses en el rango para asegurar que aparezcan aunque no tengan datos
    current_date = fecha_inicio
    end_date = timezone.now()
    while current_date <= end_date:
        mes_key = current_date.strftime('%Y-%m')
        mes_label = current_date.strftime('%b %Y')
        respuestas_por_mes[mes_key] = {'label': mes_label, 'count': 0}
        # Avanzar al siguiente mes (aproximado)
        next_month = current_date.replace(day=28) + timedelta(days=4) # Ir al final del mes y sumar 4 días
        current_date = next_month - timedelta(days=next_month.day - 1) # Ir al primer día del siguiente mes

    for respuesta in respuestas_historial:
        mes_key = respuesta.fecha_respuesta.strftime('%Y-%m')
        if mes_key in respuestas_por_mes:
            respuestas_por_mes[mes_key]['count'] += 1
        # else: Manejar respuestas fuera del rango si es necesario
    
    respuestas_ordenadas = sorted(respuestas_por_mes.items())
    historial_meses = [datos['label'] for _, datos in respuestas_ordenadas]
    historial_conteos = [datos['count'] for _, datos in respuestas_ordenadas]

    # Distribución por Región (basado en respuestas filtradas)
    distribucion_regiones = {} # { 'Region A': 100, 'Region B': 50 }
    # Usar los datos ya calculados para la tabla de regiones
    for region_data in datos_regiones_lista:
        distribucion_regiones[region_data['nombre']] = region_data['totalRespuestas']
        
    # Formatear para Plotly Pie
    regiones_pie_datos = [{'name': nombre, 'value': valor} for nombre, valor in distribucion_regiones.items()]

    # Top 10 Municipios (basado en respuestas filtradas)
    municipios_ordenados = sorted(
        datos_municipios_lista,
        key=lambda x: x['totalRespuestas'],
        reverse=True
    )
    top_10_municipios = municipios_ordenados[:10]
    municipios_bar_nombres = [m['nombre'] for m in top_10_municipios]
    municipios_bar_valores = [m['totalRespuestas'] for m in top_10_municipios]

    # Agrupar datos para JSON de gráficos
    datos_graficos_dict = {
        "historial": {
            "meses": historial_meses,
            "conteos": historial_conteos
        },
        "regiones": {
            "datos": regiones_pie_datos # Ya tiene formato {name:..., value:...}
        },
        "municipios": {
            "nombres": municipios_bar_nombres,
            "valores": municipios_bar_valores
        }
    }

    # 4. Encuestas Disponibles (Filtradas y con conteo)
    encuestas_disponibles = []
    query_encuestas = Encuesta.objects.prefetch_related('respuestas').select_related('region', 'municipio').all()
    # Aplicar filtros si existen (considerar si el filtro debe aplicar aquí o solo a estadísticas)
    # if region_id:
    #     query_encuestas = query_encuestas.filter(region_id=region_id)
    # if municipio_id:
    #     query_encuestas = query_encuestas.filter(Q(municipio_id=municipio_id) | Q(municipio__isnull=True)) # O encuestas sin municipio específico?
    
    query_encuestas = query_encuestas.order_by('-fecha_creacion')[:50]
    
    for encuesta in query_encuestas:
        # El prefetch_related debería hacer este conteo eficiente
        total_respuestas_encuesta = encuesta.respuestas.count() 
        encuestas_disponibles.append({
            'id': encuesta.id,
            'titulo': encuesta.titulo,
            'descripcion': encuesta.descripcion,
            'fecha_creacion': encuesta.fecha_creacion.strftime('%d/%m/%Y'),
            'es_publica': encuesta.es_publica,
            'activa': getattr(encuesta, 'activa', True), # Asumiendo un campo 'activa' o por defecto True
            'is_proxima': getattr(encuesta, 'is_proxima', False), # Asumiendo campo
            'total_respuestas': total_respuestas_encuesta,
            'region': encuesta.region.nombre if encuesta.region else 'N/A',
            'municipio': encuesta.municipio.nombre if encuesta.municipio else 'N/A',
            'grupo_interes': encuesta.grupo_interes.id if encuesta.grupo_interes else None
        })

    # --- Contexto Final --- 
    context = {
        # Datos para selects y UI
        'regiones': regiones,
        'municipios': todos_municipios_json, # Para el select JS
        'grupos_interes': GrupoInteres.objects.all(), # Lista de grupos de interés para filtro de encuestas
        'encuestas': encuestas_disponibles, # Para la sección de encuestas
        'region_seleccionada': region_id_str,
        'municipio_seleccionado': municipio_id_str,

        # Datos para tarjetas de resumen
        'total_encuestas': total_encuestas_aplicables_general, # Revisar lógica
        'total_respuestas': total_respuestas_general,
        'total_encuestas_completadas': total_encuestas_completadas_general, # Revisar lógica
        'tasa_finalizacion': round(tasa_finalizacion_general, 1),

        # --- JSONs para JavaScript --- 
        'datos_graficos_json': json.dumps(datos_graficos_dict, cls=DjangoJSONEncoder),
        'datos_regiones_tabla_json': json.dumps(datos_regiones_lista, cls=DjangoJSONEncoder),
        'datos_municipios_json': json.dumps(datos_municipios_lista, cls=DjangoJSONEncoder),
    }
    
    return render(request, 'estadisticas/municipios.html', context)

def public_home(request):
    """
    Vista pública que sirve como página principal del sitio.
    Muestra encuestas públicas y permite crear PQRSFD.
    """
    # Obtener encuestas públicas activas
    encuestas_publicas = Encuesta.objects.filter(
        es_publica=True,
        activa=True,
        fecha_inicio__lte=timezone.now(),
        fecha_fin__gte=timezone.now()
    ).select_related('categoria').order_by('-fecha_creacion')

    # Obtener categorías únicas de las encuestas activas
    categorias_unicas = Categoria.objects.filter(
        encuesta__in=encuestas_publicas
    ).distinct()

    # Obtener grupos de interes unicos
    grupos_interes_unicos = GrupoInteres.objects.filter(
        encuesta__in=encuestas_publicas
    ).distinct()

    context = {
        'encuestas_publicas': encuestas_publicas,
        'categorias_unicas': categorias_unicas,
        'grupos_interes_unicos': grupos_interes_unicos,
    }
    return render(request, 'public/home.html', context)

def crear_pqrsfd(request):
    if request.method == 'POST':
        form = PQRSFDForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                pqrsfd = form.save(commit=False)
                
                # Si es anónimo, aseguramos que no se guarden datos personales
                if pqrsfd.es_anonimo:
                    pqrsfd.nombre = None
                    pqrsfd.email = None
                    pqrsfd.telefono = None
                
                # Guardar el objeto usando el ORM de Django
                pqrsfd.save()
                
                # Procesar archivo adjunto
                if 'archivos' in request.FILES:
                    archivo = request.FILES['archivos']
                    ArchivoAdjuntoPQRSFD.objects.create(
                        pqrsfd=pqrsfd,
                        archivo=archivo,
                        nombre_original=archivo.name,
                        tipo_archivo=archivo.content_type
                    )
                
                messages.success(request, 'Su PQRSFD ha sido registrado exitosamente. Le agradecemos por su contribución.')
                return redirect('public_home')
            except Exception as e:
                # Capturar errores y mostrar mensaje de error específico
                messages.error(request, f'Error al guardar PQRSFD: {str(e)}')
    else:
        form = PQRSFDForm()
    
    return render(request, 'public/crear_pqrsfd.html', {'form': form})

@login_required
def listar_pqrsfd(request):
    estado_filtro = request.GET.get('estado', None)
    
    # Obtenemos todos los PQRSFD
    todos_pqrsfd = PQRSFD.objects.all().order_by('-fecha_creacion')
    
    # Aplicar filtro por estado si está especificado
    if estado_filtro:
        if estado_filtro == 'vencidos':
            # Filtramos PQRSFD vencidos (debe hacerse en Python porque usa el método esta_vencido)
            pqrsfds = [p for p in todos_pqrsfd.filter(estado__in=['P', 'E']) if p.esta_vencido()]
        elif estado_filtro in dict(PQRSFD.ESTADO_CHOICES):
            pqrsfds = todos_pqrsfd.filter(estado=estado_filtro)
        else:
            pqrsfds = todos_pqrsfd
    else:
        pqrsfds = todos_pqrsfd
    
    # Contar PQRSFD por estado para mostrar en la interfaz
    conteo_estados = {
        'P': PQRSFD.objects.filter(estado='P').count(),
        'E': PQRSFD.objects.filter(estado='E').count(),
        'R': PQRSFD.objects.filter(estado='R').count(),
        'C': PQRSFD.objects.filter(estado='C').count(),
        'total': PQRSFD.objects.count(),
        'vencidos': sum(1 for p in PQRSFD.objects.filter(estado__in=['P', 'E']) if p.esta_vencido())
    }
    
    context = {
        'pqrsfds': pqrsfds,
        'estado_actual': estado_filtro,
        'conteo_estados': conteo_estados,
        'ESTADO_CHOICES': dict(PQRSFD.ESTADO_CHOICES)
    }
    
    
    return render(request, 'admin/listar_pqrsfd.html', context)

@login_required
def responder_pqrsfd(request, pqrsfd_id):
    pqrsfd = get_object_or_404(PQRSFD, id=pqrsfd_id)
    
    if request.method == 'POST':
        respuesta = request.POST.get('respuesta')
        estado = request.POST.get('estado')
        estado_anterior = pqrsfd.estado
        enviar_email = request.POST.get('enviar_email') == 'on'
        enviar_sms = request.POST.get('enviar_sms') == 'on'
        
        # Validar que el cambio de estado siga el flujo correcto
        estados_validos = get_siguientes_estados_validos(estado_anterior)
        if estado not in estados_validos:
            messages.warning(request, f'Cambio de estado no válido. De "{pqrsfd.get_estado_display()}" solo puede pasar a: {", ".join([dict(PQRSFD.ESTADO_CHOICES)[e] for e in estados_validos])}')
            return redirect('responder_pqrsfd', pqrsfd_id=pqrsfd.id)
        
        # Actualización de los datos
        pqrsfd.respuesta = respuesta
        pqrsfd.estado = estado
        
        # Solo actualizar fecha de respuesta si no existía antes o cambia a Resuelto/Cerrado
        if (not pqrsfd.fecha_respuesta and estado in ['R', 'C']):
            pqrsfd.fecha_respuesta = timezone.now()
            
        pqrsfd.save()
        
        # Manejar los archivos adjuntos
        archivos = request.FILES.getlist('archivos')
        archivos_guardados = 0
        for archivo in archivos:
            ArchivoRespuestaPQRSFD.objects.create(
                pqrsfd=pqrsfd,
                archivo=archivo,
                nombre_original=archivo.name,
                tipo_archivo=archivo.content_type
            )
            archivos_guardados += 1
            
        if archivos_guardados > 0:
            messages.success(request, f'Se han adjuntado {archivos_guardados} archivo(s) a la respuesta.')
        
        # Enviar notificaciones si se seleccionó la opción
        if (enviar_email or enviar_sms) and pqrsfd.respuesta and not pqrsfd.es_anonimo:
            try:
                ahora = timezone.now()
                
                if enviar_email and pqrsfd.email:
                    enviar_respuesta_email(pqrsfd, request)
                    pqrsfd.notificado_email = True
                    pqrsfd.fecha_notificacion = ahora
                    messages.success(request, f'Se ha enviado una notificación por correo a {pqrsfd.email}')
                
                if enviar_sms and pqrsfd.telefono:
                    enviar_respuesta_sms(pqrsfd)
                    pqrsfd.notificado_sms = True
                    if not pqrsfd.fecha_notificacion:
                        pqrsfd.fecha_notificacion = ahora
                    messages.success(request, f'Se ha enviado una notificación por SMS al número {pqrsfd.telefono}')
                
                pqrsfd.save()
            except Exception as e:
                messages.warning(request, f'Error al enviar notificaciones: {str(e)}')
        
        if estado_anterior != estado:
            messages.success(request, f'La respuesta ha sido guardada y el estado ha cambiado de "{dict(PQRSFD.ESTADO_CHOICES)[estado_anterior]}" a "{dict(PQRSFD.ESTADO_CHOICES)[estado]}".')
        else:
            messages.success(request, 'La respuesta ha sido guardada exitosamente.')
        
        # Redirección corregida
        return redirect('{}?estado={}'.format(reverse('listar_pqrsfd'), estado))
    
    return render(request, 'admin/responder_pqrsfd.html', {'pqrsfd': pqrsfd})

def enviar_respuesta_email(pqrsfd, request):
    """Envía un correo electrónico con la respuesta al PQRSFD"""
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags
    
    asunto = f'Respuesta a su {pqrsfd.get_tipo_display()} - {pqrsfd.asunto}'
    
    # Crear el contenido del correo en HTML
    contexto = {
        'pqrsfd': pqrsfd,
        'fecha': timezone.now().strftime("%d/%m/%Y %H:%M"),
        'url_base': f"{request.scheme}://{request.get_host()}"
    }
    contenido_html = render_to_string('emails/respuesta_pqrsfd.html', contexto)
    contenido_texto = strip_tags(contenido_html)
    
    # Crear y enviar el correo
    email = EmailMultiAlternatives(
        subject=asunto,
        body=contenido_texto,
        from_email='noreply@corpensar.com',  # Reemplazar con un correo real
        to=[pqrsfd.email]
    )
    email.attach_alternative(contenido_html, "text/html")
    
    # Adjuntar los archivos de la respuesta (si existen)
    for adjunto in pqrsfd.archivos_respuesta.all():
        email.attach_file(adjunto.archivo.path)
    
    email.send()

def enviar_respuesta_sms(pqrsfd):
    """
    Envía un SMS con la notificación de respuesta
    
    Nota: Esta es una implementación básica, necesitará configurar
    un servicio de SMS real para producción (Twilio, etc.)
    """
    # Este es un placeholder - necesita implementar con un proveedor real
    telefono = pqrsfd.telefono
    mensaje = f"Su {pqrsfd.get_tipo_display()} '{pqrsfd.asunto}' ha sido respondido. Por favor revise su correo o acceda a la plataforma."
    
    # Aquí implementaría la llamada a un servicio de SMS como Twilio
    # Por ejemplo:
    # from twilio.rest import Client
    # client = Client(account_sid, auth_token)
    # message = client.messages.create(
    #     body=mensaje,
    #     from_='+12345678901',  # Número Twilio
    #     to=telefono
    # )
    
    # Por ahora solo registramos que se "envió"
    print(f"SMS enviado a {telefono}: {mensaje}")
    return True

def get_siguientes_estados_validos(estado_actual):
    """Obtiene los siguientes estados válidos según el flujo de trabajo"""
    if estado_actual == 'P':  # Pendiente
        return ['P', 'E', 'R', 'C']  # Puede quedarse pendiente, pasar a en proceso, resuelto o cerrado
    elif estado_actual == 'E':  # En Proceso
        return ['E', 'R', 'C']  # Puede quedarse en proceso, pasar a resuelto o cerrado
    elif estado_actual == 'R':  # Resuelto
        return ['R', 'C']  # Puede quedarse resuelto o pasar a cerrado
    elif estado_actual == 'C':  # Cerrado
        return ['C']  # No puede cambiar de estado
    return ['P', 'E', 'R', 'C']  # Por defecto, permitir cualquier estado

@login_required
def categorias_principales(request):
    """Vista para listar todas las categorías principales"""
    categorias = Categoria.objects.all()
    return render(request, 'categorias_principales.html', {
        'categorias': categorias
    })

@login_required
def crear_categoria_principal(request):
    """Vista para crear una nueva categoría principal"""
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion', '')
        
        if Categoria.objects.filter(nombre=nombre).exists():
            messages.error(request, 'Ya existe una categoría con ese nombre.')
            return redirect('crear_categoria_principal')
        
        Categoria.objects.create(
            nombre=nombre,
            descripcion=descripcion
        )
        messages.success(request, 'Categoría principal creada exitosamente.')
        return redirect('categorias_principales')
    
    return render(request, 'crear_categoria_principal.html')

@login_required
def crear_subcategoria(request):
    """Vista para crear una nueva subcategoría"""
    if request.method == 'POST':
        categoria_id = request.POST.get('categoria_principal')  # Cambiado de 'categoria' a 'categoria_principal'
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion', '')
        
        categoria = get_object_or_404(Categoria, id=categoria_id)
        
        if Subcategoria.objects.filter(categoria=categoria, nombre__iexact=nombre).exists():
            messages.error(request, 'Ya existe una subcategoría con ese nombre en la categoría seleccionada.')
            return redirect('crear_subcategoria')
        
        Subcategoria.objects.create(
            categoria=categoria,
            nombre=nombre,
            descripcion=descripcion
        )
        messages.success(request, 'Subcategoría creada exitosamente.')
        return redirect('categorias_principales')
    
    categorias = Categoria.objects.all()
    return render(request, 'crear_subcategoria.html', {'categorias': categorias})

@login_required
def eliminar_categoria_principal(request, categoria_id):
    """Vista para eliminar una categoría principal"""
    categoria = get_object_or_404(Categoria, id=categoria_id)
    
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, 'Categoría eliminada exitosamente.')
        return redirect('categorias_principales')
    
    return render(request, 'confirmar_eliminar_categoria.html', {
        'categoria': categoria
    })

@login_required
def eliminar_subcategoria(request, subcategoria_id):
    """Vista para eliminar una subcategoría"""
    subcategoria = get_object_or_404(Subcategoria, id=subcategoria_id)
    
    # Verificar si hay encuestas asociadas a esta subcategoría
    encuestas_relacionadas = Encuesta.objects.filter(subcategoria=subcategoria).count()
    
    if request.method == 'POST':
        # Si hay encuestas relacionadas, cambiar su subcategoría a None
        if encuestas_relacionadas:
            Encuesta.objects.filter(subcategoria=subcategoria).update(subcategoria=None)
        
        nombre_subcategoria = subcategoria.nombre
        subcategoria.delete()
        messages.success(request, f'Subcategoría "{nombre_subcategoria}" eliminada exitosamente.')
        return redirect('categorias_principales')
    
    # Si la solicitud es GET y proviene de JavaScript AJAX, devolvemos datos JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'encuestas_relacionadas': encuestas_relacionadas,
            'nombre': subcategoria.nombre
        })
    
    # Si es GET normal, seguimos mostrando la página de confirmación por compatibilidad
    return render(request, 'confirmar_eliminar_subcategoria.html', {
        'subcategoria': subcategoria,
        'encuestas_relacionadas': encuestas_relacionadas
    })

def get_subcategorias(request):
    """Vista para obtener subcategorías por categoría vía AJAX"""
    categoria_id = request.GET.get('categoria')
    if categoria_id:
        subcategorias = Subcategoria.objects.filter(categoria_id=categoria_id).values('id', 'nombre')
        return JsonResponse(list(subcategorias), safe=False)
    return JsonResponse([], safe=False)

def qr_generator(request):
    """
    Vista para generar códigos QR de formularios
    """
    return render(request, 'qr_generator.html')

@login_required
@require_http_methods(["POST"])
def editar_multiples_preguntas(request, encuesta_id):
    encuesta = get_object_or_404(Encuesta, id=encuesta_id, creador=request.user)
    
    try:
        with transaction.atomic():
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
            
            # Actualizar cada pregunta
            for pregunta in preguntas:
                requerida = request.POST.get(f'requerida_{pregunta.id}') == 'on'
                permitir_archivos = request.POST.get(f'permitir_archivos_{pregunta.id}') == 'on'
                
                pregunta.requerida = requerida
                pregunta.permitir_archivos = permitir_archivos
                pregunta.save()
            
            messages.success(request, "Preguntas actualizadas exitosamente.")
            
    except Exception as e:
        messages.error(request, f"Error al actualizar las preguntas: {str(e)}")
    
    return redirect('editar_encuesta', encuesta_id=encuesta.id)

@login_required
def agregar_caracterizacion(request, encuesta_id):
    encuesta = get_object_or_404(Encuesta, id=encuesta_id, creador=request.user)
    
    if request.method == 'POST':
        requeridas = request.POST.get('preguntas_obligatorias', 'false') == 'true'
        
        # Obtener el último orden de las preguntas existentes
        ultimo_orden = 0
        
        # Obtener todas las preguntas ya es una lista ordenada
        preguntas = encuesta.obtener_preguntas()
        if preguntas:
            ultimo_orden = max(p.orden for p in preguntas)
        
        # Crear las preguntas de caracterización
        preguntas = [
            {
                'tipo': 'TEXT',
                'texto': 'Nombre del Entrevistador',
                'orden': ultimo_orden + 1,
                'seccion': 'Caracterización',
                'requerida': requeridas
            },
            {
                'tipo': 'TEXT',
                'texto': '¿Cuál es su nombre completo?',
                'orden': ultimo_orden + 2,
                'seccion': 'Caracterización',
                'requerida': requeridas
            },
            {
                'tipo': 'TEXT',
                'texto': 'Identificación',
                'orden': ultimo_orden + 3,
                'seccion': 'Caracterización',
                'requerida': requeridas
            },
            {
                'tipo': 'TEXT',
                'texto': 'Correo electrónico',
                'orden': ultimo_orden + 4,
                'seccion': 'Caracterización',
                'requerida': False,
                'placeholder': 'ejemplo@correo.com'
            },
            {
                'tipo': 'TEXT',
                'texto': 'Número de teléfono o celular',
                'orden': ultimo_orden + 5,
                'seccion': 'Caracterización',
                'requerida': False,
                'placeholder': 'Ej: 3001234567'
            },
            {
                'tipo': 'RADIO',
                'texto': '¿Cuál es su sexo?',
                'orden': ultimo_orden + 6,
                'seccion': 'Caracterización',
                'requerida': requeridas,
                'opciones': [
                    {'texto': 'Masculino', 'valor': 'a', 'orden': 1},
                    {'texto': 'Femenino', 'valor': 'b', 'orden': 2},
                    {'texto': 'Otro', 'valor': 'c', 'orden': 3},
                    {'texto': 'Prefiero no responder', 'valor': 'd', 'orden': 4}
                ]
            },
            {
                'tipo': 'RADIO',
                'texto': '¿Cuál es su rango de edad?',
                'orden': ultimo_orden + 7,
                'seccion': 'Caracterización',
                'requerida': requeridas,
                'opciones': [
                    {'texto': 'Menos de 18 años', 'valor': 'a', 'orden': 1},
                    {'texto': '18 a 25 años', 'valor': 'b', 'orden': 2},
                    {'texto': '26 a 35 años', 'valor': 'c', 'orden': 3},
                    {'texto': '36 a 45 años', 'valor': 'd', 'orden': 4},
                    {'texto': '46 a 60 años', 'valor': 'e', 'orden': 5},
                    {'texto': 'Más de 60 años', 'valor': 'f', 'orden': 6}
                ]
            },
            {
                'tipo': 'CHECK',
                'texto': '¿A cuál(es) de los siguientes grupos diferenciales pertenece?',
                'orden': ultimo_orden + 8,
                'seccion': 'Caracterización',
                'requerida': requeridas,
                'opciones': [
                    {'texto': 'Comunidad Indígena', 'valor': 'a', 'orden': 1},
                    {'texto': 'Comunidad Afrodescendiente', 'valor': 'b', 'orden': 2},
                    {'texto': 'Comunidad Campesina', 'valor': 'c', 'orden': 3},
                    {'texto': 'Persona con Discapacidad', 'valor': 'd', 'orden': 4},
                    {'texto': 'LGBTIQ+', 'valor': 'e', 'orden': 5},
                    {'texto': 'Victima del conflicto armado', 'valor': 'f', 'orden': 6},
                    {'texto': 'Otro', 'valor': 'g', 'orden': 7},
                    {'texto': 'Ninguno', 'valor': 'h', 'orden': 8}
                ]
            }
        ]
        
        # Crear cada pregunta
        for pregunta_data in preguntas:
            if pregunta_data['tipo'] == 'TEXT':
                pregunta = PreguntaTexto.objects.create(
                    encuesta=encuesta,
                    texto=pregunta_data['texto'],
                    tipo=pregunta_data['tipo'],
                    requerida=pregunta_data['requerida'],
                    orden=pregunta_data['orden'],
                    seccion=pregunta_data['seccion'],
                    ayuda=pregunta_data.get('ayuda', ''),
                    placeholder=pregunta_data.get('placeholder', '')
                )
            elif pregunta_data['tipo'] == 'RADIO':
                pregunta = PreguntaOpcionMultiple.objects.create(
                    encuesta=encuesta,
                    texto=pregunta_data['texto'],
                    tipo=pregunta_data['tipo'],
                    requerida=pregunta_data['requerida'],
                    orden=pregunta_data['orden'],
                    seccion=pregunta_data['seccion']
                )
                # Agregar opciones
                for opcion_data in pregunta_data['opciones']:
                    OpcionMultiple.objects.create(
                        pregunta=pregunta,
                        texto=opcion_data['texto'],
                        valor=opcion_data['valor'],
                        orden=opcion_data['orden']
                    )
            elif pregunta_data['tipo'] == 'CHECK':
                pregunta = PreguntaCasillasVerificacion.objects.create(
                    encuesta=encuesta,
                    texto=pregunta_data['texto'],
                    tipo=pregunta_data['tipo'],
                    requerida=pregunta_data['requerida'],
                    orden=pregunta_data['orden'],
                    seccion=pregunta_data['seccion']
                )
                # Agregar opciones
                for opcion_data in pregunta_data['opciones']:
                    OpcionCasillaVerificacion.objects.create(
                        pregunta=pregunta,
                        texto=opcion_data['texto'],
                        valor=opcion_data['valor'],
                        orden=opcion_data['orden']
                    )
        
        messages.success(request, 'Preguntas de caracterización agregadas exitosamente.')
        return redirect('editar_encuesta', encuesta_id=encuesta.id)
    
    return redirect('editar_encuesta', encuesta_id=encuesta.id)

@login_required
def exportar_encuesta_json(request, encuesta_id):
    # Obtener la encuesta
    encuesta = get_object_or_404(Encuesta, id=encuesta_id)
    
    # Verificar que el usuario tenga permiso para ver esta encuesta
    if not request.user.is_staff and encuesta.usuario != request.user:
        return HttpResponseForbidden("No tienes permiso para exportar esta encuesta")
    
    # Obtener todas las preguntas relacionadas
    preguntas = []
    
    # Preguntas de texto
    preguntas_texto = encuesta.preguntatexto_relacionadas.all()
    for pregunta in preguntas_texto:
        preguntas.append({
            'tipo': 'texto',
            'texto': pregunta.texto,
            'requerida': pregunta.requerida
        })
    
    # Preguntas de texto múltiple
    preguntas_texto_multiple = encuesta.preguntatextomultiple_relacionadas.all()
    for pregunta in preguntas_texto_multiple:
        preguntas.append({
            'tipo': 'texto_multiple',
            'texto': pregunta.texto,
            'requerida': pregunta.requerida
        })
    
    # Preguntas de opción múltiple
    preguntas_opcion_multiple = encuesta.preguntaopcionmultiple_relacionadas.all()
    for pregunta in preguntas_opcion_multiple:
        opciones = [opcion.texto for opcion in pregunta.opciones.all()]
        preguntas.append({
            'tipo': 'opcion_multiple',
            'texto': pregunta.texto,
            'requerida': pregunta.requerida,
            'opciones': opciones
        })
    
    # Preguntas de casillas de verificación
    preguntas_casillas = encuesta.preguntacasillasverificacion_relacionadas.all()
    for pregunta in preguntas_casillas:
        opciones = [opcion.texto for opcion in pregunta.opciones.all()]
        preguntas.append({
            'tipo': 'casillas_verificacion',
            'texto': pregunta.texto,
            'requerida': pregunta.requerida,
            'opciones': opciones
        })
    
    # Preguntas de menú desplegable
    preguntas_menu = encuesta.preguntamenudesplegable_relacionadas.all()
    for pregunta in preguntas_menu:
        opciones = [opcion.texto for opcion in pregunta.opciones.all()]
        preguntas.append({
            'tipo': 'menu_desplegable',
            'texto': pregunta.texto,
            'requerida': pregunta.requerida,
            'opciones': opciones
        })
    
    # Preguntas de estrellas
    preguntas_estrellas = encuesta.preguntaestrellas_relacionadas.all()
    for pregunta in preguntas_estrellas:
        preguntas.append({
            'tipo': 'estrellas',
            'texto': pregunta.texto,
            'requerida': pregunta.requerida,
            'max_estrellas': pregunta.max_estrellas
        })
    
    # Preguntas de escala
    preguntas_escala = encuesta.preguntaescala_relacionadas.all()
    for pregunta in preguntas_escala:
        preguntas.append({
            'tipo': 'escala',
            'texto': pregunta.texto,
            'requerida': pregunta.requerida,
            'min_valor': pregunta.min_valor,
            'max_valor': pregunta.max_valor,
            'etiqueta_min': pregunta.etiqueta_min,
            'etiqueta_max': pregunta.etiqueta_max
        })
    
    # Preguntas de matriz
    preguntas_matriz = encuesta.preguntamatriz_relacionadas.all()
    for pregunta in preguntas_matriz:
        filas = [fila.texto for fila in pregunta.filas.all()]
        columnas = [columna.texto for columna in pregunta.columnas.all()]
        preguntas.append({
            'tipo': 'matriz',
            'texto': pregunta.texto,
            'requerida': pregunta.requerida,
            'filas': filas,
            'columnas': columnas
        })
    
    # Preguntas de fecha
    preguntas_fecha = encuesta.preguntafecha_relacionadas.all()
    for pregunta in preguntas_fecha:
        preguntas.append({
            'tipo': 'fecha',
            'texto': pregunta.texto,
            'requerida': pregunta.requerida
        })
    
    # Construir el JSON final
    encuesta_json = {
        'id': encuesta.id,
        'titulo': encuesta.titulo,
        'descripcion': encuesta.descripcion,
        'fecha_creacion': encuesta.fecha_creacion.isoformat(),
        'fecha_inicio': encuesta.fecha_inicio.isoformat() if encuesta.fecha_inicio else None,
        'fecha_fin': encuesta.fecha_fin.isoformat() if encuesta.fecha_fin else None,
        'activa': encuesta.activa,
        'region': encuesta.region.nombre if encuesta.region else None,
        'categoria': encuesta.categoria.nombre if encuesta.categoria else None,
        'preguntas': preguntas
    }
    
    # Crear la respuesta HTTP con el JSON
    response = HttpResponse(json.dumps(encuesta_json, ensure_ascii=False, indent=2), content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="encuesta_{encuesta.id}.json"'
    
    return response


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

def mi_perfil(request):
    return render(request, 'perfil/mi_perfil.html')

def configuracion(request):
    return render(request, 'perfil/configuracion.html')

def eliminar_respuesta_encuesta(request, respuesta_id):
    """
    Elimina una respuesta de encuesta completa, incluyendo todas sus subrespuestas.
    Solo permitido para administradores y creadores de la encuesta.
    """
    respuesta = get_object_or_404(RespuestaEncuesta, id=respuesta_id)
    encuesta = respuesta.encuesta
    
    # Comprobar permisos: solo permitir al creador de la encuesta o administradores
    if not request.user.is_authenticated or (request.user != encuesta.creador and not request.user.is_staff):
        messages.error(request, "No tienes permiso para eliminar esta respuesta.")
        return redirect('resultados_encuesta', pk=encuesta.id)
    
    # Guardar el ID de la encuesta antes de eliminar la respuesta
    encuesta_id = encuesta.id
    
    # Eliminar la respuesta
    respuesta.delete()
    
    messages.success(request, "La respuesta ha sido eliminada con éxito.")
    return redirect('resultados_encuesta', pk=encuesta_id)

@login_required
def administrar_usuarios(request):
    """Vista para que los administradores gestionen los usuarios"""
    # Verificar si el usuario es administrador
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para acceder a esta sección.")
        return redirect('index')
    
    # Obtener todos los usuarios
    usuarios = User.objects.all().order_by('-date_joined')
    
    return render(request, 'usuarios/administrar_usuarios.html', {
        'usuarios': usuarios
    })

@login_required
def crear_usuario(request):
    """Vista para que los administradores creen nuevos usuarios"""
    # Verificar si el usuario es administrador
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para acceder a esta sección.")
        return redirect('index')
    
    if request.method == 'POST':
        form = CrearUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Usuario '{user.username}' creado correctamente.")
            return redirect('administrar_usuarios')
    else:
        form = CrearUsuarioForm()
    
    return render(request, 'usuarios/crear_usuario.html', {
        'form': form
    })

# API Views para el mapa y estadísticas
def api_estadisticas_municipios(request):
    """
    API que devuelve estadísticas de municipios en formato JSON para el mapa
    """
    try:
        # Obtener todas las regiones y municipios
        regiones = Region.objects.all()
        todos_municipios = Municipio.objects.select_related('region').all()
        
        # Filtros aplicados (opcional)
        region_id = request.GET.get('region')
        municipio_id = request.GET.get('municipio')
        
        # Consulta base para municipios
        municipios_query = todos_municipios
        
        # Aplicar filtros si existen
        if region_id and region_id != 'todas':
            municipios_query = municipios_query.filter(region_id=region_id)
        if municipio_id and municipio_id != 'todos':
            municipios_query = municipios_query.filter(id=municipio_id)
        
        # Estadísticas por municipio
        datos_municipios = {}
        
        for municipio in municipios_query:
            # Obtener encuestas activas para este municipio
            encuestas_activas = Encuesta.objects.filter(region=municipio.region)
            
            # Obtener respuestas para este municipio
            respuestas = RespuestaEncuesta.objects.filter(municipio=municipio)
            
            # Contar respuestas únicas por encuesta
            encuestas_respondidas = respuestas.values('encuesta').distinct().count()
            
            # Calcular estadísticas
            municipio_total_encuestas = encuestas_activas.count()
            municipio_total_respuestas = respuestas.count()
            
            # Calcular tasa de finalización
            tasa_finalizacion = 0
            if municipio_total_encuestas > 0:
                tasa_finalizacion = (encuestas_respondidas / municipio_total_encuestas) * 100
            
            # La clave debe ser el nombre del municipio en mayúsculas ya que así lo espera el código JS
            datos_municipios[municipio.nombre.upper()] = {
                'id': municipio.id,
                'nombre': municipio.nombre,
                'region': municipio.region.nombre,
                'region_id': municipio.region.id,
                'totalEncuestas': municipio_total_encuestas,
                'totalRespuestas': municipio_total_respuestas,
                'encuestasRespondidas': encuestas_respondidas,
                'tasaFinalizacion': round(tasa_finalizacion, 2),
                'latitud': municipio.latitud,
                'longitud': municipio.longitud
            }
        
        # Retornar directamente el diccionario sin envolverlo en otro objeto
        return JsonResponse(datos_municipios)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)

def api_mapa_municipios(request):
    """
    API que devuelve datos de municipios para el mapa
    """
    try:
        # Obtener todos los municipios con coordenadas
        municipios = Municipio.objects.select_related('region').all()
        
        # Filtrar por región si se proporciona
        region_id = request.GET.get('region')
        if region_id and region_id != 'todas':
            municipios = municipios.filter(region_id=region_id)
        
        # Preparar datos para el mapa
        datos_mapa = {}
        for municipio in municipios:
            if municipio.latitud and municipio.longitud:  # Solo incluir si tiene coordenadas
                # Contar respuestas para este municipio
                respuestas = RespuestaEncuesta.objects.filter(municipio=municipio).count()
                
                # La clave debe ser el nombre del municipio en mayúsculas
                datos_mapa[municipio.nombre.upper()] = {
                    'id': municipio.id,
                    'nombre': municipio.nombre,
                    'region': municipio.region.nombre,
                    'region_id': municipio.region.id,
                    'latitud': municipio.latitud,
                    'longitud': municipio.longitud,
                    'totalRespuestas': respuestas,
                    'totalEncuestas': Encuesta.objects.filter(region=municipio.region).count(),
                    'tasaFinalizacion': 0  # Se calculará correctamente si es necesario
                }
        
        # Retornar directamente el diccionario como lo espera el frontend
        return JsonResponse(datos_mapa)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)

# --- NUEVA VISTA API ---
def api_encuestas_por_municipio(request, municipio_id):
    """
    API que devuelve una lista de encuestas activas y públicas
    asociadas a la región del municipio especificado.
    """
    # Validar que el municipio exista
    municipio = get_object_or_404(Municipio.objects.select_related('region'), id=municipio_id)
    region_id = municipio.region.id

    try:
        # Filtrar encuestas: activas, públicas y de la misma región que el municipio
        # También podrías filtrar directamente por municipio si una encuesta pertenece a uno solo:
        # encuestas = Encuesta.objects.filter(municipio_id=municipio_id, activa=True, es_publica=True)
        encuestas = Encuesta.objects.filter(
            Q(region_id=region_id), # De la misma región
            # Opcional: incluir encuestas sin región específica si aplica
            # Q(region__isnull=True) |
            activa=True,
            es_publica=True,
            fecha_inicio__lte=timezone.now(), # Que ya hayan iniciado
            fecha_fin__gte=timezone.now() # Que no hayan terminado
        ).values(
            'id', 'titulo', 'slug' # Devolver solo campos necesarios
        ).order_by('-fecha_creacion')[:10] # Limitar a 10 más recientes

        # Convertir QuerySet a lista de diccionarios
        lista_encuestas = list(encuestas)

        return JsonResponse(lista_encuestas, safe=False) # safe=False porque devolvemos una lista

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def duplicar_encuesta_json(request, encuesta_id):
    """
    Duplica una encuesta y todas sus preguntas utilizando serialización JSON.
    Esta función es más robusta que duplicar_encuesta() ya que serializa todos los campos 
    automáticamente sin necesidad de listarlos.
    """
    encuesta_original = get_object_or_404(Encuesta, id=encuesta_id)
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            nuevo_titulo = request.POST.get('titulo', f"{encuesta_original.titulo} (Copia)")
            
            # Verificar que el título no esté repetido
            if Encuesta.objects.filter(titulo=nuevo_titulo).exists():
                messages.error(request, 'Ya existe una encuesta con este título. Por favor, elige otro.')
                return redirect('duplicar_encuesta_json', encuesta_id=encuesta_original.id)
            
            # Generar slug único
            from django.utils.text import slugify
            slug_base = slugify(nuevo_titulo)
            slug = slug_base
            counter = 1
            while Encuesta.objects.filter(slug=slug).exists():
                slug = f"{slug_base}-{counter}"
                counter += 1
                
            # Crear la nueva encuesta con datos básicos que deben ser diferentes
            nueva_encuesta = Encuesta.objects.create(
                titulo=nuevo_titulo,
                slug=slug,
                creador=request.user,
                fecha_creacion=timezone.now(),
                fecha_inicio=request.POST.get('fecha_inicio'),
                fecha_fin=request.POST.get('fecha_fin'),
                activa=request.POST.get('activa') == 'on',
                es_publica=request.POST.get('es_publica') == 'on',
                region_id=request.POST.get('region'),
                categoria_id=request.POST.get('categoria'),
            )
            
            # Copiar todos los demás campos directamente usando __dict__
            # Excluimos campos que no deben copiarse
            exclude_fields = ['_state', 'id', 'titulo', 'slug', 'creador_id', 
                            'fecha_creacion', 'fecha_inicio', 'fecha_fin', 
                            'activa', 'es_publica', 'region_id', 'categoria_id']
            
            for field, value in encuesta_original.__dict__.items():
                if field not in exclude_fields:
                    setattr(nueva_encuesta, field, value)
            
            nueva_encuesta.save()
            
            # Función auxiliar para duplicar preguntas con opciones
            def duplicar_pregunta_con_opciones(modelo_pregunta, relation_name, 
                                              modelo_opcion=None, opcion_relation_name=None):
                """Duplica preguntas de un tipo específico y sus opciones si las tiene"""
                # Obtener el manager para este tipo de pregunta (por ejemplo, preguntatexto_relacionadas)
                manager = getattr(encuesta_original, relation_name)
                
                for pregunta_orig in manager.all():
                    # Excluir campos que no deben copiarse
                    valores_pregunta = {k: v for k, v in pregunta_orig.__dict__.items() 
                                      if k not in ['_state', 'id', 'encuesta_id']}
                    
                    # Asociar a la nueva encuesta
                    valores_pregunta['encuesta'] = nueva_encuesta
                    
                    # Crear la nueva pregunta
                    nueva_pregunta = modelo_pregunta.objects.create(**valores_pregunta)
                    
                    # Si tiene opciones, duplicarlas
                    if modelo_opcion and opcion_relation_name:
                        for opcion_orig in getattr(pregunta_orig, opcion_relation_name).all():
                            valores_opcion = {k: v for k, v in opcion_orig.__dict__.items() 
                                          if k not in ['_state', 'id', 'pregunta_id']}
                            valores_opcion['pregunta'] = nueva_pregunta
                            modelo_opcion.objects.create(**valores_opcion)
            
            # Duplicar todos los tipos de preguntas
            duplicar_pregunta_con_opciones(PreguntaTexto, 'preguntatexto_relacionadas')
            duplicar_pregunta_con_opciones(PreguntaTextoMultiple, 'preguntatextomultiple_relacionadas')
            duplicar_pregunta_con_opciones(PreguntaOpcionMultiple, 'preguntaopcionmultiple_relacionadas', 
                                         OpcionMultiple, 'opciones')
            duplicar_pregunta_con_opciones(PreguntaCasillasVerificacion, 'preguntacasillasverificacion_relacionadas', 
                                         OpcionCasillaVerificacion, 'opciones')
            duplicar_pregunta_con_opciones(PreguntaMenuDesplegable, 'preguntamenudesplegable_relacionadas', 
                                         OpcionMenuDesplegable, 'opciones')
            duplicar_pregunta_con_opciones(PreguntaEstrellas, 'preguntaestrellas_relacionadas')
            duplicar_pregunta_con_opciones(PreguntaFecha, 'preguntafecha_relacionadas')
            
            # Para preguntas de escala (sin opciones)
            duplicar_pregunta_con_opciones(PreguntaEscala, 'preguntaescala_relacionadas')
            
            # Caso especial: Preguntas de matriz que tienen una relación con escala y otra con items
            for pregunta_matriz_orig in encuesta_original.preguntamatriz_relacionadas.all():
                # Primero duplicar la escala asociada
                escala_orig = pregunta_matriz_orig.escala
                valores_escala = {k: v for k, v in escala_orig.__dict__.items() 
                                if k not in ['_state', 'id', 'encuesta_id']}
                valores_escala['encuesta'] = nueva_encuesta
                nueva_escala = PreguntaEscala.objects.create(**valores_escala)
                
                # Ahora duplicar la pregunta de matriz
                valores_matriz = {k: v for k, v in pregunta_matriz_orig.__dict__.items() 
                               if k not in ['_state', 'id', 'encuesta_id', 'escala_id']}
                valores_matriz['encuesta'] = nueva_encuesta
                valores_matriz['escala'] = nueva_escala
                nueva_matriz = PreguntaMatriz.objects.create(**valores_matriz)
                
                # Duplicar los items (filas) de la matriz
                for item_orig in pregunta_matriz_orig.items.all():
                    valores_item = {k: v for k, v in item_orig.__dict__.items() 
                                 if k not in ['_state', 'id', 'pregunta_id']}
                    valores_item['pregunta'] = nueva_matriz
                    ItemMatrizPregunta.objects.create(**valores_item)
            
            messages.success(request, '¡Encuesta duplicada exitosamente!')
            return redirect('editar_encuesta', encuesta_id=nueva_encuesta.id)
            
        except Exception as e:
            # Activar esto para depuración en producción si es necesario
            import traceback
            print(f"Error al duplicar encuesta: {type(e).__name__} - {str(e)}")
            traceback.print_exc()
            
            messages.error(request, f'Error al duplicar la encuesta: {str(e)}')
            return redirect('lista_encuestas')
    
    # Si es GET, mostrar el formulario de duplicación
    regiones = Region.objects.all()
    categorias = Categoria.objects.all()
    
    return render(request, 'Encuesta/duplicar_encuesta.html', {
        'encuesta_original': encuesta_original,
        'regiones': regiones,
        'categorias': categorias,
        'now': timezone.now()
    })

@login_required
def grupos_interes(request):
    """Vista para listar todos los grupos de interés"""
    grupos = GrupoInteres.objects.all()
    return render(request, 'grupos_interes/grupos_interes.html', {
        'grupos': grupos
    })

@login_required
def crear_grupo_interes(request):
    """Vista para crear un nuevo grupo de interés"""
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion', '')
        
        if GrupoInteres.objects.filter(nombre=nombre).exists():
            messages.error(request, 'Ya existe un grupo de interés con ese nombre.')
            return redirect('crear_grupo_interes')
        
        GrupoInteres.objects.create(
            nombre=nombre,
            descripcion=descripcion
        )
        messages.success(request, f'Grupo de interés "{nombre}" creado exitosamente.')
        return redirect('grupos_interes')
    
    return render(request, 'grupos_interes/crear_grupo_interes.html')

@login_required
def eliminar_grupo_interes(request, grupo_id):
    """Vista para eliminar un grupo de interés"""
    grupo = get_object_or_404(GrupoInteres, id=grupo_id)
    
    # Verificar si hay encuestas asociadas
    encuestas_asociadas = Encuesta.objects.filter(grupo_interes=grupo).count()
    
    if request.method == 'POST':
        # Si hay encuestas relacionadas, cambiar su grupo a None
        if encuestas_asociadas:
            Encuesta.objects.filter(grupo_interes=grupo).update(grupo_interes=None)
        
        nombre = grupo.nombre
        grupo.delete()
        messages.success(request, f'Grupo de interés "{nombre}" eliminado exitosamente.')
        return redirect('grupos_interes')
    
    # Si la solicitud es GET y proviene de JavaScript AJAX, devolvemos datos JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'encuestas_asociadas': encuestas_asociadas,
            'nombre': grupo.nombre
        })
    
    # Si es GET normal, mostramos la página de confirmación
    return render(request, 'grupos_interes/confirmar_eliminar_grupo.html', {
        'grupo': grupo,
        'encuestas_asociadas': encuestas_asociadas
    })

@login_required
def editar_grupo_interes(request, grupo_id):
    """Vista para editar un grupo de interés"""
    grupo = get_object_or_404(GrupoInteres, id=grupo_id)
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion', '')
        
        grupo.nombre = nombre
        grupo.descripcion = descripcion
        grupo.save()
        messages.success(request, f'Grupo de interés "{nombre}" actualizado exitosamente.')
        return redirect('grupos_interes')
    
    return render(request, 'grupos_interes/editar_grupo_interes.html', {
        'grupo': grupo
    })

@login_required
def generar_certificado(request):
    """Vista para generar certificados a partir de formularios completados"""
    if request.method == 'POST':
        form_id = request.POST.get('formulario_id')
        nombre = request.POST.get('nombre_completo')
        documento = request.POST.get('numero_identificacion')
        correo = request.POST.get('correo')
        telefono = request.POST.get('telefono')
        municipio = request.POST.get('municipio')
        fecha = request.POST.get('fecha_certificado')

        print(f"municipio: {municipio}")
        print(f"telefono: {telefono}")
        print(f"correo: {correo}")
        print(f"documento: {documento}")
        print(f"nombre: {nombre}")
        print(f"form_id: {form_id}")
        print(f"fecha: {fecha}")
        
        if form_id and nombre and documento:
            encuesta = get_object_or_404(Encuesta, id=form_id)
            fecha_actual = timezone.now().strftime('%d/%m/%Y')
            
            context = {
                'encuesta': encuesta,
                'nombre_completo': nombre,
                'numero_identificacion': documento,
                'correo': correo,
                'telefono': telefono,
                'fecha_actual': fecha_actual,
                'municipio': municipio,
            }
            
            return render(request, 'certificado_template.html', context)
    
    # Si llegamos aquí, no se enviaron los datos correctamente
    # Obtener la lista de encuestas disponibles para seleccionar
    encuestas = Encuesta.objects.all().order_by('-fecha_creacion')
    
    return render(request, 'generar_certificado.html', {
        'encuestas': encuestas
    })


