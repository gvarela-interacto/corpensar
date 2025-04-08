from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django import forms

User = get_user_model()

class Encuesta(models.Model):
    """Modelo principal que representa una encuesta completa"""
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
    
    class Meta:
        verbose_name = _("Encuesta")
        verbose_name_plural = _("Encuestas")
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return self.titulo


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
    requerida = models.BooleanField(default=True, verbose_name=_("Requerida"))
    orden = models.PositiveIntegerField(verbose_name=_("Orden"))
    ayuda = models.CharField(max_length=300, blank=True, verbose_name=_("Texto de ayuda"))
    seccion = models.CharField(max_length=100, blank=True, verbose_name=_("Sección"))
    
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
    pregunta = models.ForeignKey('PreguntaOpcionMultiple', related_name='opciones', 
                               on_delete=models.CASCADE, verbose_name=_("Pregunta"))


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