from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
  path('admin/', admin.site.urls),

  path('', views.index_view, name='index'), 
  #encuesta
  path('encuestas/nueva/', views.seleccionar_metodo_creacion, name='seleccionar_metodo'),
  path('encuestas/crear/desde-cero/', views.crear_desde_cero, name='crear_desde_cero'),
  path('encuestas/crear/con-ia/', views.crear_con_ia, name='crear_con_ia'),
  path('encuestas/duplicar/', views.duplicar_encuesta, name='duplicar_encuesta'),
  path('encuestas/editar/<int:encuesta_id>/', views.editar_encuesta, name='editar_encuesta'),
  path('encuestas/eliminar/<int:encuesta_id>/', views.eliminar_encuesta, name='eliminar_encuesta'),
  path('encuestas/mis-encuestas/', views.ListaEncuestasView.as_view(), name='lista_encuestas'),
  path('encuestas/todas-encuestas/', views.TodasEncuestasView.as_view(), name='todas_encuestas'),
  path('encuestas/<int:pk>/resultados/', views.ResultadosEncuestaView.as_view(), name='resultados_encuesta'),
  path('encuestas/<slug:slug>/responder/', views.responder_encuesta, name='responder_encuesta'),
  path('encuesta/responder/<int:encuesta_id>/', views.guardar_respuesta, name='guardar_respuesta'),
  path('regiones-y-municipios/', views.regiones_y_municipios, name='regiones_y_municipios'),
  path('region/crear/', views.crear_region, name='crear_region'),
  path('municipio/crear/', views.crear_municipio, name='crear_municipio'),
  path('categoria/crear/', views.crear_categoria, name='crear_categoria'), # Crear Categoria
  path('categoria/eliminar/<int:categoria_id>/', views.eliminar_categoria, name='eliminar_categoria'), # Eliminar Categoria
  path('api/municipios/', views.municipios_por_region, name='municipios_por_region'),
  path('encuestas/<int:encuesta_id>/diseno/', views.actualizar_diseno, name='actualizar_diseno'),
  path('encuestas/<int:encuesta_id>/preview-diseno/', views.preview_diseno, name='preview_diseno'),

  #Inicio Sesion y Registro
  path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
  path('accounts/logout/', views.custom_logout, name='logout'),
  path('accounts/registro/', views.registro_view, name='registro'),

  path('pregunta/<int:pregunta_id>/editar/', views.editar_pregunta, name='editar_pregunta'),
  path('pregunta/<int:pregunta_id>/eliminar/', views.eliminar_pregunta, name='eliminar_pregunta'),
  path('encuesta/<int:encuesta_id>/agregar-pregunta/', views.agregar_pregunta, name='agregar_pregunta'),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) \
  + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)