from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django import forms
from smart_selects.db_fields import ChainedForeignKey
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.utils.timezone import now
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
import os
from datetime import timedelta
from django.utils import timezone

# Esta línea ya no es necesaria porque importamos User directamente
# User = get_user_model()

# Se aplica para categorizar si un formulario es una encuesta, entrevista, etc.
class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self):
        return self.nombre

class Region(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Región"
        verbose_name_plural = "Regiones"

    def __str__(self):
        return self.nombre

class Municipio(models.Model):
    nombre = models.CharField(max_length=100)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name="municipios")
    latitud = models.FloatField(null=True, blank=True)
    longitud = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = "Municipio"
        verbose_name_plural = "Municipios"

    def __str__(self):
        return self.nombre

def get_valores_rango(self):
    return range(self.min_valor, self.max_valor + 1)

class GrupoInteres(models.Model):
    """Grupo de interés para encuestas (comunidades, autoridades locales, trabajadores, líderes, proveedores)"""
    nombre = models.CharField(max_length=100, verbose_name=_("Nombre"))
    descripcion = models.TextField(blank=True, verbose_name=_("Descripción"))
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name=_("Fecha de creación"))
    
    class Meta:
        verbose_name = _("Grupo de interés")
        verbose_name_plural = _("Grupos de interés")
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre

class Encuesta(models.Model):
    """Modelo principal que representa una encuesta completa"""
    TEMAS = (
        ('default', _('Tema por defecto')),
        ('azul', _('Tema Azul')),
        ('verde', _('Tema Verde')),
        ('rojo', _('Tema Rojo')),
        ('morado', _('Tema Morado')),
        ('naranja', _('Tema Naranja')),
        ('turquesa', _('Tema Turquesa')),
        ('rosa', _('Tema Rosa')),
        ('esmeralda', _('Tema Esmeralda')),
        ('indigo', _('Tema Índigo')),
        ('cielo', _('Tema Cielo')),
        ('coral', _('Tema Coral')),
    )
    
    TIPOS_FONDO = (
        ('color', _('Color sólido')),
        ('gradiente', _('Gradiente')),
        ('imagen', _('Imagen')),
        ('patron', _('Patrón')),
    )
    
    ESTILOS_FUENTE = (
        ('default', _('Por defecto')),
        ('serif', _('Serif')),
        ('sans-serif', _('Sans-serif')),
        ('monospace', _('Monospace')),
    )
    
    TAMANOS_FUENTE = (
        ('normal', _('Normal')),
        ('grande', _('Grande')),
        ('pequeno', _('Pequeño')),
    )
    
    ESTILOS_BORDE = (
        ('redondeado', _('Redondeado')),
        ('cuadrado', _('Cuadrado')),
        ('suave', _('Suave')),
    )
    
    # Estructura de una encuesta (datos basicos)
    titulo = models.CharField(max_length=200, verbose_name=_("Título"))
    descripcion = models.TextField(blank=True, verbose_name=_("Descripción"))
    slug = models.SlugField(max_length=250, unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name=_("Fecha de creación"))
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name=_("Fecha de actualización"))
    fecha_inicio = models.DateTimeField(verbose_name=_("Fecha de inicio"))
    fecha_fin = models.DateTimeField(verbose_name=_("Fecha de finalización"))
    activa = models.BooleanField(default=True, verbose_name=_("Activa"))
    creador = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Creador"))
    es_publica = models.BooleanField(default=False, verbose_name=_("Es pública"))
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Región")
    tema = models.CharField(max_length=20, choices=TEMAS, default='default', verbose_name=_("Tema"))
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Categoría")
    subcategoria = models.ForeignKey('Subcategoria', on_delete=models.SET_NULL, null=True, blank=True, 
                                    verbose_name="Subcategoría")
    municipio = models.ForeignKey(
        Municipio, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Municipio"
    )
    grupo_interes = models.ForeignKey(GrupoInteres, null=True, blank=True, on_delete=models.SET_NULL,
                                    verbose_name=_("Grupo de interés"))
    
    # Campos para personalización del diseño
    imagen_encabezado = models.ImageField(upload_to='encuestas/encabezados/', null=True, blank=True, verbose_name=_("Imagen de encabezado"))
    logotipo = models.ImageField(upload_to='encuestas/logos/', null=True, blank=True, verbose_name=_("Logotipo"))
    mostrar_logo = models.BooleanField(default=True, verbose_name=_("Mostrar logotipo"))
    
    tipo_fondo = models.CharField(max_length=20, choices=TIPOS_FONDO, default='color', verbose_name=_("Tipo de fondo"))
    color_fondo = models.CharField(max_length=20, default='#f0f2f5', verbose_name=_("Color de fondo"))
    color_gradiente_1 = models.CharField(max_length=20, default='#4361ee', verbose_name=_("Color 1 del gradiente"))
    color_gradiente_2 = models.CharField(max_length=20, default='#3a0ca3', verbose_name=_("Color 2 del gradiente"))
    imagen_fondo = models.ImageField(upload_to='encuestas/fondos/', null=True, blank=True, verbose_name=_("Imagen de fondo"))
    patron_fondo = models.CharField(max_length=20, default='patron1', verbose_name=_("Patrón de fondo"))
    
    estilo_fuente = models.CharField(max_length=20, choices=ESTILOS_FUENTE, default='default', verbose_name=_("Estilo de fuente"))
    tamano_fuente = models.CharField(max_length=20, choices=TAMANOS_FUENTE, default='normal', verbose_name=_("Tamaño de fuente"))
    estilo_bordes = models.CharField(max_length=20, choices=ESTILOS_BORDE, default='redondeado', verbose_name=_("Estilo de bordes"))

    class Meta:
        verbose_name = _("Encuesta")
        verbose_name_plural = _("Encuestas")
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return self.titulo
    
    def obtener_preguntas(self):
        """
        Obtiene todas las preguntas de la encuesta y las devuelve 
        como una lista ordenada por orden
        """
        from itertools import chain
        
        # Obtener todas las preguntas relacionadas con esta encuesta como listas
        preguntas = list(chain(
            self.preguntatexto_relacionadas.all(),
            self.preguntatextomultiple_relacionadas.all(),
            self.preguntaopcionmultiple_relacionadas.all(),
            self.preguntacasillasverificacion_relacionadas.all(),
            self.preguntamenudesplegable_relacionadas.all(),
            self.preguntaestrellas_relacionadas.all(),
            self.preguntaescala_relacionadas.all(),
            self.preguntamatriz_relacionadas.all(),
            self.preguntafecha_relacionadas.all()
        ))
        
        # Ordenar las preguntas por el atributo orden y devolverlas como lista
        return sorted(preguntas, key=lambda p: p.orden)

