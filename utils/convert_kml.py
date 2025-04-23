from lxml import etree
import json
import os
from django.conf import settings

def extract_coordinates(coord_str):
    """
    Extrae coordenadas de una cadena KML
    """
    coords = []
    for point in str(coord_str).strip().split():
        try:
            lon, lat, _ = point.split(',')
            coords.append([float(lon), float(lat)])
        except (ValueError, TypeError):
            continue
    return coords

def kml_to_geojson(input_path, output_path):
    """
    Convierte un archivo KML a GeoJSON usando lxml
    """
    # Asegurarse de que el directorio de salida existe
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Leer el archivo KML
    parser = etree.XMLParser(recover=True, remove_blank_text=True)
    tree = etree.parse(input_path, parser)
    root = tree.getroot()
    
    # Registrar todos los namespaces posibles
    ns = {
        'kml': 'http://www.opengis.net/kml/2.2',
        'gx': 'http://www.google.com/kml/ext/2.2',
        'atom': 'http://www.w3.org/2005/Atom',
        'xal': 'urn:oasis:names:tc:ciq:xsdschema:xAL:2.0'
    }
    
    # Convertir a GeoJSON
    features = []
    
    # Buscar todos los Placemarks
    for placemark in root.xpath('.//kml:Placemark | .//Placemark', namespaces=ns):
        try:
            # Extraer nombre y descripción
            name_elem = placemark.xpath('./kml:name | ./name', namespaces=ns)
            name = name_elem[0].text if name_elem else ''
            
            desc_elem = placemark.xpath('./kml:description | ./description', namespaces=ns)
            description = desc_elem[0].text if desc_elem else ''
            
            # Buscar LineString
            line_coords = placemark.xpath('.//kml:LineString/kml:coordinates | .//LineString/coordinates', namespaces=ns)
            if line_coords:
                coords = extract_coordinates(line_coords[0].text)
                if coords:
                    feature = {
                        'type': 'Feature',
                        'geometry': {
                            'type': 'LineString',
                            'coordinates': coords
                        },
                        'properties': {
                            'name': name,
                            'description': description
                        }
                    }
                    features.append(feature)
                    print(f"LineString procesado: {name}")
            
            # Buscar Polygon
            polygon_coords = placemark.xpath('.//kml:Polygon/kml:outerBoundaryIs/kml:LinearRing/kml:coordinates | .//Polygon/outerBoundaryIs/LinearRing/coordinates', namespaces=ns)
            if polygon_coords:
                coords = extract_coordinates(polygon_coords[0].text)
                if coords:
                    feature = {
                        'type': 'Feature',
                        'geometry': {
                            'type': 'Polygon',
                            'coordinates': [coords]  # GeoJSON requiere un array adicional para polígonos
                        },
                        'properties': {
                            'name': name,
                            'description': description
                        }
                    }
                    features.append(feature)
                    print(f"Polygon procesado: {name}")
        except Exception as e:
            print(f"Error procesando placemark: {str(e)}")
            continue
    
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    # Guardar el GeoJSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)
    
    print(f"Conversión completada: {output_path}")
    print(f"Total de features convertidas: {len(features)}")

def convert_kml_to_geojson():
    """
    Función para convertir el KML del oleoducto a GeoJSON
    """
    # Usar rutas relativas al directorio del proyecto
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_path = os.path.join(base_dir, 'static', 'kml', 'Trazado oleoducto Cenit.kml')
    output_path = os.path.join(base_dir, 'static', 'kml', 'Trazado_oleoducto_Cenit.geojson')
    
    try:
        kml_to_geojson(input_path, output_path)
        return True
    except Exception as e:
        print(f"Error al convertir KML a GeoJSON: {str(e)}")
        return False 