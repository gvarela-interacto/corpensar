from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Encuesta,
    PreguntaTexto, PreguntaTextoMultiple,
    PreguntaOpcionMultiple, OpcionMultiple,
    PreguntaCasillasVerificacion, OpcionCasillaVerificacion,
    PreguntaMenuDesplegable, OpcionMenuDesplegable,
    PreguntaEstrellas, PreguntaEscala,
    PreguntaMatriz, ItemMatrizPregunta,
    PreguntaFecha,
    RespuestaEncuesta,
    RespuestaTexto, RespuestaOpcionMultiple,
    RespuestaCasillasVerificacion, RespuestaEstrellas,
    RespuestaEscala, RespuestaMatriz, RespuestaFecha
)

# Clases inline para opciones de preguntas
class OpcionMultipleInline(admin.TabularInline):
    model = OpcionMultiple
    extra = 1
    fields = ['texto', 'valor', 'orden']
    ordering = ['orden']

class OpcionCasillaVerificacionInline(admin.TabularInline):
    model = OpcionCasillaVerificacion
    extra = 1
    fields = ['texto', 'valor', 'orden']
    ordering = ['orden']

class OpcionMenuDesplegableInline(admin.TabularInline):
    model = OpcionMenuDesplegable
    extra = 1
    fields = ['texto', 'valor', 'orden']
    ordering = ['orden']

class ItemMatrizInline(admin.TabularInline):
    model = ItemMatrizPregunta
    extra = 1
    fields = ['texto', 'orden']
    ordering = ['orden']

# Clases inline para respuestas
class RespuestaTextoInline(admin.TabularInline):
    model = RespuestaTexto
    extra = 0
    readonly_fields = ['fecha_creacion']
    fields = ['pregunta', 'valor', 'fecha_creacion']
    can_delete = False

class RespuestaOpcionMultipleInline(admin.TabularInline):
    model = RespuestaOpcionMultiple
    extra = 0
    readonly_fields = ['fecha_creacion']
    fields = ['pregunta', 'opcion', 'texto_otro', 'fecha_creacion']
    can_delete = False

class RespuestaCasillasVerificacionInline(admin.TabularInline):
    model = RespuestaCasillasVerificacion
    extra = 0
    readonly_fields = ['fecha_creacion']
    fields = ['pregunta', 'opcion', 'texto_otro', 'fecha_creacion']
    can_delete = False

class RespuestaEstrellasInline(admin.TabularInline):
    model = RespuestaEstrellas
    extra = 0
    readonly_fields = ['fecha_creacion']
    fields = ['pregunta', 'valor', 'fecha_creacion']
    can_delete = False

class RespuestaEscalaInline(admin.TabularInline):
    model = RespuestaEscala
    extra = 0
    readonly_fields = ['fecha_creacion']
    fields = ['pregunta', 'valor', 'fecha_creacion']
    can_delete = False

class RespuestaMatrizInline(admin.TabularInline):
    model = RespuestaMatriz
    extra = 0
    readonly_fields = ['fecha_creacion']
    fields = ['pregunta', 'item', 'valor', 'fecha_creacion']
    can_delete = False

class RespuestaFechaInline(admin.TabularInline):
    model = RespuestaFecha
    extra = 0
    readonly_fields = ['fecha_creacion']
    fields = ['pregunta', 'valor', 'fecha_creacion']
    can_delete = False

# Clases Admin para preguntas
@admin.register(PreguntaTexto)
class PreguntaTextoAdmin(admin.ModelAdmin):
    list_display = ['texto', 'encuesta', 'orden', 'requerida']
    list_filter = ['encuesta', 'requerida']
    search_fields = ['texto']
    ordering = ['encuesta', 'orden']
    fields = ['encuesta', 'texto', 'tipo', 'requerida', 'orden', 'ayuda', 'seccion',
              'max_longitud', 'placeholder']
    readonly_fields = ['tipo']