class PreguntaBase(models.Model):
    """Modelo abstracto base para todas las preguntas"""
    TIPOS_PREGUNTA = (
        ('TEXT', _('Texto simple')),
        ('MTEXT', _('Texto múltiple')),
        ('RADIO', _('Opción múltiple')),
        ('CHECK', _('Casillas de verificación')),
        ('SELECT', _('Menú desplegable')),
        ('STAR', _('Valoración con estrellas')),
        ('SCALE', _('Escala mejor/peor')),
        ('MATRIX', _('Matriz de valoración')),
        ('DATE', _('Fecha')),
        ('DATETIME', _('Fecha y hora')),
    )
    
    encuesta = models.ForeignKey(
        Encuesta, 
        on_delete=models.CASCADE, 
        verbose_name=_("Encuesta"),
        related_name='%(class)s_relacionadas'  # Esto hará que cada subclase tenga su propio related_name
    )
    texto = models.TextField(verbose_name=_("Texto de la pregunta"))
    tipo = models.CharField(max_length=10, choices=TIPOS_PREGUNTA, verbose_name=_("Tipo de pregunta"))
    requerida = models.BooleanField(default=False, verbose_name=_("Requerida"))
    orden = models.PositiveIntegerField(verbose_name=_("Orden"))
    ayuda = models.CharField(max_length=300, blank=True, verbose_name=_("Texto de ayuda"))
    seccion = models.CharField(max_length=100, blank=True, verbose_name=_("Sección"))
    permitir_archivos = models.BooleanField(default=False, verbose_name=_("Permitir adjuntar archivos como evidencia"))
    
    class Meta:
        abstract = True
        ordering = ['orden']
    
    def __str__(self):
        return f"{self.texto[:50]}... ({self.get_tipo_display()})"
    

