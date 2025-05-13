import os
import google.generativeai as genai
from PyPDF2 import PdfReader
import logging
from django.conf import settings

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

def process_pdf_with_gemini(pdf_file):
    """Procesa un archivo PDF con Gemini para extraer datos de caracterización municipal"""
    if not configure_gemini():
        return None, "No se pudo configurar la API de Google Gemini"
    
    # Extraer texto del PDF
    pdf_text = extract_text_from_pdf(pdf_file)
    if not pdf_text:
        return None, "No se pudo extraer texto del PDF"
    
    # Prompt para Gemini
    prompt = f"""
    Analiza el siguiente documento que contiene información sobre un municipio y extrae los siguientes datos en formato JSON:
    
    {pdf_text}
    
    Extrae la siguiente información en formato JSON (solo valores, sin texto adicional):
    
    {{
        "municipio_nombre": "Nombre del municipio",
        "area_km2": número (área en km²),
        "poblacion_total": número entero,
        "poblacion_hombres_total": número entero,
        "poblacion_mujeres_total": número entero,
        "poblacion_hombres_rural": número entero,
        "poblacion_mujeres_rural": número entero,
        "poblacion_hombres_urbana": número entero,
        "poblacion_mujeres_urbana": número entero,
        "poblacion_indigena": número entero,
        "poblacion_raizal": número entero,
        "poblacion_gitano_rrom": número entero,
        "poblacion_palenquero": número entero,
        "poblacion_negro_mulato_afrocolombiano": número entero,
        "poblacion_desplazada": número entero,
        "poblacion_migrantes": número entero,
        "necesidades_basicas_insatisfechas": número decimal (porcentaje),
        "indice_pobreza_multidimensional": número decimal (porcentaje)
    }}
    
    Si no encuentras algún dato, déjalo con valor null. Asegúrate de devolver solo el JSON sin texto adicional.
    """
    
    try:
        # Configurar el modelo
        model = genai.GenerativeModel('gemini-flash')
        
        # Enviar la solicitud al modelo
        response = model.generate_content(prompt)
        
        # Extraer el resultado JSON
        return extract_json_from_response(response.text), None
    except Exception as e:
        logger.error(f"Error al procesar PDF con Gemini: {str(e)}")
        return None, f"Error al procesar el PDF: {str(e)}"

def extract_json_from_response(response_text):
    """Extrae el JSON de la respuesta de Gemini"""
    import json
    try:
        # Intentar encontrar solo la parte JSON
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        if start_idx == -1 or end_idx == 0:
            return None
        
        json_text = response_text[start_idx:end_idx]
        return json.loads(json_text)
    except Exception as e:
        logger.error(f"Error al extraer JSON de la respuesta: {str(e)}")
        return None 