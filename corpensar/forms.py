from django import forms
from .models import Encuesta
from django.utils import timezone
from django.core.exceptions import ValidationError

class EncuestaForm(forms.ModelForm):
    class Meta:
        model = Encuesta
        fields = ['titulo', 'descripcion', 'fecha_inicio', 'fecha_fin', 'activa', 'es_publica']
        widgets = {
            'fecha_inicio': forms.DateTimeInput(attrs={'type': 'datetime-local'}), 
            'fecha_fin': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'descripcion': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'titulo': 'Título de la encuesta',
            'descripcion': 'Descripción (opcional)',
            'fecha_inicio': 'Fecha y hora de inicio',
            'fecha_fin': 'Fecha y hora de finalización',
            'activa': 'Encuesta activa',
            'es_publica': 'Encuesta pública',
        }
        help_texts = {
            'es_publica': 'Si está marcada, cualquier usuario podrá responder sin necesidad de autenticarse',
        }

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')

        # Validar que la fecha de fin no sea anterior a la de inicio
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise ValidationError(
                "La fecha de finalización no puede ser anterior a la fecha de inicio"
            )

        # Validar que la fecha de inicio no sea en el pasado (si se está creando)
        if not self.instance.pk and fecha_inicio and fecha_inicio < timezone.now():
            raise ValidationError(
                "No puedes crear una encuesta con fecha de inicio en el pasado"
            )

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Añadir clases CSS a todos los campos
        for field in self.fields:
            if field not in ['activa', 'es_publica']:  # Excluir checkboxes
                self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # Estilos específicos para checkboxes
        self.fields['activa'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['es_publica'].widget.attrs.update({'class': 'form-check-input'})