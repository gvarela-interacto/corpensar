import os
import google.generativeai as genai
from PyPDF2 import PdfReader
import logging
from django.conf import settings
import json
import re
import mimetypes
from corpensar.models import Encuesta

logger = logging.getLogger(__name__)

def configure_gemini():
    """Configura la API de Google Gemini con la clave de API"""
    try:
        api_key = settings.GEMINI_API_KEY
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        logger.error(f"Error al configurar Gemini API: {str(e)}")
        return False

def extract_json_from_response(response_text):
    """Extrae el JSON de la respuesta de Gemini de manera más robusta"""
    try:
        # Loggear la respuesta completa para diagnóstico
        logger.info(f"Respuesta de Gemini (primeros 200 caracteres): {response_text[:200]}...")
        
        # Intento 1: Buscar patrón JSON usando expresiones regulares
        json_pattern = r'({[\s\S]*?})'
        matches = re.findall(json_pattern, response_text)
        
        if matches:
            # Intenta con el match más grande (probablemente el JSON completo)
            matches.sort(key=len, reverse=True)
            for json_candidate in matches:
                try:
                    return json.loads(json_candidate)
                except json.JSONDecodeError:
                    continue
        
        # Intento 2: Extraer desde la primera llave hasta la última
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        if start_idx >= 0 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Si falla, intentar limpiar el texto
                json_str = re.sub(r'[\n\r\t]', ' ', json_str)
                
                # Intentar arreglar problemas comunes con las comillas
                json_str = re.sub(r'(?<!")(\w+)(?=":)', r'"\1"', json_str)
                
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
        
        # Intento 3: Extraer campo por campo manualmente
        # Crear un diccionario manualmente buscando patrones clave:valor
        manual_json = {}
        
        # Patrones para buscar valores
        patterns = {
            'municipio_nombre': r'"municipio_nombre"\s*:\s*"([^"]+)"',
            'area_km2': r'"area_km2"\s*:\s*(\d+(?:\.\d+)?)',
            'poblacion_total': r'"poblacion_total"\s*:\s*(\d+)',
            'poblacion_hombres_total': r'"poblacion_hombres_total"\s*:\s*(\d+)',
            'poblacion_mujeres_total': r'"poblacion_mujeres_total"\s*:\s*(\d+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, response_text)
            if match:
                value = match.group(1)
                # Convertir a número si es posible
                if key != 'municipio_nombre':
                    try:
                        value = float(value)
                        if value.is_integer():
                            value = int(value)
                    except ValueError:
                        pass
                manual_json[key] = value
        
        if manual_json:
            logger.warning(f"JSON construido manualmente con {len(manual_json)} campos: {manual_json}")
            return manual_json
            
        # Si todo falla, crear un JSON mínimo
        if 'municipio' in response_text.lower():
            # Buscar cualquier nombre de municipio en el texto
            municipio_match = re.search(r'municipio[:\s]+([A-Za-zÁÉÍÓÚáéíóúÑñ\s]+)', response_text, re.IGNORECASE)
            if municipio_match:
                nombre = municipio_match.group(1).strip()
                if nombre:
                    return {"municipio_nombre": nombre}
        
        logger.error(f"No se pudo extraer JSON válido de la respuesta. Texto: {response_text}")
        return {"municipio_nombre": "Municipio Desconocido"}
    except Exception as e:
        logger.error(f"Error al extraer JSON de la respuesta: {str(e)}")
        return {"municipio_nombre": "Error en procesamiento"}

def process_audio_with_gemini(audio_file, encuesta_id):
    """Procesa un archivo de audio directamente con Gemini para transcribir y extraer respuestas.
    
    Args:
        audio_file: Objeto de archivo de audio (ej. UploadedFile de Django).
        encuesta_id: ID de la encuesta para obtener las preguntas.
    
    Returns:
        tuple: (datos_json_respuestas, error_message)
    """

    if not configure_gemini():
        return None, "No se pudo configurar la API de Google Gemini"
    
    preguntas_info_dict = []
    try:
        encuesta = Encuesta.objects.get(id=encuesta_id)
        lista_objetos_preguntas = encuesta.obtener_preguntas_procesar_audio()
        for pregunta_obj in lista_objetos_preguntas:
            preguntas_info_dict.append({
                "id": str(pregunta_obj.id),
                "texto": pregunta_obj.texto
            })
    except Encuesta.DoesNotExist:
        return None, f"Encuesta con ID {encuesta_id} no encontrada."
    except Exception as e:
        logger.error(f"Error al obtener preguntas de la encuesta: {str(e)}")
        return None, f"Error al obtener preguntas: {str(e)}"

    if not preguntas_info_dict:
        return None, "No se encontraron preguntas de tipo texto o texto múltiple en la encuesta."

    # Preparar datos del archivo de audio
    audio_bytes = None
    audio_mime_type = None
    try:
        audio_file.seek(0)
        audio_bytes = audio_file.read()
        
        if hasattr(audio_file, 'content_type') and audio_file.content_type:
            audio_mime_type = audio_file.content_type
            logger.info(f"MIME type obtenido de audio_file.content_type: {audio_mime_type}")
        elif hasattr(audio_file, 'name') and audio_file.name:
            guessed_type, _ = mimetypes.guess_type(audio_file.name)
            if guessed_type:
                audio_mime_type = guessed_type
                logger.info(f"MIME type adivinado desde audio_file.name '{audio_file.name}': {audio_mime_type}")
            else:
                logger.warning(f"No se pudo adivinar el MIME type para el nombre de archivo: {audio_file.name}")
        else:
            logger.warning("No se pudo determinar el MIME type del audio: 'content_type' no disponible y 'name' no disponible o no útil.")

        if not audio_mime_type: # Fallback adicional si aún no se tiene tipo MIME
            if hasattr(audio_file, 'name'):
                filename_lower = audio_file.name.lower()
                if filename_lower.endswith('.m4a'): audio_mime_type = 'audio/m4a'
                elif filename_lower.endswith('.mp3'): audio_mime_type = 'audio/mpeg'
                elif filename_lower.endswith('.wav'): audio_mime_type = 'audio/wav'
                elif filename_lower.endswith('.ogg'): audio_mime_type = 'audio/ogg'
                elif filename_lower.endswith('.flac'): audio_mime_type = 'audio/flac'
                if audio_mime_type:
                    logger.info(f"MIME type asignado por fallback de extensión: {audio_mime_type}")
        
        if not audio_bytes:
            return None, "El archivo de audio está vacío o no se pudo leer."
        
        logger.info(f"Archivo de audio leído: {len(audio_bytes)} bytes. MIME type: {audio_mime_type if audio_mime_type else 'No especificado'}")

    except Exception as e:
        logger.error(f"Error al leer el archivo de audio: {str(e)}")
        return None, "Error al leer el archivo de audio. Asegúrese de que sea un archivo de audio válido y no un archivo de texto."

    if not audio_mime_type:
        logger.error("No se pudo determinar un MIME type válido para el archivo de audio después de todos los intentos.")
        return None, "No se pudo determinar el tipo de archivo de audio. Asegúrese de que el archivo tenga una extensión o formato reconocible (ej: .m4a, .mp3, .wav)."

    prompt_preguntas_list = []
    for i, pregunta_data in enumerate(preguntas_info_dict):
        prompt_preguntas_list.append(f"{i+1}. (ID: {pregunta_data['id']}) {pregunta_data['texto']}")
    prompt_preguntas_str = "\\n".join(prompt_preguntas_list)

    # Prompt para Gemini (parte de texto)
    prompt_instructions_part = f"""
Eres un asistente de IA encargado de analizar el siguiente AUDIO de una entrevista o grupo focal.
Tu tarea principal es primero transcribir el contenido del audio. Una vez transcrito, debes identificar y extraer las respuestas a las preguntas proporcionadas basándote en esa transcripción.

PREGUNTAS A RESPONDER (utiliza el ID de la pregunta como clave en el JSON de salida):
---
{prompt_preguntas_str}
---

INSTRUCCIONES PARA EL FORMATO DE SALIDA:
1. Devuelve un ÚNICO objeto JSON.
2. Las claves del JSON deben ser los IDs de las preguntas tal como se muestran (ej: "ID: xxx").
3. Los valores deben ser las respuestas extraídas del audio para cada pregunta.
4. Si no encuentras una respuesta clara para una pregunta específica, puedes omitir esa clave del JSON o asignar un string vacío "" como valor. NO uses null o N/A.
5. Sé conciso y extrae solo la respuesta pertinente. Asegúrate de que la respuesta refleje fielmente lo dicho en el audio.
6. El JSON debe ser la única salida, sin texto introductorio, explicaciones adicionales ni formato Markdown.

EJEMPLO DE FORMATO JSON DE SALIDA ESPERADO:
{{{{  # Se duplican las llaves para el f-string
  "ID_pregunta_1": "Respuesta extraída del audio para la pregunta 1...",
  "ID_pregunta_2": "Respuesta extraída del audio para la pregunta 2...",
  ...
}}}}
"""

    # Construir el contenido para la API de Gemini
    content_for_gemini = [
        prompt_instructions_part,
        {
            "mime_type": audio_mime_type,
            "data": audio_bytes
        }
    ]

    try:
        logger.info("Usando modelo gemini-1.5-flash-latest para procesar el audio.")
        model = genai.GenerativeModel('gemini-1.5-flash-latest')

        generation_config = {
            "temperature": 0.1,
            "top_p": 0.95,
            "top_k": 0,
            "max_output_tokens": 4096,
            "response_mime_type": "application/json",
        }
        
        logger.info(f"Enviando contenido multimodal a Gemini. Longitud de instrucciones: {len(prompt_instructions_part)} caracteres. Tamaño de audio: {len(audio_bytes)} bytes.")
        logger.debug(f"Instrucciones para Gemini (primeros 500 caracteres): {prompt_instructions_part[:500]}...")

        response = model.generate_content(
            content_for_gemini, # <--- Contenido multimodal
            generation_config=generation_config
        )
        
        logger.info("Respuesta recibida de la API de Gemini.")
        logger.debug(f"Respuesta de Gemini (texto): {response.text[:500]}...")

        raw_response_text = response.text
        final_answers = {}

        try:
            parsed_json = json.loads(raw_response_text)
            if isinstance(parsed_json, dict):
                for key, value in parsed_json.items():
                    match = re.search(r'ID: (\S+)', str(key))
                    if match:
                        final_answers[match.group(1)] = str(value)
                    else:
                        logger.warning(f"Clave JSON inesperada de Gemini: {key}. Se esperaba formato 'ID: xxx'.")
                        final_answers[str(key)] = str(value)
            else:
                logger.warning(f"Gemini devolvió un JSON que no es un diccionario: {type(parsed_json)}. Se intentará extracción robusta.")
                raise json.JSONDecodeError("No es un diccionario", raw_response_text, 0)

        except json.JSONDecodeError:
            logger.warning(f"No se pudo decodificar la respuesta de Gemini como JSON directamente o no era un dict. Respuesta: {raw_response_text[:200]}. Intentando extracción robusta.")
            extracted_data = extract_json_from_response(raw_response_text)
            if isinstance(extracted_data, dict):
                for key, value in extracted_data.items():
                    match = re.search(r'ID: (\S+)', str(key))
                    if match:
                        final_answers[match.group(1)] = str(value)
                    else:
                        final_answers[str(key)] = str(value)
            else:
                logger.error(f"La extracción robusta tampoco pudo obtener un diccionario JSON. Data: {extracted_data}")
                return None, f"No se pudo extraer un JSON válido de la respuesta de Gemini. Contenido: {raw_response_text[:200]}..."
        
        if not final_answers:
            logger.warning(f"El JSON procesado de Gemini está vacío. Respuesta original: {raw_response_text[:200]}")
            return None, f"No se obtuvieron respuestas válidas de Gemini. Respuesta: {raw_response_text[:200]}..."

        logger.info(f"Respuestas JSON procesadas: {final_answers}")
        return final_answers, None

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error al procesar audio con Gemini: {error_msg}")
        
        if "API key not valid" in error_msg:
            return None, "Error de API Key con Gemini. Por favor, verifica la configuración."
        if "model not found" in error_msg or "Could not find model" in error_msg or "permission" in error_msg.lower() :
            logger.warning(f"Modelo 'gemini-1.5-flash-latest' no encontrado, inválido o sin permisos. Intentando con 'gemini-1.5-flash'.")
            try:
                model = genai.GenerativeModel('gemini-1.5-flash') 
                response = model.generate_content(content_for_gemini, generation_config=generation_config) # <--- Usar content_for_gemini también en fallback
                logger.info("Respuesta recibida de Gemini con modelo de fallback 'gemini-1.5-flash'.")
                raw_response_text_fallback = response.text
                final_answers_fallback = {}
                try:
                    parsed_json_fallback = json.loads(raw_response_text_fallback)
                    if isinstance(parsed_json_fallback, dict):
                        for key, value in parsed_json_fallback.items():
                            match = re.search(r'ID: (\S+)', str(key))
                            if match:
                                final_answers_fallback[match.group(1)] = str(value)
                            else:
                                final_answers_fallback[str(key)] = str(value)
                    else:
                        raise json.JSONDecodeError("No es un diccionario", raw_response_text_fallback, 0)

                except json.JSONDecodeError:
                    logger.warning(f"Fallo JSON directo con modelo fallback. Respuesta: {raw_response_text_fallback[:200]}. Intentando extracción robusta.")
                    extracted_data_fallback = extract_json_from_response(raw_response_text_fallback)
                    if isinstance(extracted_data_fallback, dict):
                        for key, value in extracted_data_fallback.items():
                            match = re.search(r'ID: (\S+)', str(key))
                            if match:
                                final_answers_fallback[match.group(1)] = str(value)
                            else:
                                final_answers_fallback[str(key)] = str(value)
                    else:
                        logger.error(f"Extracción robusta falló con modelo fallback. Data: {extracted_data_fallback}")
                        return None, f"No se pudo extraer JSON (modelo fallback). Respuesta: {raw_response_text_fallback[:200]}"
                
                if not final_answers_fallback:
                    return None, f"No se obtuvieron respuestas (modelo fallback). Respuesta: {raw_response_text_fallback[:200]}..."
                
                logger.info(f"Respuestas JSON procesadas con modelo de fallback: {final_answers_fallback}")
                return final_answers_fallback, None

            except Exception as fallback_e:
                logger.error(f"Error también con el modelo de fallback 'gemini-1.5-flash': {str(fallback_e)}")
                return None, f"Error al procesar con Gemini (ambos modelos intentados): {str(fallback_e)}"

        return None, f"Error inesperado al procesar con Gemini: {error_msg}"

def extract_json_array_from_response(response_text):
    """Extrae un array JSON de la respuesta de Gemini"""
    try:
        # Buscar el patrón de array JSON usando regex
        array_pattern = r'(\[[\s\S]*?\])'
        array_matches = re.findall(array_pattern, response_text)
        
        if array_matches:
            # Intenta con el match más grande (probablemente el array completo)
            array_matches.sort(key=len, reverse=True)
            for array_candidate in array_matches:
                try:
                    return json.loads(array_candidate)
                except json.JSONDecodeError:
                    continue
        
        # Intento alternativo: extraer desde el primer corchete hasta el último
        start_idx = response_text.find('[')
        end_idx = response_text.rfind(']') + 1
        
        if start_idx >= 0 and end_idx > start_idx:
            array_str = response_text[start_idx:end_idx]
            try:
                return json.loads(array_str)
            except json.JSONDecodeError:
                # Si falla, intentar limpiar el texto
                array_str = re.sub(r'[\n\r\t]', ' ', array_str)
                try:
                    return json.loads(array_str)
                except json.JSONDecodeError:
                    pass
        
        # Si todo falla, buscar objetos JSON individuales y construir el array manualmente
        object_pattern = r'({[^{}]*})'
        object_matches = re.findall(object_pattern, response_text)
        
        if object_matches:
            result_array = []
            for obj_str in object_matches:
                try:
                    obj_data = json.loads(obj_str)
                    if isinstance(obj_data, dict) and "municipio_nombre" in obj_data:
                        result_array.append(obj_data)
                except json.JSONDecodeError:
                    continue
            
            if result_array:
                return result_array
        
        logger.error(f"No se pudo extraer array JSON válido de la respuesta")
        return []
    except Exception as e:
        logger.error(f"Error al extraer array JSON de la respuesta: {str(e)}")
        return [] 