class PreguntaTexto(PreguntaBase):
    """Pregunta de texto simple"""
    max_longitud = models.PositiveIntegerField(default=250, verbose_name=_("Longitud máxima"))
    placeholder = models.CharField(max_length=100, blank=True, verbose_name=_("Texto de ejemplo"))
    
    class Meta:
        verbose_name = _("Pregunta de texto")
        verbose_name_plural = _("Preguntas de texto")


class PreguntaTextoMultiple(PreguntaBase):
    """Pregunta de texto multilínea"""
    max_longitud = models.PositiveIntegerField(default=1000, verbose_name=_("Longitud máxima"))
    filas = models.PositiveIntegerField(default=4, verbose_name=_("Número de filas"))
    placeholder = models.CharField(max_length=100, blank=True, verbose_name=_("Texto de ejemplo"))
    
    class Meta:
        verbose_name = _("Pregunta de texto múltiple")
        verbose_name_plural = _("Preguntas de texto múltiple")


class OpcionPregunta(models.Model):
    """Opciones para preguntas de selección"""
    texto = models.CharField(max_length=200, verbose_name=_("Texto de la opción"))
    valor = models.CharField(max_length=100, verbose_name=_("Valor de la opción"))
    orden = models.PositiveIntegerField(verbose_name=_("Orden"))
    
    class Meta:
        abstract = True
        ordering = ['orden']
    
    def __str__(self):
        return self.texto


class OpcionMultiple(OpcionPregunta):
    """Opciones para preguntas de opción múltiple"""
    pregunta = models.ForeignKey('PreguntaOpcionMultiple', related_name='opciones', on_delete=models.CASCADE, verbose_name=_("Pregunta"))


class PreguntaOpcionMultiple(PreguntaBase):
    """Pregunta de opción múltiple (radio buttons)"""
    opcion_otro = models.BooleanField(default=False, verbose_name=_("Incluir opción 'Otro'"))
    texto_otro = models.CharField(max_length=100, blank=True, default=_("Otro"), verbose_name=_("Texto para 'Otro'"))
    
    class Meta:
        verbose_name = _("Pregunta de opción múltiple")
        verbose_name_plural = _("Preguntas de opción múltiple")


class OpcionCasillaVerificacion(OpcionPregunta):
    """Opciones para preguntas de casillas de verificación"""
    pregunta = models.ForeignKey('PreguntaCasillasVerificacion', related_name='opciones', 
                               on_delete=models.CASCADE, verbose_name=_("Pregunta"))


class PreguntaCasillasVerificacion(PreguntaBase):
    """Pregunta de casillas de verificación (múltiple selección)"""
    opcion_otro = models.BooleanField(default=False, verbose_name=_("Incluir opción 'Otro'"))
    texto_otro = models.CharField(max_length=100, blank=True, default=_("Otro"), verbose_name=_("Texto para 'Otro'"))
    min_selecciones = models.PositiveIntegerField(default=1, verbose_name=_("Mínimo de selecciones"))
    max_selecciones = models.PositiveIntegerField(default=None, null=True, blank=True, 
                                                verbose_name=_("Máximo de selecciones"))
    
    class Meta:
        verbose_name = _("Pregunta de casillas de verificación")
        verbose_name_plural = _("Preguntas de casillas de verificación")


class OpcionMenuDesplegable(OpcionPregunta):
    """Opciones para preguntas de menú desplegable"""
    pregunta = models.ForeignKey('PreguntaMenuDesplegable', related_name='opciones', 
                               on_delete=models.CASCADE, verbose_name=_("Pregunta"))


class PreguntaMenuDesplegable(PreguntaBase):
    """Pregunta con menú desplegable"""
    opcion_vacia = models.BooleanField(default=True, verbose_name=_("Incluir opción vacía"))
    texto_vacio = models.CharField(max_length=100, blank=True, default=_("Seleccione..."), 
                                 verbose_name=_("Texto para opción vacía"))
    
    class Meta:
        verbose_name = _("Pregunta de menú desplegable")
        verbose_name_plural = _("Preguntas de menú desplegable")