@admin.register(PreguntaTextoMultiple)
class PreguntaTextoMultipleAdmin(admin.ModelAdmin):
    list_display = ['texto', 'encuesta', 'orden', 'requerida']
    list_filter = ['encuesta', 'requerida']
    search_fields = ['texto']
    ordering = ['encuesta', 'orden']
    fields = ['encuesta', 'texto', 'tipo', 'requerida', 'orden', 'ayuda', 'seccion',
              'max_longitud', 'filas', 'placeholder']
    readonly_fields = ['tipo']

@admin.register(PreguntaOpcionMultiple)
class PreguntaOpcionMultipleAdmin(admin.ModelAdmin):
    list_display = ['texto', 'encuesta', 'orden', 'requerida', 'opcion_otro']
    list_filter = ['encuesta', 'requerida', 'opcion_otro']
    search_fields = ['texto']
    ordering = ['encuesta', 'orden']
    fields = ['encuesta', 'texto', 'tipo', 'requerida', 'orden', 'ayuda', 'seccion',
              'opcion_otro', 'texto_otro']
    readonly_fields = ['tipo']
    inlines = [OpcionMultipleInline]

@admin.register(PreguntaCasillasVerificacion)
class PreguntaCasillasVerificacionAdmin(admin.ModelAdmin):
    list_display = ['texto', 'encuesta', 'orden', 'requerida', 'opcion_otro', 'min_selecciones', 'max_selecciones']
    list_filter = ['encuesta', 'requerida', 'opcion_otro']
    search_fields = ['texto']
    ordering = ['encuesta', 'orden']
    fields = ['encuesta', 'texto', 'tipo', 'requerida', 'orden', 'ayuda', 'seccion',
              'opcion_otro', 'texto_otro', 'min_selecciones', 'max_selecciones']
    readonly_fields = ['tipo']
    inlines = [OpcionCasillaVerificacionInline]

@admin.register(PreguntaMenuDesplegable)
class PreguntaMenuDesplegableAdmin(admin.ModelAdmin):
    list_display = ['texto', 'encuesta', 'orden', 'requerida', 'opcion_vacia']
    list_filter = ['encuesta', 'requerida', 'opcion_vacia']
    search_fields = ['texto']
    ordering = ['encuesta', 'orden']
    fields = ['encuesta', 'texto', 'tipo', 'requerida', 'orden', 'ayuda', 'seccion',
              'opcion_vacia', 'texto_vacio']
    readonly_fields = ['tipo']
    inlines = [OpcionMenuDesplegableInline]

@admin.register(PreguntaEstrellas)
class PreguntaEstrellasAdmin(admin.ModelAdmin):
    list_display = ['texto', 'encuesta', 'orden', 'requerida', 'max_estrellas']
    list_filter = ['encuesta', 'requerida']
    search_fields = ['texto']
    ordering = ['encuesta', 'orden']
    fields = ['encuesta', 'texto', 'tipo', 'requerida', 'orden', 'ayuda', 'seccion',
              'max_estrellas', 'etiqueta_inicio', 'etiqueta_fin']
    readonly_fields = ['tipo']

@admin.register(PreguntaEscala)
class PreguntaEscalaAdmin(admin.ModelAdmin):
    list_display = ['texto', 'encuesta', 'orden', 'requerida', 'min_valor', 'max_valor']
    list_filter = ['encuesta', 'requerida']
    search_fields = ['texto']
    ordering = ['encuesta', 'orden']
    fields = ['encuesta', 'texto', 'tipo', 'requerida', 'orden', 'ayuda', 'seccion',
              'min_valor', 'max_valor', 'etiqueta_min', 'etiqueta_max', 'paso']
    readonly_fields = ['tipo']

