#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from utils.convert_kml import convert_kml_to_geojson


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'corpensar.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    
    # Si el comando es 'convert_kml', ejecutar la conversión
    if len(sys.argv) > 1 and sys.argv[1] == 'convert_kml':
        if convert_kml_to_geojson():
            print("✅ Conversión completada exitosamente")
        else:
            print("❌ Error en la conversión")
        return
    
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