class PreguntaEstrellas(PreguntaBase):
    """Pregunta de valoración con estrellas"""
    max_estrellas = models.PositiveIntegerField(default=5, verbose_name=_("Número máximo de estrellas"))
    etiqueta_inicio = models.CharField(max_length=50, blank=True, verbose_name=_("Etiqueta para valor mínimo"))
    etiqueta_fin = models.CharField(max_length=50, blank=True, verbose_name=_("Etiqueta para valor máximo"))
    
    class Meta:
        verbose_name = _("Pregunta de valoración con estrellas")
        verbose_name_plural = _("Preguntas de valoración con estrellas")


class PreguntaEscala(PreguntaBase):
    """Pregunta de escala (mejor/peor)"""
    min_valor = models.IntegerField(default=1, verbose_name=_("Valor mínimo"))
    max_valor = models.IntegerField(default=5, verbose_name=_("Valor máximo"))
    etiqueta_min = models.CharField(max_length=50, verbose_name=_("Etiqueta para valor mínimo"))
    etiqueta_max = models.CharField(max_length=50, verbose_name=_("Etiqueta para valor máximo"))
    paso = models.IntegerField(default=1, verbose_name=_("Paso de incremento"))
    
    class Meta:
        verbose_name = _("Pregunta de escala")
        verbose_name_plural = _("Preguntas de escala")


class ItemMatriz(models.Model):
    """Ítems para preguntas tipo matriz"""
    texto = models.CharField(max_length=200, verbose_name=_("Texto del ítem"))
    orden = models.PositiveIntegerField(verbose_name=_("Orden"))
    
    class Meta:
        abstract = True
        ordering = ['orden']
    
    def __str__(self):
        return self.texto


class ItemMatrizPregunta(ItemMatriz):
    """Ítems para preguntas tipo matriz"""
    pregunta = models.ForeignKey('PreguntaMatriz', related_name='items', 
                                on_delete=models.CASCADE, verbose_name=_("Pregunta matriz"))


class PreguntaMatriz(PreguntaBase):
    """Pregunta tipo matriz de valoración"""
    escala = models.ForeignKey(PreguntaEscala, on_delete=models.CASCADE, verbose_name=_("Escala a utilizar"))
    
    class Meta:
        verbose_name = _("Pregunta de matriz")
        verbose_name_plural = _("Preguntas de matriz")


class PreguntaFecha(PreguntaBase):
    """Pregunta de fecha"""
    incluir_hora = models.BooleanField(default=False, verbose_name=_("Incluir hora"))
    
    class Meta:
        verbose_name = _("Pregunta de fecha/hora")
        verbose_name_plural = _("Preguntas de fecha/hora")


class RespuestaEncuesta(models.Model):
    """Registro completo de una respuesta a encuesta"""
    encuesta = models.ForeignKey(Encuesta, related_name='respuestas', on_delete=models.CASCADE, verbose_name=_("Encuesta"))
    usuario = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("Usuario"))
    municipio = models.ForeignKey(Municipio, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("Municipio"))
    fecha_respuesta = models.DateTimeField(auto_now_add=True, verbose_name=_("Fecha de respuesta"))
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_("Dirección IP"))
    user_agent = models.TextField(null=True, blank=True, verbose_name=_("User Agent"))
    completada = models.BooleanField(default=False, verbose_name=_("Completada"))
    
    class Meta:
        verbose_name = _("Respuesta de encuesta")
        verbose_name_plural = _("Respuestas de encuestas")
        ordering = ['-fecha_respuesta']
    
    def __str__(self):
        return f"Respuesta a {self.encuesta.titulo}"


class RespuestaBase(models.Model):
    """Modelo base abstracto para todas las respuestas"""
    respuesta_encuesta = models.ForeignKey(RespuestaEncuesta, related_name='%(class)s_relacionadas', 
                                        on_delete=models.CASCADE)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        abstract = True
    
    def __str__(self):
        return f"Respuesta a pregunta en {self.respuesta_encuesta}"


