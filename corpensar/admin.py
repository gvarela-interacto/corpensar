from django.contrib import admin
from django.contrib.admin import TabularInline, StackedInline
from django import forms
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import path
from django.utils.safestring import mark_safe
from django.db.models import F
from .models import (
    Encuesta, PreguntaTexto, PreguntaTextoMultiple, PreguntaOpcionMultiple,
    OpcionMultiple, PreguntaCasillasVerificacion, OpcionCasillaVerificacion,
    PreguntaMenuDesplegable, OpcionMenuDesplegable, PreguntaEstrellas,
    PreguntaEscala, PreguntaMatriz, ItemMatrizPregunta, PreguntaFecha,
    RespuestaEncuesta, RespuestaTexto, RespuestaTextoMultiple, RespuestaOpcionMultiple,
    RespuestaCasillasVerificacion, RespuestaEstrellas, RespuestaEscala,
    RespuestaMatriz, RespuestaFecha, Region, Municipio, PQRSFD,
    Subcategoria, ArchivoRespuestaPQRSFD, ArchivoAdjuntoPQRSFD, GrupoInteres,
    DocumentoCaracterizacion, CaracterizacionMunicipal, Categoria
)


# Inline para mostrar municipios dentro de Region
class MunicipioInline(admin.TabularInline):
    model = Municipio
    extra = 1
    show_change_link = True



@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('nombre',)

    def has_module_permission(self, request):
        """Oculta el módulo del listado general"""
        return False

    def has_change_permission(self, request, obj=None):
        """No permitir editar"""
        return False

    def has_delete_permission(self, request, obj=None):
        """No permitir eliminar"""
        return False

    def has_view_permission(self, request, obj=None):
        """No mostrar listado"""
        return False


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'region')

    def has_module_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return False
# Inlines para las opciones de preguntas
class OpcionMultipleInline(TabularInline):
    model = OpcionMultiple
    extra = 1
    min_num = 2
    fields = ['texto', 'valor', 'orden']

class OpcionCasillaVerificacionInline(TabularInline):
    model = OpcionCasillaVerificacion
    extra = 1
    min_num = 2
    fields = ['texto', 'valor', 'orden']

class OpcionMenuDesplegableInline(TabularInline):
    model = OpcionMenuDesplegable
    extra = 1
    min_num = 2
    fields = ['texto', 'valor', 'orden']

class ItemMatrizPreguntaInline(TabularInline):
    model = ItemMatrizPregunta
    extra = 1
    min_num = 1
    fields = ['texto', 'orden']

# Formularios personalizados para preguntas
class PreguntaOpcionMultipleForm(forms.ModelForm):
    class Meta:
        model = PreguntaOpcionMultiple
        fields = '__all__'
        widgets = {
            'texto': forms.Textarea(attrs={'rows': 2}),
            'ayuda': forms.TextInput(),
        }

class PreguntaCasillasVerificacionForm(forms.ModelForm):
    class Meta:
        model = PreguntaCasillasVerificacion
        fields = '__all__'
        widgets = {
            'texto': forms.Textarea(attrs={'rows': 2}),
            'ayuda': forms.TextInput(),
        }

class PreguntaMenuDesplegableForm(forms.ModelForm):
    class Meta:
        model = PreguntaMenuDesplegable
        fields = '__all__'
        widgets = {
            'texto': forms.Textarea(attrs={'rows': 2}),
            'ayuda': forms.TextInput(),
        }

class PreguntaMatrizForm(forms.ModelForm):
    class Meta:
        model = PreguntaMatriz
        fields = '__all__'
        widgets = {
            'texto': forms.Textarea(attrs={'rows': 2}),
            'ayuda': forms.TextInput(),
        }

# ModelAdmins para los diferentes tipos de preguntas
class PreguntaTextoAdmin(admin.ModelAdmin):
    list_display = ['texto', 'encuesta', 'orden', 'requerida']
    list_filter = ['encuesta']
    search_fields = ['texto']
    fieldsets = (
        (None, {
            'fields': ('encuesta', 'orden', 'texto', 'ayuda', 'seccion')
        }),
        ('Configuración', {
            'fields': ('tipo', 'requerida', 'max_longitud', 'placeholder')
        }),
    )