@admin.register(PreguntaMatriz)
class PreguntaMatrizAdmin(admin.ModelAdmin):
    list_display = ['texto', 'encuesta', 'orden', 'requerida', 'escala']
    list_filter = ['encuesta', 'requerida', 'escala']
    search_fields = ['texto']
    ordering = ['encuesta', 'orden']
    fields = ['encuesta', 'texto', 'tipo', 'requerida', 'orden', 'ayuda', 'seccion', 'escala']
    readonly_fields = ['tipo']
    inlines = [ItemMatrizInline]

@admin.register(PreguntaFecha)
class PreguntaFechaAdmin(admin.ModelAdmin):
    list_display = ['texto', 'encuesta', 'orden', 'requerida', 'incluir_hora']
    list_filter = ['encuesta', 'requerida', 'incluir_hora']
    search_fields = ['texto']
    ordering = ['encuesta', 'orden']
    fields = ['encuesta', 'texto', 'tipo', 'requerida', 'orden', 'ayuda', 'seccion',
              'incluir_hora']
    readonly_fields = ['tipo']

# Clase Admin para Encuesta con todas las preguntas relacionadas
class PreguntaTextoInline(admin.StackedInline):
    model = PreguntaTexto
    extra = 0
    fields = ['texto', 'orden', 'requerida', 'ayuda', 'max_longitud']
    readonly_fields = ['tipo']
    show_change_link = True

class PreguntaTextoMultipleInline(admin.StackedInline):
    model = PreguntaTextoMultiple
    extra = 0
    fields = ['texto', 'orden', 'requerida', 'ayuda', 'max_longitud', 'filas']
    readonly_fields = ['tipo']
    show_change_link = True

class PreguntaOpcionMultipleInline(admin.StackedInline):
    model = PreguntaOpcionMultiple
    extra = 0
    fields = ['texto', 'orden', 'requerida', 'ayuda', 'opcion_otro']
    readonly_fields = ['tipo']
    show_change_link = True

class PreguntaCasillasVerificacionInline(admin.StackedInline):
    model = PreguntaCasillasVerificacion
    extra = 0
    fields = ['texto', 'orden', 'requerida', 'ayuda', 'opcion_otro', 'min_selecciones', 'max_selecciones']
    readonly_fields = ['tipo']
    show_change_link = True

class PreguntaMenuDesplegableInline(admin.StackedInline):
    model = PreguntaMenuDesplegable
    extra = 0
    fields = ['texto', 'orden', 'requerida', 'ayuda', 'opcion_vacia']
    readonly_fields = ['tipo']
    show_change_link = True

class PreguntaEstrellasInline(admin.StackedInline):
    model = PreguntaEstrellas
    extra = 0
    fields = ['texto', 'orden', 'requerida', 'ayuda', 'max_estrellas']
    readonly_fields = ['tipo']
    show_change_link = True

class PreguntaEscalaInline(admin.StackedInline):
    model = PreguntaEscala
    extra = 0
    fields = ['texto', 'orden', 'requerida', 'ayuda', 'min_valor', 'max_valor']
    readonly_fields = ['tipo']
    show_change_link = True

class PreguntaMatrizInline(admin.StackedInline):
    model = PreguntaMatriz
    extra = 0
    fields = ['texto', 'orden', 'requerida', 'ayuda', 'escala']
    readonly_fields = ['tipo']
    show_change_link = True

class PreguntaFechaInline(admin.StackedInline):
    model = PreguntaFecha
    extra = 0
    fields = ['texto', 'orden', 'requerida', 'ayuda', 'incluir_hora']
    readonly_fields = ['tipo']
    show_change_link = True