class RespuestaTexto(RespuestaBase):
    """Respuesta para preguntas de texto"""
    pregunta = models.ForeignKey(PreguntaTexto, on_delete=models.CASCADE)
    valor = models.TextField()
    
    class Meta:
        verbose_name = _("Respuesta de texto")
        verbose_name_plural = _("Respuestas de texto")


class RespuestaOpcionMultiple(RespuestaBase):
    """Respuesta para preguntas de opción múltiple"""
    pregunta = models.ForeignKey(PreguntaOpcionMultiple, on_delete=models.CASCADE)
    opcion = models.ForeignKey(OpcionMultiple, on_delete=models.CASCADE)
    texto_otro = models.TextField(blank=True)
    
    class Meta:
        verbose_name = _("Respuesta de opción múltiple")
        verbose_name_plural = _("Respuestas de opción múltiple")


class RespuestaCasillasVerificacion(RespuestaBase):
    """Respuesta para preguntas de casillas de verificación"""
    pregunta = models.ForeignKey(PreguntaCasillasVerificacion, on_delete=models.CASCADE)
    opcion = models.ForeignKey(OpcionCasillaVerificacion, on_delete=models.CASCADE)
    texto_otro = models.TextField(blank=True)
    
    class Meta:
        verbose_name = _("Respuesta de casillas de verificación")
        verbose_name_plural = _("Respuestas de casillas de verificación")


class RespuestaEstrellas(RespuestaBase):
    """Respuesta para preguntas de estrellas"""
    pregunta = models.ForeignKey(PreguntaEstrellas, on_delete=models.CASCADE)
    valor = models.PositiveIntegerField()
    
    class Meta:
        verbose_name = _("Respuesta de estrellas")
        verbose_name_plural = _("Respuestas de estrellas")


class RespuestaEscala(RespuestaBase):
    """Respuesta para preguntas de escala"""
    pregunta = models.ForeignKey(PreguntaEscala, on_delete=models.CASCADE)
    valor = models.IntegerField()
    
    class Meta:
        verbose_name = _("Respuesta de escala")
        verbose_name_plural = _("Respuestas de escala")


class RespuestaMatriz(RespuestaBase):
    """Respuesta para preguntas de matriz"""
    pregunta = models.ForeignKey(PreguntaMatriz, on_delete=models.CASCADE)
    item = models.ForeignKey(ItemMatrizPregunta, on_delete=models.CASCADE)
    valor = models.IntegerField()
    
    class Meta:
        verbose_name = _("Respuesta de matriz")
        verbose_name_plural = _("Respuestas de matriz")


class RespuestaFecha(RespuestaBase):
    """Respuesta para preguntas de fecha/hora"""
    pregunta = models.ForeignKey(PreguntaFecha, on_delete=models.CASCADE)
    valor = models.DateTimeField()
    
    class Meta:
        verbose_name = _("Respuesta de fecha/hora")
        verbose_name_plural = _("Respuestas de fecha/hora")
        
class RespuestaTextoMultiple(RespuestaBase):
    pregunta = models.ForeignKey(PreguntaTextoMultiple, on_delete=models.CASCADE)
    valor = models.TextField()

    class Meta:
        verbose_name = _("Respuesta de texto múltiple")
        verbose_name_plural = _("Respuestas de texto múltiple")

