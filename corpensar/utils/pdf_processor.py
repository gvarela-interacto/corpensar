import os
import google.generativeai as genai
from PyPDF2 import PdfReader
import logging
from django.conf import settings
import json
import re

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

def extract_text_from_pdf(pdf_file):
    """Extrae el texto de un archivo PDF"""
    try:
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        logger.error(f"Error al extraer texto del PDF: {str(e)}")
        return ""

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

def process_pdf_with_gemini(pdf_file, municipio_nombre=None):
    """Procesa un archivo PDF con Gemini para extraer datos de caracterización municipal
    
    Args:
        pdf_file: Archivo PDF a procesar
        municipio_nombre: Nombre del municipio a buscar específicamente (opcional)
    
    Returns:
        tuple: (datos_json, error_message)
    """
    if not configure_gemini():
        return {"error": "Error API"}, "No se pudo configurar la API de Google Gemini"
    
    # Extraer texto del PDF
    pdf_text = extract_text_from_pdf(pdf_file)
    if not pdf_text:
        return {"error": "Error PDF"}, "No se pudo extraer texto del PDF"
    
    logger.info(f"Texto extraído del PDF: {len(pdf_text)} caracteres")
    
    # Ajustar el prompt según si tenemos un municipio específico o no
    municipio_instruccion = ""
    if municipio_nombre:
        municipio_instruccion = f"""
        IMPORTANTE: Busca específicamente información sobre el municipio "{municipio_nombre}".
        Enfócate SOLO en este municipio y extrae sus datos, ignorando información de otros municipios.
        """
        
        # Prompt para Gemini - para un municipio específico
        prompt = f"""
        Analiza el siguiente documento PDF sobre municipios y extrae la información en formato JSON.
        
        {municipio_instruccion}
        
        CONTENIDO DEL PDF:
        {pdf_text[:25000]}  # Ampliamos el límite para capturar más información
        
        EXTRAE LOS SIGUIENTES CAMPOS EN FORMATO JSON:
        {{
            "municipio_nombre": "{municipio_nombre}",
            "area_km2": número,
            "concejos_comunitarios_ha": número,
            "resguardos_indigenas_ha": número,
            "zonas_reserva_campesina_ha": número,
            "zonas_reserva_sinap_ha": número,
            "es_municipio_pdei": true/false,
            "poblacion_total": número,
            "poblacion_hombres_total": número,
            "poblacion_mujeres_total": número,
            "poblacion_hombres_rural": número,
            "poblacion_mujeres_rural": número,
            "poblacion_hombres_urbana": número,
            "poblacion_mujeres_urbana": número,
            "poblacion_indigena": número,
            "poblacion_raizal": número,
            "poblacion_gitano_rrom": número,
            "poblacion_palenquero": número,
            "poblacion_negro_mulato_afrocolombiano": número,
            "poblacion_desplazada": número,
            "poblacion_migrantes": número,
            "necesidades_basicas_insatisfechas": número,
            "proporcion_personas_miseria": número,
            "indice_pobreza_multidimensional": número,
            "analfabetismo": número,
            "bajo_logro_educativo": número,
            "inasistencia_escolar": número,
            "trabajo_informal": número,
            "desempleo_larga_duracion": número,
            "trabajo_infantil": número,
            "hacinamiento_critico": número,
            "barreras_servicios_cuidado_primera_infancia": número,
            "barreras_acceso_servicios_salud": número,
            "inadecuada_eliminacion_excretas": número,
            "sin_acceso_fuente_agua_mejorada": número,
            "sin_aseguramiento_salud": número
        }}
        
        SI NO ENCUENTRAS ALGÚN DATO, OMÍTELO DEL JSON. NO USES VALORES COMO "null", "N/A" O "0".
        DEVUELVE SOLO EL JSON, SIN TEXTO ADICIONAL NI EXPLICACIONES.
        """
        
        # Para un solo municipio, procesamos como antes
        return process_single_municipality(prompt, municipio_nombre)
    else:
        # Para múltiples municipios, usamos un enfoque diferente
        prompt = f"""
        Analiza el siguiente documento PDF que contiene información sobre MÚLTIPLES municipios.
        
        CONTENIDO DEL PDF:
        {pdf_text[:48000]}  # Ampliamos el límite para capturar información de varios municipios
        
        INSTRUCCIONES:
        1. Identifica todos los municipios que aparecen en el documento
        2. Para cada municipio, extrae la siguiente información
        3. Devuelve un array JSON con la información de TODOS los municipios encontrados
        
        FORMATO DE RESPUESTA:
        [
            {{
                "municipio_nombre": "Nombre del primer municipio",
                "area_km2": número,
                "concejos_comunitarios_ha": número,
                "resguardos_indigenas_ha": número,
                "zonas_reserva_campesina_ha": número,
                "zonas_reserva_sinap_ha": número,
                "es_municipio_pdei": true/false,
                "poblacion_total": número,
                "poblacion_hombres_total": número,
                "poblacion_mujeres_total": número,
                "poblacion_hombres_rural": número,
                "poblacion_mujeres_rural": número,
                "poblacion_hombres_urbana": número,
                "poblacion_mujeres_urbana": número,
                "poblacion_indigena": número,
                "poblacion_raizal": número,
                "poblacion_gitano_rrom": número,
                "poblacion_palenquero": número,
                "poblacion_negro_mulato_afrocolombiano": número,
                "poblacion_desplazada": número,
                "poblacion_migrantes": número,
                "necesidades_basicas_insatisfechas": número,
                "proporcion_personas_miseria": número,
                "indice_pobreza_multidimensional": número,
                "analfabetismo": número,
                "bajo_logro_educativo": número,
                "inasistencia_escolar": número,
                "trabajo_informal": número,
                "desempleo_larga_duracion": número,
                "trabajo_infantil": número,
                "hacinamiento_critico": número,
                "barreras_servicios_cuidado_primera_infancia": número,
                "barreras_acceso_servicios_salud": número,
                "inadecuada_eliminacion_excretas": número,
                "sin_acceso_fuente_agua_mejorada": número,
                "sin_aseguramiento_salud": número
            }},
            {{
                "municipio_nombre": "Nombre del segundo municipio",
                ... (mismos campos que el anterior)
            }},
            ... (y así sucesivamente para cada municipio)
        ]
        
        IMPORTANTE: Asegúrate de que cada objeto JSON del array tenga el nombre del municipio correcto.
        SI NO ENCUENTRAS ALGÚN DATO, OMÍTELO DEL JSON. NO USES VALORES COMO "null", "N/A" O "0".
        DEVUELVE SOLO EL ARRAY JSON, SIN TEXTO ADICIONAL NI EXPLICACIONES.
        """
        
        return process_multiple_municipalities(prompt)

