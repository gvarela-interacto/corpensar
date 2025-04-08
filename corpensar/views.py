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



from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.forms import modelform_factory, formset_factory, Form
from django import forms


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
    # Obtener la encuesta o devolver 404
    encuesta = get_object_or_404(Encuesta, slug=slug)
    
    # Verificar si la encuesta está activa y en su periodo de validez
    ahora = timezone.now()
    if not encuesta.activa or encuesta.fecha_inicio > ahora or encuesta.fecha_fin < ahora:
        messages.error(request, "Esta encuesta no está disponible en este momento.")
        return redirect('inicio')  # Redirigir a la página de inicio o a un listado de encuestas
    
    # Si no es pública, verificar que el usuario esté autenticado
    if not encuesta.es_publica and not request.user.is_authenticated:
        messages.error(request, "Debes iniciar sesión para acceder a esta encuesta.")
        return redirect('login')  # Redirigir a la página de login
    
    # Obtener todas las preguntas organizadas por tipo y ordenadas
    preguntas = {}
    
    preguntas['texto'] = PreguntaTexto.objects.filter(encuesta=encuesta).order_by('orden')
    preguntas['texto_multiple'] = PreguntaTextoMultiple.objects.filter(encuesta=encuesta).order_by('orden')
    preguntas['opcion_multiple'] = PreguntaOpcionMultiple.objects.filter(encuesta=encuesta).order_by('orden')
    preguntas['casillas'] = PreguntaCasillasVerificacion.objects.filter(encuesta=encuesta).order_by('orden')
    preguntas['menu'] = PreguntaMenuDesplegable.objects.filter(encuesta=encuesta).order_by('orden')
    preguntas['estrellas'] = PreguntaEstrellas.objects.filter(encuesta=encuesta).order_by('orden')
    preguntas['escala'] = PreguntaEscala.objects.filter(encuesta=encuesta).order_by('orden')
    preguntas['matriz'] = PreguntaMatriz.objects.filter(encuesta=encuesta).order_by('orden')
    preguntas['fecha'] = PreguntaFecha.objects.filter(encuesta=encuesta).order_by('orden')
    
    # Crear diccionario para almacenar los formularios
    formularios = {}
    
    # Manejar envío del formulario
    if request.method == 'POST':
        formularios_validos = True
        
        # Validar todos los formularios
        for tipo, lista_preguntas in preguntas.items():
            formularios[tipo] = {}
            for pregunta in lista_preguntas:
                if tipo == 'texto':
                    form = TextoForm(request.POST, prefix=f'texto_{pregunta.id}', pregunta=pregunta, requerida=pregunta.requerida)
                elif tipo == 'texto_multiple':
                    form = TextoMultipleForm(request.POST, prefix=f'texto_multiple_{pregunta.id}', pregunta=pregunta, requerida=pregunta.requerida)
                elif tipo == 'opcion_multiple':
                    form = OpcionMultipleForm(request.POST, prefix=f'opcion_multiple_{pregunta.id}', pregunta=pregunta, requerida=pregunta.requerida)
                elif tipo == 'casillas':
                    form = CasillasVerificacionForm(request.POST, prefix=f'casillas_{pregunta.id}', pregunta=pregunta, requerida=pregunta.requerida)
                elif tipo == 'menu':
                    form = MenuDesplegableForm(request.POST, prefix=f'menu_{pregunta.id}', pregunta=pregunta, requerida=pregunta.requerida)
                elif tipo == 'estrellas':
                    form = EstrellasForm(request.POST, prefix=f'estrellas_{pregunta.id}', pregunta=pregunta, requerida=pregunta.requerida)
                elif tipo == 'escala':
                    form = EscalaForm(request.POST, prefix=f'escala_{pregunta.id}', pregunta=pregunta, requerida=pregunta.requerida)
                elif tipo == 'matriz':
                    form = MatrizForm(request.POST, prefix=f'matriz_{pregunta.id}', pregunta=pregunta, requerida=pregunta.requerida)
                elif tipo == 'fecha':
                    form = FechaForm(request.POST, prefix=f'fecha_{pregunta.id}', pregunta=pregunta, requerida=pregunta.requerida)
                
                formularios[tipo][pregunta.id] = form
                
                if not form.is_valid():
                    formularios_validos = False
        
        # Si todos los formularios son válidos, guardar la respuesta
        if formularios_validos:
            # Crear registro de respuesta de encuesta
            respuesta_encuesta = RespuestaEncuesta.objects.create(
                encuesta=encuesta,
                usuario=request.user if request.user.is_authenticated else None,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                completada=True
            )
            
            # Guardar respuestas individuales
            for tipo, dict_formularios in formularios.items():
                for pregunta_id, form in dict_formularios.items():
                    if tipo == 'texto':
                        pregunta = PreguntaTexto.objects.get(id=pregunta_id)
                        if form.cleaned_data['respuesta']:
                            RespuestaTexto.objects.create(
                                respuesta_encuesta=respuesta_encuesta,
                                pregunta=pregunta,
                                valor=form.cleaned_data['respuesta']
                            )
                    
                    elif tipo == 'texto_multiple':
                        pregunta = PreguntaTextoMultiple.objects.get(id=pregunta_id)
                        if form.cleaned_data['respuesta']:
                            RespuestaTexto.objects.create(
                                respuesta_encuesta=respuesta_encuesta,
                                pregunta=pregunta,
                                valor=form.cleaned_data['respuesta']
                            )
                    
                    elif tipo == 'opcion_multiple':
                        pregunta = PreguntaOpcionMultiple.objects.get(id=pregunta_id)
                        if form.cleaned_data['opcion']:
                            RespuestaOpcionMultiple.objects.create(
                                respuesta_encuesta=respuesta_encuesta,
                                pregunta=pregunta,
                                opcion=form.cleaned_data['opcion'],
                                texto_otro=form.cleaned_data.get('texto_otro', '')
                            )
                    
                    elif tipo == 'casillas':
                        pregunta = PreguntaCasillasVerificacion.objects.get(id=pregunta_id)
                        for opcion in form.cleaned_data['opciones']:
                            RespuestaCasillasVerificacion.objects.create(
                                respuesta_encuesta=respuesta_encuesta,
                                pregunta=pregunta,
                                opcion=opcion,
                                texto_otro=form.cleaned_data.get('texto_otro', '')
                            )
                    
                    elif tipo == 'menu':
                        pregunta = PreguntaMenuDesplegable.objects.get(id=pregunta_id)
                        if form.cleaned_data['opcion']:
                            RespuestaOpcionMultiple.objects.create(
                                respuesta_encuesta=respuesta_encuesta,
                                pregunta=pregunta,
                                opcion=form.cleaned_data['opcion']
                            )
                    
                    elif tipo == 'estrellas':
                        pregunta = PreguntaEstrellas.objects.get(id=pregunta_id)
                        if form.cleaned_data['valor']:
                            RespuestaEstrellas.objects.create(
                                respuesta_encuesta=respuesta_encuesta,
                                pregunta=pregunta,
                                valor=form.cleaned_data['valor']
                            )
                    
                    elif tipo == 'escala':
                        pregunta = PreguntaEscala.objects.get(id=pregunta_id)
                        if form.cleaned_data['valor']:
                            RespuestaEscala.objects.create(
                                respuesta_encuesta=respuesta_encuesta,
                                pregunta=pregunta,
                                valor=form.cleaned_data['valor']
                            )
                    
                    elif tipo == 'matriz':
                        pregunta = PreguntaMatriz.objects.get(id=pregunta_id)
                        for item in pregunta.items.all():
                            field_name = f"item_{item.id}"
                            if field_name in form.cleaned_data and form.cleaned_data[field_name]:
                                RespuestaMatriz.objects.create(
                                    respuesta_encuesta=respuesta_encuesta,
                                    pregunta=pregunta,
                                    item=item,
                                    valor=form.cleaned_data[field_name]
                                )
                    
                    elif tipo == 'fecha':
                        pregunta = PreguntaFecha.objects.get(id=pregunta_id)
                        if form.cleaned_data['valor']:
                            RespuestaFecha.objects.create(
                                respuesta_encuesta=respuesta_encuesta,
                                pregunta=pregunta,
                                valor=form.cleaned_data['valor']
                            )
            
            messages.success(request, "¡Gracias por completar la encuesta!")
            return redirect('encuesta_completada', slug=encuesta.slug)
    
    else:
        # Inicializar formularios vacíos
        for tipo, lista_preguntas in preguntas.items():
            formularios[tipo] = {}
            for pregunta in lista_preguntas:
                if tipo == 'texto':
                    form = TextoForm(prefix=f'texto_{pregunta.id}', pregunta=pregunta, requerida=pregunta.requerida)
                elif tipo == 'texto_multiple':
                    form = TextoMultipleForm(prefix=f'texto_multiple_{pregunta.id}', pregunta=pregunta, requerida=pregunta.requerida)
                elif tipo == 'opcion_multiple':
                    form = OpcionMultipleForm(prefix=f'opcion_multiple_{pregunta.id}', pregunta=pregunta, requerida=pregunta.requerida)
                elif tipo == 'casillas':
                    form = CasillasVerificacionForm(prefix=f'casillas_{pregunta.id}', pregunta=pregunta, requerida=pregunta.requerida)
                elif tipo == 'menu':
                    form = MenuDesplegableForm(prefix=f'menu_{pregunta.id}', pregunta=pregunta, requerida=pregunta.requerida)
                elif tipo == 'estrellas':
                    form = EstrellasForm(prefix=f'estrellas_{pregunta.id}', pregunta=pregunta, requerida=pregunta.requerida)
                elif tipo == 'escala':
                    form = EscalaForm(prefix=f'escala_{pregunta.id}', pregunta=pregunta, requerida=pregunta.requerida)
                elif tipo == 'matriz':
                    form = MatrizForm(prefix=f'matriz_{pregunta.id}', pregunta=pregunta, requerida=pregunta.requerida)
                elif tipo == 'fecha':
                    form = FechaForm(prefix=f'fecha_{pregunta.id}', pregunta=pregunta, requerida=pregunta.requerida)
                
                formularios[tipo][pregunta.id] = form
    
    # Crear una lista unificada de secciones para ordenar las preguntas
    secciones = []
    todas_preguntas = []
    
    # Recopilar todas las preguntas con sus formularios
    for tipo, dict_formularios in formularios.items():
        for pregunta_id, form in dict_formularios.items():
            if tipo == 'texto':
                pregunta = PreguntaTexto.objects.get(id=pregunta_id)
            elif tipo == 'texto_multiple':
                pregunta = PreguntaTextoMultiple.objects.get(id=pregunta_id)
            elif tipo == 'opcion_multiple':
                pregunta = PreguntaOpcionMultiple.objects.get(id=pregunta_id)
            elif tipo == 'casillas':
                pregunta = PreguntaCasillasVerificacion.objects.get(id=pregunta_id)
            elif tipo == 'menu':
                pregunta = PreguntaMenuDesplegable.objects.get(id=pregunta_id)
            elif tipo == 'estrellas':
                pregunta = PreguntaEstrellas.objects.get(id=pregunta_id)
            elif tipo == 'escala':
                pregunta = PreguntaEscala.objects.get(id=pregunta_id)
            elif tipo == 'matriz':
                pregunta = PreguntaMatriz.objects.get(id=pregunta_id)
            elif tipo == 'fecha':
                pregunta = PreguntaFecha.objects.get(id=pregunta_id)
            
            todas_preguntas.append({
                'pregunta': pregunta,
                'formulario': form,
                'tipo': tipo,
                'seccion': pregunta.seccion
            })
            
            if pregunta.seccion and pregunta.seccion not in secciones:
                secciones.append(pregunta.seccion)
    
    # Ordenar las preguntas por sección y orden
    todas_preguntas.sort(key=lambda x: (x['seccion'] if x['seccion'] else '', x['pregunta'].orden))
    
    return render(request, 'encuestas/responder_encuesta.html', {
        'encuesta': encuesta,
        'todas_preguntas': todas_preguntas,
        'secciones': secciones
    })


def encuesta_completada(request, slug):
    """Vista de agradecimiento después de completar una encuesta"""
    encuesta = get_object_or_404(Encuesta, slug=slug)
    return render(request, 'encuestas/encuesta_completada.html', {
        'encuesta': encuesta
    })