class RespuestaOpcionMenuDesplegable(RespuestaBase):
    """Respuesta para preguntas de menú desplegable"""
    pregunta = models.ForeignKey(PreguntaMenuDesplegable, on_delete=models.CASCADE)
    opcion = models.ForeignKey(OpcionMenuDesplegable, on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Respuesta a menú desplegable")
        verbose_name_plural = _("Respuestas a menú desplegable")

class PQRSFD(models.Model):
    TIPO_CHOICES = [
        ('P', 'Petición'),
        ('Q', 'Queja'),
        ('R', 'Reclamo'),
        ('S', 'Sugerencia'),
        ('F', 'Felicitación'),
        ('D', 'Denuncia'),
    ]

    ESTADO_CHOICES = [
        ('P', 'Pendiente'),
        ('E', 'En Proceso'),
        ('R', 'Resuelto'),
        ('C', 'Cerrado'),
    ]

    # Tiempo de respuesta en días según la ley para cada tipo de PQRSFD
    TIEMPO_RESPUESTA = {
        'P': 15,  # Petición: 15 días hábiles
        'Q': 15,  # Queja: 15 días hábiles
        'R': 15,  # Reclamo: 15 días hábiles
        'S': 15,  # Sugerencia: 15 días hábiles
        'F': 15,  # Felicitación: 15 días hábiles
        'D': 15,  # Denuncia: 15 días hábiles
    }

    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES)
    nombre = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    asunto = models.CharField(max_length=200)
    descripcion = models.TextField()
    estado = models.CharField(max_length=1, choices=ESTADO_CHOICES, default='P')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    respuesta = models.TextField(blank=True, null=True)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)
    es_anonimo = models.BooleanField(default=False)
    notificado_email = models.BooleanField(default=False, verbose_name="Notificado por email")
    notificado_sms = models.BooleanField(default=False, verbose_name="Notificado por SMS")
    fecha_notificacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'PQRSFD'
        verbose_name_plural = 'PQRSFDs'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.asunto}"
        
    def get_tiempo_respuesta(self):
        """Retorna el tiempo de respuesta en días según el tipo de PQRSFD"""
        return self.TIEMPO_RESPUESTA.get(self.tipo, 15)
        
    def get_fecha_limite(self):
        """Calcula la fecha límite para responder"""
        if self.estado in ['R', 'C'] or self.fecha_respuesta:
            return None
        
        dias = self.get_tiempo_respuesta()
        return self.fecha_creacion + timedelta(days=dias)
        
    def get_dias_restantes(self):
        """Calcula los días restantes para responder"""
        if self.estado in ['R', 'C'] or self.fecha_respuesta:
            return 0
            
        fecha_limite = self.get_fecha_limite()
        if not fecha_limite:
            return 0
            
        dias_restantes = (fecha_limite - timezone.now()).days
        return max(0, dias_restantes)
        
    def get_porcentaje_tiempo(self):
        """Retorna el porcentaje de tiempo transcurrido"""
        if self.estado in ['R', 'C'] or self.fecha_respuesta:
            return 100
            
        tiempo_total = self.get_tiempo_respuesta()
        dias_transcurridos = (timezone.now() - self.fecha_creacion).days
        
        if dias_transcurridos >= tiempo_total:
            return 100
            
        return int((dias_transcurridos / tiempo_total) * 100)
        
    def esta_vencido(self):
        """Indica si el PQRSFD está vencido"""
        if self.estado in ['R', 'C'] or self.fecha_respuesta:
            return False
            
        return self.get_dias_restantes() <= 0

class ArchivoAdjuntoPQRSFD(models.Model):
    pqrsfd = models.ForeignKey(PQRSFD, on_delete=models.CASCADE, related_name='archivos_adjuntos')
    archivo = models.FileField(upload_to='pqrsfd/adjuntos/%Y/%m/')
    nombre_original = models.CharField(max_length=255)
    tipo_archivo = models.CharField(max_length=100)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Archivo adjunto PQRSFD'
        verbose_name_plural = 'Archivos adjuntos PQRSFD'

    def __str__(self):
        return f"Adjunto {self.nombre_original} - {self.pqrsfd}"

class Subcategoria(models.Model):
    """Modelo para las subcategorías (población, dirección de formulario, etc.)"""
    categoria = models.ForeignKey(
        Categoria, 
        on_delete=models.CASCADE, 
        related_name='subcategorias', 
        verbose_name=_("Categoría")
    )
    nombre = models.CharField(max_length=100, verbose_name=_("Nombre de la subcategoría"))
    descripcion = models.TextField(blank=True, verbose_name=_("Descripción"))
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name=_("Fecha de creación"))

    class Meta:
        verbose_name = _("Subcategoría")
        verbose_name_plural = _("Subcategorías")
        ordering = ['categoria', 'nombre']
        unique_together = ['categoria', 'nombre']  # Evitar duplicados en la misma categoría

    def __str__(self):
        return f"{self.categoria.nombre} - {self.nombre}"

    def clean(self):
        """Validación personalizada para el modelo"""
        # Verificar si ya existe una subcategoría con el mismo nombre en la misma categoría
        if Subcategoria.objects.filter(
            categoria=self.categoria,
            nombre__iexact=self.nombre
        ).exclude(id=self.id).exists():
            raise ValidationError(_("Ya existe una subcategoría con este nombre en la categoría seleccionada."))