@admin.register(Encuesta)
class EncuestaAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'creador', 'fecha_creacion', 'fecha_inicio', 'fecha_fin', 'activa', 'es_publica', 'total_preguntas']
    list_filter = ['activa', 'es_publica', 'creador', 'fecha_creacion']
    search_fields = ['titulo', 'descripcion']
    ordering = ['-fecha_creacion']
    fieldsets = (
        (None, {
            'fields': ('titulo', 'descripcion', 'creador', 'slug')
        }),
        ('Fechas', {
            'fields': ('fecha_inicio', 'fecha_fin'),
            'classes': ('collapse',)
        }),
        ('Configuración', {
            'fields': ('activa', 'es_publica'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['slug', 'fecha_creacion', 'fecha_actualizacion']
    inlines = [
        PreguntaTextoInline,
        PreguntaTextoMultipleInline,
        PreguntaOpcionMultipleInline,
        PreguntaCasillasVerificacionInline,
        PreguntaMenuDesplegableInline,
        PreguntaEstrellasInline,
        PreguntaEscalaInline,
        PreguntaMatrizInline,
        PreguntaFechaInline,
    ]
    
    def total_preguntas(self, obj):
        total = 0
        total += obj.preguntatexto_relacionadas.count()
        total += obj.preguntatextomultiple_relacionadas.count()
        total += obj.preguntaopcionmultiple_relacionadas.count()
        total += obj.preguntacasillasverificacion_relacionadas.count()
        total += obj.preguntamenudesplegable_relacionadas.count()
        total += obj.preguntaestrellas_relacionadas.count()
        total += obj.preguntaescala_relacionadas.count()
        total += obj.preguntamatriz_relacionadas.count()
        total += obj.preguntafecha_relacionadas.count()
        return total
    total_preguntas.short_description = 'Total Preguntas'

# Clase Admin para RespuestaEncuesta con todas las respuestas
@admin.register(RespuestaEncuesta)
class RespuestaEncuestaAdmin(admin.ModelAdmin):
    list_display = ['encuesta', 'usuario', 'fecha_respuesta', 'completada', 'ip_address']
    list_filter = ['encuesta', 'completada', 'fecha_respuesta']
    search_fields = ['encuesta__titulo', 'usuario__username']
    ordering = ['-fecha_respuesta']
    readonly_fields = ['fecha_respuesta', 'ip_address', 'user_agent']
    inlines = [
        RespuestaTextoInline,
        RespuestaOpcionMultipleInline,
        RespuestaCasillasVerificacionInline,
        RespuestaEstrellasInline,
        RespuestaEscalaInline,
        RespuestaMatrizInline,
        RespuestaFechaInline,
    ]
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ['encuesta', 'usuario']
        return self.readonly_fields

# Admin para modelos de opciones (solo lectura)
@admin.register(OpcionMultiple)
class OpcionMultipleAdmin(admin.ModelAdmin):
    list_display = ['texto', 'valor', 'orden', 'pregunta']
    list_filter = ['pregunta__encuesta']
    search_fields = ['texto', 'valor']
    ordering = ['pregunta', 'orden']
    readonly_fields = ['pregunta']

@admin.register(OpcionCasillaVerificacion)
class OpcionCasillaVerificacionAdmin(admin.ModelAdmin):
    list_display = ['texto', 'valor', 'orden', 'pregunta']
    list_filter = ['pregunta__encuesta']
    search_fields = ['texto', 'valor']
    ordering = ['pregunta', 'orden']
    readonly_fields = ['pregunta']

@admin.register(OpcionMenuDesplegable)
class OpcionMenuDesplegableAdmin(admin.ModelAdmin):
    list_display = ['texto', 'valor', 'orden', 'pregunta']
    list_filter = ['pregunta__encuesta']
    search_fields = ['texto', 'valor']
    ordering = ['pregunta', 'orden']
    readonly_fields = ['pregunta']

@admin.register(ItemMatrizPregunta)
class ItemMatrizPreguntaAdmin(admin.ModelAdmin):
    list_display = ['texto', 'orden', 'pregunta']
    list_filter = ['pregunta__encuesta']
    search_fields = ['texto']
    ordering = ['pregunta', 'orden']
    readonly_fields = ['pregunta']

# Personalización del sitio admin
admin.site.site_header = "Administración de Encuestas"
admin.site.site_title = "Sistema de Encuestas"
admin.site.index_title = "Bienvenido al panel de administración"