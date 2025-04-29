from django.utils.deprecation import MiddlewareMixin
from .models import PQRSFD

class PQRSFDContextMiddleware(MiddlewareMixin):
    """Middleware que agrega los contadores de PQRSFD al contexto de todas las plantillas."""
    
    def process_template_response(self, request, response):
        if hasattr(response, 'context_data') and request.user.is_authenticated:
            # Sólo calcular los contadores si no están ya en el contexto
            if 'conteo_estados' not in response.context_data:
                # Contar PQRSFD por estado
                conteo_estados = {
                    'P': PQRSFD.objects.filter(estado='P').count(),
                    'E': PQRSFD.objects.filter(estado='E').count(),
                    'R': PQRSFD.objects.filter(estado='R').count(),
                    'C': PQRSFD.objects.filter(estado='C').count(),
                    'total': PQRSFD.objects.count(),
                    'vencidos': sum(1 for p in PQRSFD.objects.filter(estado__in=['P', 'E']) if p.esta_vencido())
                }
                response.context_data['conteo_estados'] = conteo_estados
        return response 