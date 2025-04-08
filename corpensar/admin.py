from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    Encuesta, PreguntaTexto, PreguntaTextoMultiple, PreguntaOpcionMultiple, 
    OpcionMultiple, PreguntaCasillasVerificacion, OpcionCasillaVerificacion, 
    PreguntaMenuDesplegable, OpcionMenuDesplegable, PreguntaEstrellas, 
    PreguntaEscala, PreguntaMatriz, ItemMatrizPregunta, PreguntaFecha, 
    RespuestaEncuesta, RespuestaTexto, RespuestaOpcionMultiple, 
    RespuestaCasillasVerificacion, RespuestaEstrellas, RespuestaEscala, 
    RespuestaMatriz, RespuestaFecha
)

class OpcionMultipleInline(admin.TabularInline):
    model = OpcionMultiple
    extra = 3
    fields = ('texto', 'valor', 'orden')

class OpcionCasillaVerificacionInline(admin.TabularInline):
    model = OpcionCasillaVerificacion
    extra = 3
    fields = ('texto', 'valor', 'orden')

class OpcionMenuDesplegableInline(admin.TabularInline):
    model = OpcionMenuDesplegable
    extra = 3
    fields = ('texto', 'valor', 'orden')

class ItemMatrizPreguntaInline(admin.TabularInline):
    model = ItemMatrizPregunta
    extra = 3
    fields = ('texto', 'orden')

class PreguntaTextoInline(admin.StackedInline):
    model = PreguntaTexto
    extra = 0
    fields = ('texto', 'tipo', 'requerida', 'orden', 'seccion', 'ayuda', 'max_longitud', 'placeholder')
    readonly_fields = ('tipo',)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields['tipo'].initial = 'TEXT'
        return formset

class PreguntaTextoMultipleInline(admin.StackedInline):
    model = PreguntaTextoMultiple
    extra = 0
    fields = ('texto', 'tipo', 'requerida', 'orden', 'seccion', 'ayuda', 'max_longitud', 'filas', 'placeholder')
    readonly_fields = ('tipo',)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields['tipo'].initial = 'MTEXT'
        return formset

class PreguntaOpcionMultipleInline(admin.StackedInline):
    model = PreguntaOpcionMultiple
    extra = 0
    fields = ('texto', 'tipo', 'requerida', 'orden', 'seccion', 'ayuda', 'opcion_otro', 'texto_otro')
    readonly_fields = ('tipo',)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields['tipo'].initial = 'RADIO'
        return formset

class PreguntaCasillasVerificacionInline(admin.StackedInline):
    model = PreguntaCasillasVerificacion
    extra = 0
    fields = ('texto', 'tipo', 'requerida', 'orden', 'seccion', 'ayuda', 'opcion_otro', 'texto_otro', 
              'min_selecciones', 'max_selecciones')
    readonly_fields = ('tipo',)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields['tipo'].initial = 'CHECK'
        return formset

class PreguntaMenuDesplegableInline(admin.StackedInline):
    model = PreguntaMenuDesplegable
    extra = 0
    fields = ('texto', 'tipo', 'requerida', 'orden', 'seccion', 'ayuda', 'opcion_vacia', 'texto_vacio')
    readonly_fields = ('tipo',)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields['tipo'].initial = 'SELECT'
        return formset

class PreguntaEstrellasInline(admin.StackedInline):
    model = PreguntaEstrellas
    extra = 0
    fields = ('texto', 'tipo', 'requerida', 'orden', 'seccion', 'ayuda', 'max_estrellas', 
              'etiqueta_inicio', 'etiqueta_fin')
    readonly_fields = ('tipo',)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields['tipo'].initial = 'STAR'
        return formset

class PreguntaEscalaInline(admin.StackedInline):
    model = PreguntaEscala
    extra = 0
    fields = ('texto', 'tipo', 'requerida', 'orden', 'seccion', 'ayuda', 'min_valor', 'max_valor', 
              'etiqueta_min', 'etiqueta_max', 'paso')
    readonly_fields = ('tipo',)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields['tipo'].initial = 'SCALE'
        return formset

class PreguntaMatrizInline(admin.StackedInline):
    model = PreguntaMatriz
    extra = 0
    fields = ('texto', 'tipo', 'requerida', 'orden', 'seccion', 'ayuda', 'escala')
    readonly_fields = ('tipo',)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields['tipo'].initial = 'MATRIX'
        return formset

class PreguntaFechaInline(admin.StackedInline):
    model = PreguntaFecha
    extra = 0
    fields = ('texto', 'tipo', 'requerida', 'orden', 'seccion', 'ayuda', 'incluir_hora')
    readonly_fields = ('tipo',)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields['tipo'].initial = 'DATE' if not obj or not obj.incluir_hora else 'DATETIME'
        return formset