class PreguntaTextoMultipleAdmin(admin.ModelAdmin):
    list_display = ['texto', 'encuesta', 'orden', 'requerida']
    list_filter = ['encuesta']
    search_fields = ['texto']
    fieldsets = (
        (None, {
            'fields': ('encuesta', 'orden', 'texto', 'ayuda', 'seccion')
        }),
        ('Configuración', {
            'fields': ('tipo', 'requerida', 'max_longitud', 'filas', 'placeholder')
        }),
    )

class PreguntaOpcionMultipleAdmin(admin.ModelAdmin):
    form = PreguntaOpcionMultipleForm
    list_display = ['texto', 'encuesta', 'orden', 'requerida']
    list_filter = ['encuesta']
    search_fields = ['texto']
    inlines = [OpcionMultipleInline]
    fieldsets = (
        (None, {
            'fields': ('encuesta', 'orden', 'texto', 'ayuda', 'seccion')
        }),
        ('Configuración', {
            'fields': ('tipo', 'requerida', 'opcion_otro', 'texto_otro')
        }),
    )

class PreguntaCasillasVerificacionAdmin(admin.ModelAdmin):
    form = PreguntaCasillasVerificacionForm
    list_display = ['texto', 'encuesta', 'orden', 'requerida']
    list_filter = ['encuesta']
    search_fields = ['texto']
    inlines = [OpcionCasillaVerificacionInline]
    fieldsets = (
        (None, {
            'fields': ('encuesta', 'orden', 'texto', 'ayuda', 'seccion')
        }),
        ('Configuración', {
            'fields': ('tipo', 'requerida', 'opcion_otro', 'texto_otro', 
                      'min_selecciones', 'max_selecciones')
        }),
    )

class PreguntaMenuDesplegableAdmin(admin.ModelAdmin):
    form = PreguntaMenuDesplegableForm
    list_display = ['texto', 'encuesta', 'orden', 'requerida']
    list_filter = ['encuesta']
    search_fields = ['texto']
    inlines = [OpcionMenuDesplegableInline]
    fieldsets = (
        (None, {
            'fields': ('encuesta', 'orden', 'texto', 'ayuda', 'seccion')
        }),
        ('Configuración', {
            'fields': ('tipo', 'requerida', 'opcion_vacia', 'texto_vacio')
        }),
    )

class PreguntaEstrellasAdmin(admin.ModelAdmin):
    list_display = ['texto', 'encuesta', 'orden', 'requerida', 'max_estrellas']
    list_filter = ['encuesta']
    search_fields = ['texto']
    fieldsets = (
        (None, {
            'fields': ('encuesta', 'orden', 'texto', 'ayuda', 'seccion')
        }),
        ('Configuración', {
            'fields': ('tipo', 'requerida', 'max_estrellas', 'etiqueta_inicio', 'etiqueta_fin')
        }),
    )

class PreguntaEscalaAdmin(admin.ModelAdmin):
    list_display = ['texto', 'encuesta', 'orden', 'requerida']
    list_filter = ['encuesta']
    search_fields = ['texto']
    fieldsets = (
        (None, {
            'fields': ('encuesta', 'orden', 'texto', 'ayuda', 'seccion')
        }),
        ('Configuración', {
            'fields': ('tipo', 'requerida', 'min_valor', 'max_valor', 
                      'etiqueta_min', 'etiqueta_max', 'paso')
        }),
    )

class PreguntaMatrizAdmin(admin.ModelAdmin):
    form = PreguntaMatrizForm
    list_display = ['texto', 'encuesta', 'orden', 'requerida']
    list_filter = ['encuesta']
    search_fields = ['texto']
    inlines = [ItemMatrizPreguntaInline]
    fieldsets = (
        (None, {
            'fields': ('encuesta', 'orden', 'texto', 'ayuda', 'seccion')
        }),
        ('Configuración', {
            'fields': ('tipo', 'requerida', 'escala')
        }),
    )

class PreguntaFechaAdmin(admin.ModelAdmin):
    list_display = ['texto', 'encuesta', 'orden', 'requerida', 'incluir_hora']
    list_filter = ['encuesta', 'incluir_hora']
    search_fields = ['texto']
    fieldsets = (
        (None, {
            'fields': ('encuesta', 'orden', 'texto', 'ayuda', 'seccion')
        }),
        ('Configuración', {
            'fields': ('tipo', 'requerida', 'incluir_hora')
        }),
    )

# Inline para mostrar todas las preguntas relacionadas en la encuesta
class PreguntaTextoInline(StackedInline):
    model = PreguntaTexto
    extra = 0
    fields = ['orden', 'texto', 'requerida', 'max_longitud', 'placeholder']
    verbose_name = "Pregunta de Texto"
    verbose_name_plural = "Preguntas de Texto"