def process_single_municipality(prompt, municipio_nombre=None):
    """Procesa un PDF para un solo municipio"""
    try:
        # Configurar el modelo gemini-1.5-flash (nombre correcto)
        logger.info("Usando modelo gemini-1.5-flash para procesar el PDF")
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Configurar generación para enfatizar precisión
        generation_config = {
            "temperature": 0,
            "top_p": 0.95,
            "top_k": 0,
            "max_output_tokens": 2048,
        }
        
        # Enviar la solicitud al modelo
        logger.info("Enviando solicitud a la API de Gemini...")
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        logger.info("Respuesta recibida de la API de Gemini")
        
        # Mostrar respuesta completa para debug
        logger.debug(f"Respuesta completa de Gemini: {response.text}")
        
        # Extraer el resultado JSON
        data = extract_json_from_response(response.text)
        
        # Si proporcionamos un municipio específico y no se encuentra en los datos,
        # asegurémonos de agregarlo
        if municipio_nombre and (not data or "municipio_nombre" not in data):
            if not data:
                data = {}
            data["municipio_nombre"] = municipio_nombre
        
        if not data or not isinstance(data, dict) or len(data) == 0:
            logger.warning("No se pudo extraer JSON, creando datos mínimos")
            return {"municipio_nombre": municipio_nombre or "Datos no detectados"}, None
            
        logger.info(f"Datos extraídos: {data}")
        return data, None
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error al procesar PDF con Gemini: {error_msg}")
        
        # Verificar si el error es por el modelo incorrecto
        if "model not found" in error_msg.lower():
            try:
                # Intentar con un modelo alternativo
                logger.info("Intentando con modelo alternativo gemini-pro...")
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content(prompt)
                data = extract_json_from_response(response.text)
                
                # Si proporcionamos un municipio específico, asegurémonos de que esté en los datos
                if municipio_nombre and (not data or "municipio_nombre" not in data):
                    if not data:
                        data = {}
                    data["municipio_nombre"] = municipio_nombre
                    
                if data:
                    logger.info(f"Extracción exitosa con modelo alternativo: {data}")
                    return data, None
            except Exception as alt_e:
                logger.error(f"Error con modelo alternativo: {str(alt_e)}")
        
        # Si todo falla, devolver un objeto mínimo para continuar
        return {"municipio_nombre": municipio_nombre or "Error en procesamiento"}, f"Error al procesar el PDF: {error_msg}"