class ArchivoRespuesta(models.Model):
    """Modelo para almacenar archivos adjuntos a las respuestas de las encuestas"""
    respuesta = models.ForeignKey(RespuestaEncuesta, on_delete=models.CASCADE, related_name='archivos_adjuntos')
    archivo = models.FileField(upload_to='respuestas/archivos/', verbose_name=_("Archivo adjunto"))
    nombre_original = models.CharField(max_length=255, verbose_name=_("Nombre original"))
    tipo_archivo = models.CharField(max_length=100, verbose_name=_("Tipo de archivo"))
    fecha_subida = models.DateTimeField(auto_now_add=True, verbose_name=_("Fecha de subida"))
    
    # Campos para asociar a la respuesta específica (a nivel de pregunta)
    pregunta_id = models.PositiveIntegerField(verbose_name=_("ID de pregunta"), null=True)
    tipo_pregunta = models.CharField(max_length=20, verbose_name=_("Tipo de pregunta"), null=True)
    
    class Meta:
        verbose_name = _("Archivo de respuesta")
        verbose_name_plural = _("Archivos de respuestas")
        
    def __str__(self):
        return f"Archivo para {self.respuesta} - {self.nombre_original}"
        
    def extension(self):
        """Devuelve la extensión del archivo"""
        return os.path.splitext(self.nombre_original)[1][1:].lower()

class ArchivoRespuestaPQRSFD(models.Model):
    """Archivos adjuntos para las respuestas a PQRSFD"""
    pqrsfd = models.ForeignKey(PQRSFD, on_delete=models.CASCADE, related_name='archivos_respuesta')
    archivo = models.FileField(upload_to='pqrsfd/respuestas/%Y/%m/')
    nombre_original = models.CharField(max_length=255)
    tipo_archivo = models.CharField(max_length=100)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Archivo respuesta PQRSFD'
        verbose_name_plural = 'Archivos respuesta PQRSFD'

    def __str__(self):
        return f"Archivo respuesta {self.nombre_original} - {self.pqrsfd}"