class PreguntaTextoMultipleInline(StackedInline):
    model = PreguntaTextoMultiple
    extra = 0
    fields = ['orden', 'texto', 'requerida', 'max_longitud', 'filas', 'placeholder']
    verbose_name = "Pregunta de Texto Múltiple"
    verbose_name_plural = "Preguntas de Texto Múltiple"

class PreguntaOpcionMultipleInline(StackedInline):
    model = PreguntaOpcionMultiple
    extra = 0
    fields = ['orden', 'texto', 'requerida', 'opcion_otro', 'texto_otro']
    verbose_name = "Pregunta de Opción Múltiple"
    verbose_name_plural = "Preguntas de Opción Múltiple"
    inlines = [OpcionMultipleInline]

class PreguntaCasillasVerificacionInline(StackedInline):
    model = PreguntaCasillasVerificacion
    extra = 0
    fields = ['orden', 'texto', 'requerida', 'opcion_otro', 'texto_otro', 
              'min_selecciones', 'max_selecciones']
    verbose_name = "Pregunta de Casillas de Verificación"
    verbose_name_plural = "Preguntas de Casillas de Verificación"
    inlines = [OpcionCasillaVerificacionInline]

class PreguntaMenuDesplegableInline(StackedInline):
    model = PreguntaMenuDesplegable
    extra = 0
    fields = ['orden', 'texto', 'requerida', 'opcion_vacia', 'texto_vacio']
    verbose_name = "Pregunta de Menú Desplegable"
    verbose_name_plural = "Preguntas de Menú Desplegable"
    inlines = [OpcionMenuDesplegableInline]

class PreguntaEstrellasInline(StackedInline):
    model = PreguntaEstrellas
    extra = 0
    fields = ['orden', 'texto', 'requerida', 'max_estrellas', 'etiqueta_inicio', 'etiqueta_fin']
    verbose_name = "Pregunta de Estrellas"
    verbose_name_plural = "Preguntas de Estrellas"

class PreguntaEscalaInline(StackedInline):
    model = PreguntaEscala
    extra = 0
    fields = ['orden', 'texto', 'requerida', 'min_valor', 'max_valor', 
              'etiqueta_min', 'etiqueta_max', 'paso']
    verbose_name = "Pregunta de Escala"
    verbose_name_plural = "Preguntas de Escala"

class PreguntaMatrizInline(StackedInline):
    model = PreguntaMatriz
    extra = 0
    fields = ['orden', 'texto', 'requerida', 'escala']
    verbose_name = "Pregunta de Matriz"
    verbose_name_plural = "Preguntas de Matriz"
    inlines = [ItemMatrizPreguntaInline]

class PreguntaFechaInline(StackedInline):
    model = PreguntaFecha
    extra = 0
    fields = ['orden', 'texto', 'requerida', 'incluir_hora']
    verbose_name = "Pregunta de Fecha/Hora"
    verbose_name_plural = "Preguntas de Fecha/Hora"

# Registro de GrupoInteres
class GrupoInteresAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'descripcion', 'fecha_creacion']
    search_fields = ['nombre', 'descripcion']
    list_per_page = 20
    # Comentamos el date_hierarchy para evitar problemas con zonas horarias
    # date_hierarchy = 'fecha_creacion'

admin.site.register(GrupoInteres, GrupoInteresAdmin)

# Admin principal para Encuesta
class EncuestaAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'creador', 'region', 'categoria', 'grupo_interes', 'fecha_creacion', 'fecha_inicio', 'fecha_fin', 'activa', 'es_publica', 'tema']
    list_filter = ['activa', 'es_publica', 'region', 'categoria', 'grupo_interes', 'creador', 'fecha_creacion', 'tema']
    search_fields = ['titulo', 'descripcion', 'creador__username']
    list_per_page = 20
    prepopulated_fields = {'slug': ('titulo',)}
    filter_horizontal = []
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']
    # Comentamos el date_hierarchy para evitar problemas con zonas horarias
    # date_hierarchy = 'fecha_creacion'
    list_editable = ['activa', 'es_publica']
    
    fieldsets = (
        (None, {
            'fields': ('titulo', 'slug', 'descripcion', 'creador')
        }),
        ('Clasificación', {
            'fields': ('region', 'categoria', 'grupo_interes')
        }),
        ('Fechas', {
            'fields': ('fecha_inicio', 'fecha_fin', 'fecha_creacion', 'fecha_actualizacion')
        }),
        ('Configuración', {
            'fields': ('activa', 'es_publica', 'tema', 'tamano_fuente', 'estilo_bordes')
        }),
    )
    
    # Todos los inlines de preguntas
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
    
    def get_inline_instances(self, request, obj=None):
        """Mostrar solo inlines cuando se edita una encuesta existente"""
        if obj:
            return super().get_inline_instances(request, obj)
        return []