@admin.register(Encuesta)
class EncuestaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'slug', 'fecha_inicio', 'fecha_fin', 'activa', 'es_publica')
    list_filter = ('activa', 'es_publica', 'fecha_creacion')
    search_fields = ('titulo', 'descripcion')
    prepopulated_fields = {'slug': ('titulo',)}
    date_hierarchy = 'fecha_creacion'
    fieldsets = (
        (None, {
            'fields': ('titulo', 'slug', 'descripcion', 'creador')
        }),
        (_('Configuración'), {
            'fields': ('fecha_inicio', 'fecha_fin', 'activa', 'es_publica')
        }),
    )
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

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.creador = request.user
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return ('creador',) + self.readonly_fields
        return self.readonly_fields


@admin.register(PreguntaOpcionMultiple)
class PreguntaOpcionMultipleAdmin(admin.ModelAdmin):
    list_display = ('texto', 'encuesta', 'requerida', 'orden')
    list_filter = ('encuesta', 'requerida')
    search_fields = ('texto', 'encuesta__titulo')
    inlines = [OpcionMultipleInline]


@admin.register(PreguntaCasillasVerificacion)
class PreguntaCasillasVerificacionAdmin(admin.ModelAdmin):
    list_display = ('texto', 'encuesta', 'requerida', 'orden', 'min_selecciones', 'max_selecciones')
    list_filter = ('encuesta', 'requerida')
    search_fields = ('texto', 'encuesta__titulo')
    inlines = [OpcionCasillaVerificacionInline]


@admin.register(PreguntaMenuDesplegable)
class PreguntaMenuDesplegableAdmin(admin.ModelAdmin):
    list_display = ('texto', 'encuesta', 'requerida', 'orden')
    list_filter = ('encuesta', 'requerida')
    search_fields = ('texto', 'encuesta__titulo')
    inlines = [OpcionMenuDesplegableInline]


@admin.register(PreguntaMatriz)
class PreguntaMatrizAdmin(admin.ModelAdmin):
    list_display = ('texto', 'encuesta', 'requerida', 'orden', 'escala')
    list_filter = ('encuesta', 'requerida')
    search_fields = ('texto', 'encuesta__titulo')
    inlines = [ItemMatrizPreguntaInline]


@admin.register(PreguntaEscala)
class PreguntaEscalaAdmin(admin.ModelAdmin):
    list_display = ('texto', 'encuesta', 'requerida', 'orden', 'min_valor', 'max_valor')
    list_filter = ('encuesta', 'requerida')
    search_fields = ('texto', 'encuesta__titulo')


class RespuestaTextoInline(admin.TabularInline):
    model = RespuestaTexto
    extra = 0
    readonly_fields = ('pregunta', 'valor')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class RespuestaOpcionMultipleInline(admin.TabularInline):
    model = RespuestaOpcionMultiple
    extra = 0
    readonly_fields = ('pregunta', 'opcion', 'texto_otro')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class RespuestaCasillasVerificacionInline(admin.TabularInline):
    model = RespuestaCasillasVerificacion
    extra = 0
    readonly_fields = ('pregunta', 'opcion', 'texto_otro')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class RespuestaEstrellasInline(admin.TabularInline):
    model = RespuestaEstrellas
    extra = 0
    readonly_fields = ('pregunta', 'valor')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class RespuestaEscalaInline(admin.TabularInline):
    model = RespuestaEscala
    extra = 0
    readonly_fields = ('pregunta', 'valor')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class RespuestaMatrizInline(admin.TabularInline):
    model = RespuestaMatriz
    extra = 0
    readonly_fields = ('pregunta', 'item', 'valor')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class RespuestaFechaInline(admin.TabularInline):
    model = RespuestaFecha
    extra = 0
    readonly_fields = ('pregunta', 'valor')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(RespuestaEncuesta)
class RespuestaEncuestaAdmin(admin.ModelAdmin):
    list_display = ('encuesta', 'usuario', 'fecha_respuesta', 'completada', 'ip_address')
    list_filter = ('encuesta', 'completada', 'fecha_respuesta')
    search_fields = ('encuesta__titulo', 'usuario__username', 'usuario__email', 'ip_address')
    readonly_fields = ('encuesta', 'usuario', 'fecha_respuesta', 'ip_address', 'user_agent', 'completada')
    
    inlines = [
        RespuestaTextoInline,
        RespuestaOpcionMultipleInline,
        RespuestaCasillasVerificacionInline,
        RespuestaEstrellasInline,
        RespuestaEscalaInline,
        RespuestaMatrizInline,
        RespuestaFechaInline,
    ]

    def has_add_permission(self, request):
        return False


# Registrar el resto de modelos
admin.site.register(PreguntaTexto)
admin.site.register(PreguntaTextoMultiple)
admin.site.register(PreguntaEstrellas)
admin.site.register(PreguntaFecha)