class CaracterizacionMunicipal(models.Model):
    """Modelo para almacenar la caracterización de municipios"""
    municipio = models.ForeignKey(Municipio, on_delete=models.CASCADE, related_name='caracterizaciones', verbose_name=_("Municipio"))
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name=_("Fecha de creación"))
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name=_("Fecha de actualización"))
    creador = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Creador"))
    
    
    # Territorio
    area_km2 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("Área (km²)"))
    concejos_comunitarios_ha = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("Consejos Comunitarios (OSPR) (ha)"))
    resguardos_indigenas_ha = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("Resguardos Indígenas (OSPR) (ha)"))
    zonas_reserva_campesina_ha = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("Zonas de Reserva Campesina (OSPR) (ha)"))
    zonas_reserva_sinap_ha = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("Zonas de Reserva (SINAP) (ha)"))
    es_municipio_pdei = models.BooleanField(default=False, verbose_name=_("Municipio PDEI"))
    
    # Datos demográficos
    poblacion_total = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("No. Habitantes"))
    
    # Datos demográficos - Hombres
    poblacion_hombres_total = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Hombres - Total"))
    poblacion_hombres_rural = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Hombres - Rural"))
    poblacion_hombres_urbana = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Hombres - Urbana"))
    
    # Datos demográficos - Mujeres
    poblacion_mujeres_total = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Mujeres - Total"))
    poblacion_mujeres_rural = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Mujeres - Rural"))
    poblacion_mujeres_urbana = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Mujeres - Urbana"))
    
    # Datos demográficos - Origen étnico
    poblacion_indigena = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Población Indígena"))
    poblacion_raizal = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Población Raizal"))
    poblacion_gitano_rrom = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Población Gitano(a)/Rrom"))
    poblacion_palenquero = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Población Palenquero(a) de San Basilio"))
    poblacion_negro_mulato_afrocolombiano = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Población Negro/Mulato/Afro"))
    
    # Datos demográficos - Población desplazada
    poblacion_desplazada = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Población Desplazada"))
    
    # Datos demográficos - Migrantes
    poblacion_migrantes = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Población Migrante"))
    
    # Indicadores Socioeconómicos
    necesidades_basicas_insatisfechas = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name=_("Necesidades Básicas Insatisfechas (%)"))
    proporcion_personas_miseria = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name=_("Proporción de personas en miseria (%)"))
    indice_pobreza_multidimensional = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name=_("Índice de pobreza multidimensional (%)"))
    analfabetismo = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name=_("Analfabetismo (%)"))
    bajo_logro_educativo = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name=_("Bajo logro educativo (%)"))
    inasistencia_escolar = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name=_("Inasistencia escolar (%)"))
    trabajo_informal = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name=_("Trabajo informal (%)"))
    desempleo_larga_duracion = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name=_("Desempleo de larga duración (%)"))
    trabajo_infantil = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name=_("Trabajo infantil (%)"))
    hacinamiento_critico = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name=_("Hacinamiento crítico (%)"))
    barreras_servicios_cuidado_primera_infancia = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name=_("Barreras a servicios cuidado primera infancia (%)"))
    barreras_acceso_servicios_salud = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name=_("Barreras acceso servicios salud (%)"))
    inadecuada_eliminacion_excretas = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name=_("Inadecuada eliminación de excretas (%)"))
    sin_acceso_fuente_agua_mejorada = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name=_("Sin acceso a fuente de agua mejorada (%)"))
    sin_aseguramiento_salud = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name=_("Sin aseguramiento en salud (%)"))
    
 
    
    # Campo para documentos o imágenes adicionales
    escudo = models.ImageField(upload_to='caracterizacion/escudos/', null=True, blank=True, verbose_name=_("Escudo"))
    bandera = models.ImageField(upload_to='caracterizacion/banderas/', null=True, blank=True, verbose_name=_("Bandera"))
    
    # Campos para notas adicionales
    observaciones = models.TextField(blank=True, verbose_name=_("Observaciones"))
    
    # Estado de la caracterización
    ESTADO_CHOICES = [
        ('borrador', _('Borrador')),
        ('publicado', _('Publicado')),
        ('archivado', _('Archivado')),
    ]
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador', verbose_name=_("Estado"))
    
    class Meta:
        verbose_name = _("Caracterización Municipal")
        verbose_name_plural = _("Caracterizaciones Municipales")
        ordering = ['-fecha_actualizacion']
        
    def __str__(self):
        return f"Caracterización de {self.municipio.nombre}"
    
    def get_absolute_url(self):
        return f"/caracterizacion/{self.id}/"
    
    def porcentaje_poblacion_urbana(self):
        if self.poblacion_total and self.poblacion_urbana:
            return (self.poblacion_urbana / self.poblacion_total) * 100
        return None
    
    def porcentaje_poblacion_rural(self):
        if self.poblacion_total and self.poblacion_rural:
            return (self.poblacion_rural / self.poblacion_total) * 100
        return None


class DocumentoCaracterizacion(models.Model):
    """Modelo para almacenar documentos adicionales de la caracterización"""
    caracterizacion = models.ForeignKey(CaracterizacionMunicipal, on_delete=models.CASCADE, 
                                        related_name='documentos', verbose_name=_("Caracterización"))
    titulo = models.CharField(max_length=200, verbose_name=_("Título"))
    descripcion = models.TextField(blank=True, verbose_name=_("Descripción"))
    archivo = models.FileField(upload_to='caracterizacion/documentos/', verbose_name=_("Archivo"))
    fecha_subida = models.DateTimeField(auto_now_add=True, verbose_name=_("Fecha de subida"))
    
    class Meta:
        verbose_name = _("Documento de Caracterización")
        verbose_name_plural = _("Documentos de Caracterización")
        ordering = ['-fecha_subida']
        
    def __str__(self):
        return self.titulo
    
    def extension(self):
        nombre, extension = os.path.splitext(self.archivo.name)
        return extension.lower()
