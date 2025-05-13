import os
import sys
import django

# Agregar el directorio actual al path de Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configurar entorno Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "corpensar.settings")
django.setup()

from django.db import connection

def check_table_exists(table_name):
    """Verifica si una tabla existe en la base de datos"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            AND table_name = %s
        """, [table_name])
        return cursor.fetchone()[0] > 0

def create_documento_caracterizacion_table():
    """Crea la tabla DocumentoCaracterizacion si no existe"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS `corpensar_documentocaracterizacion` (
                `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
                `titulo` varchar(200) NOT NULL,
                `descripcion` longtext NOT NULL,
                `archivo` varchar(100) NOT NULL,
                `fecha_subida` datetime(6) NOT NULL,
                `caracterizacion_id` bigint NOT NULL
            )
            """)
            
            # Agregar la restricción de clave externa
            try:
                cursor.execute("""
                ALTER TABLE `corpensar_documentocaracterizacion` 
                ADD CONSTRAINT `corpensar_documentoc_caracterizacion_id_fk` 
                FOREIGN KEY (`caracterizacion_id`) 
                REFERENCES `corpensar_caracterizacionmunicipal` (`id`)
                ON DELETE CASCADE
                """)
            except Exception as e:
                print(f"Error al agregar la restricción de clave externa: {str(e)}")
                print("Continuando sin la restricción...")
            
            print("Tabla creada exitosamente")
    except Exception as e:
        print(f"Error al crear la tabla: {str(e)}")

def main():
    # Verificar si la tabla existe
    table_name = 'corpensar_documentocaracterizacion'
    if check_table_exists(table_name):
        print(f"La tabla {table_name} ya existe.")
    else:
        print(f"La tabla {table_name} no existe. Creándola...")
        create_documento_caracterizacion_table()

if __name__ == "__main__":
    main() 