def process_multiple_municipalities(prompt):
    """Procesa un PDF para extraer datos de múltiples municipios"""
    try:
        # Configurar el modelo gemini-1.5-flash (nombre correcto)
        logger.info("Usando modelo gemini-1.5-flash para procesar múltiples municipios")
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Configurar generación para enfatizar precisión
        generation_config = {
            "temperature": 0,
            "top_p": 0.95,
            "top_k": 0,
            "max_output_tokens": 8192,  # Aumentamos el límite para múltiples municipios
        }
        
        # Enviar la solicitud al modelo
        logger.info("Enviando solicitud a la API de Gemini para múltiples municipios...")
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        logger.info("Respuesta recibida de la API de Gemini")
        
        # Mostrar respuesta completa para debug
        logger.debug(f"Respuesta completa de Gemini: {response.text[:500]}...")
        
        # Extraer el resultado JSON (array)
        municipalities_data = extract_json_array_from_response(response.text)
        
        if not municipalities_data or not isinstance(municipalities_data, list) or len(municipalities_data) == 0:
            logger.warning("No se pudieron extraer datos de municipios, devolviendo array vacío")
            return [], "No se encontraron municipios en el documento"
            
        logger.info(f"Se encontraron {len(municipalities_data)} municipios en el documento")
        
        # Verificar que cada elemento tenga al menos el nombre del municipio
        valid_municipalities = []
        for muni_data in municipalities_data:
            if isinstance(muni_data, dict) and "municipio_nombre" in muni_data:
                valid_municipalities.append(muni_data)
            else:
                logger.warning(f"Se encontró un municipio sin nombre válido: {muni_data}")
        
        return valid_municipalities, None
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error al procesar múltiples municipios: {error_msg}")
        
        # Verificar si el error es por el modelo incorrecto
        if "model not found" in error_msg.lower():
            try:
                # Intentar con un modelo alternativo
                logger.info("Intentando con modelo alternativo gemini-pro...")
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content(prompt)
                municipalities_data = extract_json_array_from_response(response.text)
                
                if municipalities_data and isinstance(municipalities_data, list) and len(municipalities_data) > 0:
                    logger.info(f"Extracción exitosa con modelo alternativo: {len(municipalities_data)} municipios")
                    return municipalities_data, None
            except Exception as alt_e:
                logger.error(f"Error con modelo alternativo: {str(alt_e)}")
        
        # Si todo falla, devolver un array vacío
        return [], f"Error al procesar el PDF: {error_msg}"

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