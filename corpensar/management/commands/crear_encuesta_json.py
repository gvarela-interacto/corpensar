import json
import re
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.auth.models import User
from django.db import transaction
from corpensar.models import (
    Encuesta, Region, Categoria, Municipio,
    PreguntaTexto, PreguntaTextoMultiple, PreguntaOpcionMultiple, OpcionMultiple,
    PreguntaCasillasVerificacion, OpcionCasillaVerificacion, PreguntaEscala,
    PreguntaMenuDesplegable, OpcionMenuDesplegable, PreguntaEstrellas, PreguntaMatriz,
    ItemMatrizPregunta, PreguntaFecha
)
from datetime import timedelta

class Command(BaseCommand):
    help = 'Crea una encuesta a partir de un archivo JSON'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Ruta al archivo JSON con la estructura de la encuesta')

    def handle(self, *args, **options):
        json_file = options['json_file']

        try:
            # Cargar el JSON
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Buscar usuario amesa 
            try:
                usuario = User.objects.get(username='amesa')
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR('No existe el usuario amesa'))
                return

            # Buscar la región "Oleoducto Llanos"
            try:
                region = Region.objects.get(nombre__icontains='oleoducto llanos')
            except Region.DoesNotExist:
                self.stdout.write(self.style.ERROR('No existe la región "Oleoducto Llanos"'))
                return

            # Buscar categoría o crear una por defecto si no existe
            categoria = None
            if 'categoria' in data:
                try:
                    categoria = Categoria.objects.get(nombre=data['categoria'])
                except Categoria.DoesNotExist:
                    categoria = Categoria.objects.create(nombre=data['categoria'])
            
            # Crear la encuesta
            with transaction.atomic():
                now = timezone.now()
                encuesta = Encuesta.objects.create(
                    titulo=data.get('titulo', 'Encuesta sin título'),
                    descripcion=data.get('descripcion', ''),
                    slug=data.get('slug', slugify(data.get('titulo', 'encuesta-sin-titulo'))),
                    fecha_creacion=now,
                    fecha_actualizacion=now,
                    fecha_inicio=now,
                    fecha_fin=now + timedelta(days=30),  # 30 días por defecto
                    activa=True,
                    creador=usuario,
                    es_publica=False,
                    region=region,
                    categoria=categoria,
                    tema='default'
                )
                
                # Crear las preguntas
                if 'preguntas' in data:
                    for i, pregunta_data in enumerate(data['preguntas']):
                        tipo = pregunta_data.get('tipo')
                        texto = pregunta_data.get('texto', '')
                        requerida = pregunta_data.get('requerida', True)
                        orden = i + 1
                        # Valores por defecto
                        seccion = pregunta_data.get('seccion', 'General')
                        ayuda = pregunta_data.get('ayuda', '')
                        
                        if tipo == 'TEXT':
                            PreguntaTexto.objects.create(
                                encuesta=encuesta,
                                texto=texto,
                                tipo=tipo,
                                requerida=requerida,
                                orden=orden,
                                seccion=seccion,
                                ayuda=ayuda,
                                max_longitud=pregunta_data.get('max_longitud', 250),
                                placeholder=pregunta_data.get('placeholder', '')
                            )
                        
                        elif tipo == 'MTEXT':
                            PreguntaTextoMultiple.objects.create(
                                encuesta=encuesta,
                                texto=texto,
                                tipo=tipo,
                                requerida=requerida,
                                orden=orden,
                                seccion=seccion,
                                ayuda=ayuda,
                                max_longitud=pregunta_data.get('max_longitud', 1000),
                                filas=pregunta_data.get('filas', 4),
                                placeholder=pregunta_data.get('placeholder', '')
                            )
                        
                        elif tipo == 'RADIO':
                            # Crear la pregunta
                            pregunta = PreguntaOpcionMultiple.objects.create(
                                encuesta=encuesta,
                                texto=texto,
                                tipo=tipo,
                                requerida=requerida,
                                orden=orden,
                                seccion=seccion,
                                ayuda=ayuda,
                                opcion_otro=pregunta_data.get('opcion_otro', False),
                                texto_otro=pregunta_data.get('texto_otro', 'Otro')
                            )
                            
                            # Crear las opciones
                            if 'opciones' in pregunta_data:
                                for j, opcion_data in enumerate(pregunta_data['opciones']):
                                    OpcionMultiple.objects.create(
                                        pregunta=pregunta,
                                        texto=opcion_data.get('texto', ''),
                                        valor=opcion_data.get('valor', ''),
                                        orden=j + 1
                                    )
                        
                        elif tipo == 'CHECK':
                            # Crear la pregunta
                            pregunta = PreguntaCasillasVerificacion.objects.create(
                                encuesta=encuesta,
                                texto=texto,
                                tipo=tipo,
                                requerida=requerida,
                                orden=orden,
                                seccion=seccion,
                                ayuda=ayuda,
                                opcion_otro=pregunta_data.get('opcion_otro', False),
                                texto_otro=pregunta_data.get('texto_otro', 'Otro'),
                                min_selecciones=pregunta_data.get('min_selecciones', 1),
                                max_selecciones=pregunta_data.get('max_selecciones', None)
                            )
                            
                            # Crear las opciones
                            if 'opciones' in pregunta_data:
                                for j, opcion_data in enumerate(pregunta_data['opciones']):
                                    OpcionCasillaVerificacion.objects.create(
                                        pregunta=pregunta,
                                        texto=opcion_data.get('texto', ''),
                                        valor=opcion_data.get('valor', ''),
                                        orden=j + 1
                                    )
                        
                        elif tipo == 'SELECT':
                            # Crear la pregunta
                            pregunta = PreguntaMenuDesplegable.objects.create(
                                encuesta=encuesta,
                                texto=texto,
                                tipo=tipo,
                                requerida=requerida,
                                orden=orden,
                                seccion=seccion,
                                ayuda=ayuda,
                                opcion_vacia=pregunta_data.get('opcion_vacia', True),
                                texto_vacio=pregunta_data.get('texto_vacio', 'Seleccione...')
                            )
                            
                            # Si el texto de la pregunta contiene la palabra "municipio",
                            # agregar como opciones los municipios de la región seleccionada
                            es_pregunta_municipio = re.search(r'municipio', texto.lower()) is not None
                            
                            if es_pregunta_municipio and 'opciones' not in pregunta_data:
                                # Obtener municipios de la región
                                municipios = Municipio.objects.filter(region=region).order_by('nombre')
                                
                                # Crear opciones con los municipios
                                for j, municipio in enumerate(municipios):
                                    OpcionMenuDesplegable.objects.create(
                                        pregunta=pregunta,
                                        texto=municipio.nombre,
                                        valor=str(municipio.id),
                                        orden=j + 1
                                    )
                                self.stdout.write(self.style.SUCCESS(f'  - Asociados {municipios.count()} municipios a pregunta "{texto}"'))
                            elif 'opciones' in pregunta_data:
                                for j, opcion_data in enumerate(pregunta_data['opciones']):
                                    OpcionMenuDesplegable.objects.create(
                                        pregunta=pregunta,
                                        texto=opcion_data.get('texto', ''),
                                        valor=opcion_data.get('valor', ''),
                                        orden=j + 1
                                    )
                        
                        elif tipo == 'SCALE':
                            PreguntaEscala.objects.create(
                                encuesta=encuesta,
                                texto=texto,
                                tipo=tipo,
                                requerida=requerida,
                                orden=orden,
                                seccion=seccion,
                                ayuda=ayuda,
                                min_valor=pregunta_data.get('min_valor', 1),
                                max_valor=pregunta_data.get('max_valor', 5),
                                etiqueta_min=pregunta_data.get('etiqueta_min', 'Muy en desacuerdo'),
                                etiqueta_max=pregunta_data.get('etiqueta_max', 'Muy de acuerdo'),
                                paso=pregunta_data.get('paso', 1)
                            )
                        
                        elif tipo == 'STAR':
                            PreguntaEstrellas.objects.create(
                                encuesta=encuesta,
                                texto=texto,
                                tipo=tipo,
                                requerida=requerida,
                                orden=orden,
                                seccion=seccion,
                                ayuda=ayuda,
                                max_estrellas=pregunta_data.get('max_estrellas', 5),
                                etiqueta_inicio=pregunta_data.get('etiqueta_inicio', 'Muy malo'),
                                etiqueta_fin=pregunta_data.get('etiqueta_fin', 'Excelente')
                            )
                        
                        elif tipo == 'MATRIX':
                            # Primero crear la escala
                            escala = PreguntaEscala.objects.create(
                                encuesta=encuesta,
                                texto=f"Escala para {texto}",
                                tipo='SCALE',
                                requerida=False,
                                orden=0,  # No mostrar en las preguntas normales
                                min_valor=pregunta_data.get('min_valor', 1),
                                max_valor=pregunta_data.get('max_valor', 5),
                                etiqueta_min=pregunta_data.get('etiqueta_min', 'Muy en desacuerdo'),
                                etiqueta_max=pregunta_data.get('etiqueta_max', 'Muy de acuerdo'),
                                paso=pregunta_data.get('paso', 1)
                            )
                            
                            # Crear la pregunta matriz
                            pregunta = PreguntaMatriz.objects.create(
                                encuesta=encuesta,
                                texto=texto,
                                tipo=tipo,
                                requerida=requerida,
                                orden=orden,
                                seccion=seccion,
                                ayuda=ayuda,
                                escala=escala
                            )
                            
                            # Crear los items de la matriz
                            if 'items' in pregunta_data:
                                for j, item_data in enumerate(pregunta_data['items']):
                                    ItemMatrizPregunta.objects.create(
                                        pregunta=pregunta,
                                        texto=item_data.get('texto', ''),
                                        orden=j + 1
                                    )
                        
                        elif tipo == 'DATE':
                            PreguntaFecha.objects.create(
                                encuesta=encuesta,
                                texto=texto,
                                tipo=tipo,
                                requerida=requerida,
                                orden=orden,
                                seccion=seccion,
                                ayuda=ayuda,
                                incluir_hora=pregunta_data.get('incluir_hora', False)
                            )
                
                self.stdout.write(self.style.SUCCESS(f'Encuesta "{encuesta.titulo}" creada correctamente con {len(data.get("preguntas", []))} preguntas'))
        
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'No se encontró el archivo {json_file}'))
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR(f'El archivo {json_file} no es un JSON válido'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error al crear la encuesta: {str(e)}')) 