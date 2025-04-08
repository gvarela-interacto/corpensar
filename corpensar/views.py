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
from django.db.models import Count, Avg
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse, Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods
from django import forms
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from .models import *
from .decorators import *
import locale
import re
import csv
from datetime import datetime

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

    encuestas_proximo_fin = Encuesta.objects.filter(
        fecha_fin__gte=now,
        fecha_fin__lte=now + timezone.timedelta(days=3)
    ).count()

    encuestas_poca_participacion = Encuesta.objects.annotate(
        num_respuestas=Count('respuestas')
    ).filter(num_respuestas__lt=5).count()

    tipos_preguntas = PreguntaTexto.objects.values('tipo').annotate(
        total=Count('tipo')
    ).order_by('-total')

    ultimas_respuestas = RespuestaEncuesta.objects.select_related(
        'encuesta', 'usuario'
    ).order_by('-fecha_respuesta')[:10]

    # Encuestas con detalle por nombre, cantidad de respuestas y promedio
    encuestas_detalle = Encuesta.objects.annotate(
        cantidad_respuestas=Count('respuestas'),
        promedio_respuestas=Avg('respuestas__id')  # O puedes usar otra métrica más significativa
    ).order_by('-fecha_creacion')

    context = {
        'total_encuestas': total_encuestas,
        'encuestas_activas': encuestas_activas,
        'total_respuestas': total_respuestas,
        'avg_respuestas': round(avg_respuestas, 1),
        'encuestas_proximo_fin': encuestas_proximo_fin,
        'encuestas_poca_participacion': encuestas_poca_participacion,
        'tipos_preguntas': tipos_preguntas,
        'ultimas_respuestas': ultimas_respuestas,
        'encuestas_detalle': encuestas_detalle, 
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

    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        slug = request.POST.get('slug')
        descripcion = request.POST.get('descripcion')
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')
        activa = bool(request.POST.get('activa'))
        es_publica = bool(request.POST.get('es_publica'))

        # Crear la encuesta y guardarla en una variable
        encuesta = Encuesta.objects.create(
            titulo=titulo,
            slug=slug,
            descripcion=descripcion,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            activa=activa,
            es_publica=es_publica,
            creador=request.user
        )

        # Obtener preguntas del formulario
        preguntas = []
        preguntas_ids = set()
        
        # Primero, identificar todos los IDs de preguntas
        for key in request.POST:
            if key.startswith('questions[') and '][text]' in key:
                pregunta_id = key.split('[')[1].split(']')[0]
                preguntas_ids.add(pregunta_id)
        
        # Luego, construir el diccionario para cada pregunta
        for pregunta_id in preguntas_ids:
            pregunta = {
                'texto': request.POST.get(f'questions[{pregunta_id}][text]', ''),
                'tipo': request.POST.get(f'questions[{pregunta_id}][type]', 'TEXT'),
                'requerida': request.POST.get(f'questions[{pregunta_id}][required]', 'true') == 'true',
                'orden': int(request.POST.get(f'questions[{pregunta_id}][order]', pregunta_id)),
                'ayuda': request.POST.get(f'questions[{pregunta_id}][help]', ''),
                'seccion': request.POST.get(f'questions[{pregunta_id}][section]', '')
            }
            
            # Agregar atributos específicos según el tipo
            tipo = pregunta['tipo']
            
            if tipo in ['TEXT', 'MTEXT']:
                pregunta['max_longitud'] = request.POST.get(f'questions[{pregunta_id}][max_length]', '250')
                pregunta['placeholder'] = request.POST.get(f'questions[{pregunta_id}][placeholder]', '')
                
                if tipo == 'MTEXT':
                    pregunta['filas'] = int(request.POST.get(f'questions[{pregunta_id}][rows]', '4'))
            
            elif tipo == 'RADIO':
                # Las opciones se procesarán después de crear la pregunta
                pass
            
            elif tipo == 'CHECK':
                pregunta['min_selecciones'] = int(request.POST.get(f'questions[{pregunta_id}][min_selections]', '1'))
                max_selections = request.POST.get(f'questions[{pregunta_id}][max_selections]', '')
                pregunta['max_selecciones'] = int(max_selections) if max_selections else None
            
            elif tipo == 'SELECT':
                pregunta['opcion_vacia'] = request.POST.get(f'questions[{pregunta_id}][empty_option]', 'true') == 'true'
                pregunta['texto_vacio'] = request.POST.get(f'questions[{pregunta_id}][empty_text]', 'Seleccione...')
            
            elif tipo == 'STAR':
                pregunta['max_estrellas'] = int(request.POST.get(f'questions[{pregunta_id}][max_stars]', '5'))
                pregunta['etiqueta_inicio'] = request.POST.get(f'questions[{pregunta_id}][label_start]', 'Muy malo')
                pregunta['etiqueta_fin'] = request.POST.get(f'questions[{pregunta_id}][label_end]', 'Excelente')
            
            elif tipo == 'SCALE':
                pregunta['min_valor'] = int(request.POST.get(f'questions[{pregunta_id}][min_value]', '1'))
                pregunta['max_valor'] = int(request.POST.get(f'questions[{pregunta_id}][max_value]', '5'))
                pregunta['paso'] = int(request.POST.get(f'questions[{pregunta_id}][step]', '1'))
                pregunta['etiqueta_min'] = request.POST.get(f'questions[{pregunta_id}][label_min]', 'Muy en desacuerdo')
                pregunta['etiqueta_max'] = request.POST.get(f'questions[{pregunta_id}][label_max]', 'Muy de acuerdo')
            
            elif tipo == 'MATRIX':
                # Para matrices, primero necesitamos crear una escala por defecto
                escala = PreguntaEscala.objects.create(
                    encuesta=encuesta,
                    texto="Escala para matriz",
                    tipo='SCALE',
                    requerida=True,
                    orden=0,
                    ayuda="Escala para matriz",
                    seccion='',
                    min_valor=1,
                    max_valor=5,
                    paso=1,
                    etiqueta_min='Muy en desacuerdo',
                    etiqueta_max='Muy de acuerdo'
                )
                
                pregunta_obj = PreguntaMatriz.objects.create(
                    encuesta=encuesta,
                    texto=pregunta['texto'],
                    tipo='MATRIX',
                    requerida=pregunta['requerida'],
                    orden=pregunta['orden'],
                    ayuda=pregunta['ayuda'],
                    seccion=pregunta['seccion'],
                    escala=escala
                )
                
                # Procesar los ítems de la matriz si están disponibles
                items = []
                for key in request.POST:
                    if key.startswith(f'questions[{pregunta_id}][items][') and '][text]' in key:
                        item_index = key.split('[')[3].split(']')[0]
                        item_text = request.POST.get(f'questions[{pregunta_id}][items][{item_index}][text]', '')
                        item_order = int(request.POST.get(f'questions[{pregunta_id}][items][{item_index}][order]', item_index))
                        items.append({
                            'texto': item_text,
                            'orden': item_order
                        })
                
                # Crear los ítems
                for item in items:
                    ItemMatrizPregunta.objects.create(
                        pregunta=pregunta_obj,
                        texto=item['texto'],
                        orden=item['orden']
                    )
            
            elif tipo in ['DATE', 'DATETIME']:
                pregunta['incluir_hora'] = tipo == 'DATETIME' or request.POST.get(f'questions[{pregunta_id}][include_time]', 'false') == 'true'
            
            preguntas.append(pregunta)
        
        # Si no hay preguntas, crear una por defecto
        if not preguntas:
            preguntas = [{
                'texto': "¿Cuál es su opinión sobre esta encuesta?",
                'tipo': 'TEXT',
                'requerida': True,
                'orden': 1,
                'ayuda': '',
                'seccion': ''
            }]
            
        for pregunta in preguntas:
            # Extraer atributos comunes
            texto = pregunta.get('texto', '')
            tipo = pregunta.get('tipo', '')
            requerida = pregunta.get('requerida', True)
            orden = pregunta.get('orden', 0)
            ayuda = pregunta.get('ayuda', '')
            seccion = pregunta.get('seccion', '')
            
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
                    max_longitud=pregunta.get('max_longitud', 250),
                    placeholder=pregunta.get('placeholder', '')
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
                    max_longitud=pregunta.get('max_longitud', 1000),
                    filas=pregunta.get('filas', 4),
                    placeholder=pregunta.get('placeholder', '')
                )
            elif tipo == 'RADIO':
                print('PreguntaOpcionMultiple', pregunta)
                PreguntaOpcionMultiple.objects.create(
                    encuesta=encuesta,
                    texto=texto,
                    tipo=tipo,
                    requerida=requerida,
                    orden=orden,
                    ayuda=ayuda,
                    seccion=seccion,
                    opciones=pregunta.get('opciones', [])
                )
                # Aquí podrías agregar las opciones si están disponibles
                
            elif tipo == 'CHECK':
                PreguntaCasillasVerificacion.objects.create(
                    encuesta=encuesta,
                    texto=texto,
                    tipo=tipo,
                    requerida=requerida,
                    orden=orden,
                    ayuda=ayuda,
                    seccion=seccion,
                    min_selecciones=pregunta.get('min_selecciones', 1),
                    max_selecciones=pregunta.get('max_selecciones', None)
                )
                # Aquí podrías agregar las opciones si están disponibles
                
            elif tipo == 'SELECT':
                PreguntaMenuDesplegable.objects.create(
                    encuesta=encuesta,
                    texto=texto,
                    tipo=tipo,
                    requerida=requerida,
                    orden=orden,
                    ayuda=ayuda,
                    seccion=seccion,
                    opcion_vacia=pregunta.get('opcion_vacia', True),
                    texto_vacio=pregunta.get('texto_vacio', 'Seleccione...')
                )
                # Aquí podrías agregar las opciones si están disponibles
                
            elif tipo == 'STAR':
                PreguntaEstrellas.objects.create(
                    encuesta=encuesta,
                    texto=texto,
                    tipo=tipo,
                    requerida=requerida,
                    orden=orden,
                    ayuda=ayuda,
                    seccion=seccion,
                    max_estrellas=pregunta.get('max_estrellas', 5),
                    etiqueta_inicio=pregunta.get('etiqueta_inicio', 'Muy malo'),
                    etiqueta_fin=pregunta.get('etiqueta_fin', 'Excelente')
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
                    min_valor=pregunta.get('min_valor', 1),
                    max_valor=pregunta.get('max_valor', 5),
                    paso=pregunta.get('paso', 1),
                    etiqueta_min=pregunta.get('etiqueta_min', 'Muy en desacuerdo'),
                    etiqueta_max=pregunta.get('etiqueta_max', 'Muy de acuerdo')
                )
                
            elif tipo == 'MATRIX':
                # Para matrices, primero necesitarías crear o seleccionar una escala
                escala = None  # Aquí deberías obtener o crear la escala
                PreguntaMatriz.objects.create(
                    encuesta=encuesta,
                    texto=texto,
                    tipo=tipo,
                    requerida=requerida,
                    orden=orden,
                    ayuda=ayuda,
                    seccion=seccion,
                    escala=escala
                )
                # Aquí podrías agregar los ítems si están disponibles
                
            elif tipo == 'DATE':
                PreguntaFecha.objects.create(
                    encuesta=encuesta,
                    texto=texto,
                    tipo=tipo,
                    requerida=requerida,
                    orden=orden,
                    ayuda=ayuda,
                    seccion=seccion,
                    incluir_hora=pregunta.get('incluir_hora', False)
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
        'preguntas': preguntas if 'preguntas' in locals() else []
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


class ResultadosEncuestaView(DetailView):
    model = Encuesta
    template_name = 'Encuesta/resultados_encuesta.html'
    context_object_name = 'encuesta'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        encuesta = self.object

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

        context['preguntas'] = preguntas
        context['graficas'] = {}

        for pregunta in preguntas:
            tipo = pregunta.__class__.__name__
            key = f"pregunta_{pregunta.id}"

            if tipo == 'PreguntaOpcionMultiple':
                respuestas = RespuestaOpcionMultiple.objects.filter(pregunta=pregunta)
                counter = Counter([r.opcion.texto for r in respuestas])
                context['graficas'][key] = dict(counter)

            elif tipo == 'PreguntaCasillasVerificacion':
                respuestas = RespuestaCasillasVerificacion.objects.filter(pregunta=pregunta)
                counter = Counter([r.opcion.texto for r in respuestas])
                context['graficas'][key] = dict(counter)

            elif tipo == 'PreguntaMenuDesplegable':
                respuestas = RespuestaOpcionMenuDesplegable.objects.filter(pregunta=pregunta)
                counter = Counter([r.opcion.texto for r in respuestas])
                context['graficas'][key] = dict(counter)

            elif tipo == 'PreguntaEstrellas':
                respuestas = RespuestaEstrellas.objects.filter(pregunta=pregunta)
                valores = [r.valor for r in respuestas]
                promedio = sum(valores) / len(valores) if valores else 0
                context['graficas'][key] = {
                    'valores': valores,
                    'promedio': promedio
                }

            elif tipo == 'PreguntaEscala':
                respuestas = RespuestaEscala.objects.filter(pregunta=pregunta)
                valores = [r.valor for r in respuestas]
                counter = Counter(valores)
                context['graficas'][key] = dict(counter)

            elif tipo == 'PreguntaTextoMultiple':
                respuestas = RespuestaTextoMultiple.objects.filter(pregunta=pregunta)
                textos = [r.valor for r in respuestas]
                context['graficas'][key] = textos

            elif tipo == 'PreguntaTexto':
                respuestas = RespuestaTexto.objects.filter(pregunta=pregunta)
                textos = [r.valor for r in respuestas]
                context['graficas'][key] = textos

            elif tipo == 'PreguntaFecha':
                respuestas = RespuestaFecha.objects.filter(pregunta=pregunta)
                fechas = [r.valor.isoformat() for r in respuestas]
                counter = Counter(fechas)
                context['graficas'][key] = dict(counter)

            elif tipo == 'PreguntaMatriz':
                respuestas = RespuestaMatriz.objects.filter(pregunta=pregunta)
                datos = defaultdict(Counter)
                for r in respuestas:
                    datos[r.item.texto][r.valor] += 1
                context['graficas'][key] = {fila: dict(contador) for fila, contador in datos.items()}

        return context


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
    """Vista para responder una encuesta"""
    encuesta = get_object_or_404(Encuesta, slug=slug)
    
    # Obtener todos los tipos de preguntas hijos
    tipos_preguntas = [cls.__name__.lower() for cls in PreguntaBase.__subclasses__()]
    
    # Recoger todas las preguntas de todos los tipos
    preguntas = []
    for tipo in tipos_preguntas:
        preguntas.extend(getattr(encuesta, f'{tipo}_relacionadas').all())
    
    # Ordenar las preguntas según el campo 'orden'
    preguntas_ordenadas = sorted(preguntas, key=lambda x: x.orden)
    
    # 1. Crear lista de secciones en el orden de aparición (incluyendo duplicados)
    secciones_con_duplicados = [p.seccion or 'General' for p in preguntas_ordenadas]
    
    # 2. Eliminar duplicados manteniendo el orden
    secciones_unicas = []
    seen = set()
    for seccion in secciones_con_duplicados:
        if seccion not in seen:
            seen.add(seccion)
            secciones_unicas.append(seccion)
    
    # 3. Agrupar preguntas por sección (opcional, según lo que necesites)
    preguntas_por_seccion = {}
    for seccion in secciones_unicas:
        preguntas_por_seccion[seccion] = [p for p in preguntas_ordenadas if (p.seccion or 'General') == seccion]
    
    return render(request, 'encuesta/responder_encuesta.html', {
        'encuesta': encuesta,
        'preguntas': preguntas_ordenadas,
        'secciones_unicas': secciones_unicas,  # Lista de secciones en orden de aparición sin duplicados
        'preguntas_por_seccion': preguntas_por_seccion  # Diccionario opcional con preguntas agrupadas
    })

def encuesta_completada(request, slug):
    """Vista de agradecimiento después de completar una encuesta"""
    encuesta = get_object_or_404(Encuesta, slug=slug)
    return render(request, 'Encuesta/encuesta_completada.html', {
        'encuesta': encuesta
    })
    