# Admins para respuestas
class RespuestaTextoInline(TabularInline):
    model = RespuestaTexto
    extra = 0
    readonly_fields = ['pregunta', 'valor']

class RespuestaOpcionMultipleInline(TabularInline):
    model = RespuestaOpcionMultiple
    extra = 0
    readonly_fields = ['pregunta', 'opcion', 'texto_otro']

class RespuestaCasillasVerificacionInline(TabularInline):
    model = RespuestaCasillasVerificacion
    extra = 0
    readonly_fields = ['pregunta', 'opcion', 'texto_otro']

class RespuestaEstrellasInline(TabularInline):
    model = RespuestaEstrellas
    extra = 0
    readonly_fields = ['pregunta', 'valor']

class RespuestaEscalaInline(TabularInline):
    model = RespuestaEscala
    extra = 0
    readonly_fields = ['pregunta', 'valor']

class RespuestaMatrizInline(TabularInline):
    model = RespuestaMatriz
    extra = 0
    readonly_fields = ['pregunta', 'item', 'valor']

class RespuestaFechaInline(TabularInline):
    model = RespuestaFecha
    extra = 0
    readonly_fields = ['pregunta', 'valor']

class RespuestaEncuestaAdmin(admin.ModelAdmin):
    list_display = ['encuesta', 'usuario', 'fecha_respuesta', 'completada']
    list_filter = ['encuesta', 'completada', 'fecha_respuesta']
    search_fields = ['encuesta__titulo', 'usuario__username']
    readonly_fields = ['fecha_respuesta', 'ip_address', 'user_agent']
    
    # Todos los inlines de respuestas
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
        return False  # No permitir añadir respuestas manualmente

# Registro de todos los modelos en el admin
admin.site.register(Encuesta, EncuestaAdmin)
admin.site.register(PreguntaTexto, PreguntaTextoAdmin)
admin.site.register(PreguntaTextoMultiple, PreguntaTextoMultipleAdmin)
admin.site.register(PreguntaOpcionMultiple, PreguntaOpcionMultipleAdmin)
admin.site.register(PreguntaCasillasVerificacion, PreguntaCasillasVerificacionAdmin)
admin.site.register(PreguntaMenuDesplegable, PreguntaMenuDesplegableAdmin)
admin.site.register(PreguntaEstrellas, PreguntaEstrellasAdmin)
admin.site.register(PreguntaEscala, PreguntaEscalaAdmin)
admin.site.register(PreguntaMatriz, PreguntaMatrizAdmin)
admin.site.register(PreguntaFecha, PreguntaFechaAdmin)
admin.site.register(RespuestaEncuesta, RespuestaEncuestaAdmin)

@admin.register(PQRSFD)
class PQRSFDAdmin(admin.ModelAdmin):
    list_display = ['asunto', 'tipo', 'estado', 'fecha_creacion', 'es_anonimo', 'dias_restantes', 'notificado']
    list_filter = ['tipo', 'estado', 'fecha_creacion', 'es_anonimo', 'notificado_email', 'notificado_sms']
    search_fields = ['asunto', 'descripcion', 'nombre', 'email', 'telefono']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion', 'fecha_notificacion']
    fieldsets = (
        (None, {
            'fields': ('tipo', 'asunto', 'descripcion', 'estado')
        }),
        ('Información de contacto', {
            'fields': ('nombre', 'email', 'telefono', 'es_anonimo')
        }),
        ('Respuesta', {
            'fields': ('respuesta', 'fecha_respuesta')
        }),
        ('Notificaciones', {
            'fields': ('notificado_email', 'notificado_sms', 'fecha_notificacion')
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_actualizacion')
        }),
    )
    
    def dias_restantes(self, obj):
        if obj.estado in ['R', 'C']:
            return "Completado"
        elif obj.esta_vencido():
            return format_html('<span style="color: red; font-weight: bold;">Vencido</span>')
        else:
            dias = obj.get_dias_restantes()
            color = "green"
            if dias < 3:
                color = "red"
            elif dias < 7:
                color = "orange"
            return format_html('<span style="color: {}; font-weight: bold;">{} días</span>', color, dias)
    
    dias_restantes.short_description = "Tiempo Restante"
    
    def notificado(self, obj):
        if obj.es_anonimo:
            return "Anónimo"
        elif obj.notificado_email and obj.notificado_sms:
            return format_html('<span style="color: green;">Email y SMS</span>')
        elif obj.notificado_email:
            return format_html('<span style="color: blue;">Email</span>')
        elif obj.notificado_sms:
            return format_html('<span style="color: purple;">SMS</span>')
        else:
            return format_html('<span style="color: gray;">No</span>')
    
    notificado.short_description = "Notificado"

@admin.register(ArchivoRespuestaPQRSFD)
class ArchivoRespuestaPQRSFDAdmin(admin.ModelAdmin):
    list_display = ['pqrsfd', 'nombre_original', 'tipo_archivo', 'fecha_subida']
    list_filter = ['tipo_archivo', 'fecha_subida']
    search_fields = ['nombre_original', 'pqrsfd__asunto']
    readonly_fields = ['fecha_subida']

class DocumentoCaracterizacionInline(admin.TabularInline):
    model = DocumentoCaracterizacion
    extra = 1

@admin.register(CaracterizacionMunicipal)
class CaracterizacionMunicipalAdmin(admin.ModelAdmin):
    list_display = ('municipio', 'fecha_actualizacion', 'estado', 'creador')
    list_filter = ('estado', 'municipio__region', 'fecha_creacion')
    search_fields = ('municipio__nombre',)
    # Comentamos el date_hierarchy que está causando el error de zona horaria
    # date_hierarchy = 'fecha_creacion'
    inlines = [DocumentoCaracterizacionInline]
    fieldsets = (
        ('Información General', {
            'fields': ('municipio', 'creador', 'estado')
        }),
        ('Territorio', {
            'fields': ('area_km2', 'concejos_comunitarios_ha', 'resguardos_indigenas_ha', 
                      'zonas_reserva_campesina_ha', 'zonas_reserva_sinap_ha', 'es_municipio_pdei')
        }),
        ('Datos Demográficos - General', {
            'fields': ('poblacion_total',)
        }),
        ('Datos Demográficos - Hombres', {
            'fields': ('poblacion_hombres_total', 'poblacion_hombres_rural', 'poblacion_hombres_urbana')
        }),
        ('Datos Demográficos - Mujeres', {
            'fields': ('poblacion_mujeres_total', 'poblacion_mujeres_rural', 'poblacion_mujeres_urbana')
        }),
        ('Datos Demográficos - Origen Étnico', {
            'fields': ('poblacion_indigena', 'poblacion_raizal', 'poblacion_gitano_rrom', 'poblacion_palenquero', 
                      'poblacion_negro_mulato_afrocolombiano')
        }),
        ('Datos Demográficos - Desplazados y Migrantes', {
            'fields': ('poblacion_desplazada', 'poblacion_migrantes')
        }),
        ('Indicadores Socioeconómicos - Pobreza', {
            'fields': ('necesidades_basicas_insatisfechas', 'proporcion_personas_miseria', 
                      'indice_pobreza_multidimensional')
        }),
        ('Indicadores Socioeconómicos - Educación', {
            'fields': ('analfabetismo', 'bajo_logro_educativo', 'inasistencia_escolar')
        }),
        ('Indicadores Socioeconómicos - Trabajo', {
            'fields': ('trabajo_informal', 'desempleo_larga_duracion', 'trabajo_infantil')
        }),
        ('Indicadores Socioeconómicos - Vivienda y Servicios', {
            'fields': ('hacinamiento_critico', 'barreras_servicios_cuidado_primera_infancia', 
                      'barreras_acceso_servicios_salud', 'inadecuada_eliminacion_excretas', 
                      'sin_acceso_fuente_agua_mejorada', 'sin_aseguramiento_salud')
        }),
        ('Imágenes', {
            'fields': ('escudo', 'bandera')
        }),
        ('Observaciones', {
            'fields': ('observaciones',)
        }),
    )
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')

@admin.register(DocumentoCaracterizacion)
class DocumentoCaracterizacionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'caracterizacion', 'fecha_subida')
    list_filter = ('fecha_subida',)
    search_fields = ('titulo', 'descripcion', 'caracterizacion__municipio__nombre')