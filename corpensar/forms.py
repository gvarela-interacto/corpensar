from django import forms
from .models import *
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

class RespuestaForm(forms.Form):
    def __init__(self, encuesta, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.encuesta = encuesta
        for pregunta in self.encuesta.preguntaopcionmultiple_relacionadas.all():
            choices = [(opcion.id, opcion.texto) for opcion in pregunta.opciones.all()]
            if pregunta.opcion_otro:
                choices.append(('otro', pregunta.texto_otro))
            self.fields[f'pregunta_{pregunta.id}'] = forms.ChoiceField(
                label=pregunta.texto,
                choices=choices,
                widget=forms.RadioSelect,
                required=pregunta.requerida
            )
            if pregunta.opcion_otro:
                self.fields[f'otro_{pregunta.id}'] = forms.CharField(
                    label=pregunta.texto_otro,
                    required=False,
                    widget=forms.TextInput(attrs={'style': 'display: none;'}),
                )

        for pregunta in self.encuesta.preguntacasillasverificacion_relacionadas.all():
            choices = [(opcion.id, opcion.texto) for opcion in pregunta.opciones.all()]
            if pregunta.opcion_otro:
                choices.append(('otro', pregunta.texto_otro))
            self.fields[f'pregunta_{pregunta.id}'] = forms.MultipleChoiceField(
                label=pregunta.texto,
                choices=choices,
                widget=forms.CheckboxSelectMultiple,
                required=pregunta.requerida
            )
            if pregunta.opcion_otro:
                self.fields[f'otro_{pregunta.id}'] = forms.CharField(
                    label=pregunta.texto_otro,
                    required=False,
                    widget=forms.TextInput(attrs={'style': 'display: none;'}),
                )

        for pregunta in PreguntaMenuDesplegable.objects.filter(encuesta=self.encuesta):
            choices = [(opcion.id, opcion.texto) for opcion in pregunta.opciones.all()]
            if pregunta.opcion_vacia:
                choices = [('', pregunta.texto_vacio)] + choices
            self.fields[f'pregunta_{pregunta.id}'] = forms.ChoiceField(
                label=pregunta.texto,
                choices=choices,
                widget=forms.Select,
                required=pregunta.requerida
            )

        for pregunta in self.encuesta.preguntatexto_relacionadas.all():
            self.fields[f'pregunta_{pregunta.id}'] = forms.CharField(
                label=pregunta.texto,
                max_length=pregunta.max_longitud,
                widget=forms.TextInput(attrs={'placeholder': pregunta.placeholder}),
                required=pregunta.requerida
            )

        for pregunta in self.encuesta.preguntatextomultiple_relacionadas.all():
            self.fields[f'pregunta_{pregunta.id}'] = forms.CharField(
                label=pregunta.texto,
                widget=forms.Textarea(attrs={'rows': pregunta.filas, 'placeholder': pregunta.placeholder}),
                required=pregunta.requerida
            )

        for pregunta in self.encuesta.preguntaestrellas_relacionadas.all():
            choices = [(i, str(i)) for i in range(1, pregunta.max_estrellas + 1)]
            self.fields[f'pregunta_{pregunta.id}'] = forms.ChoiceField(
                label=pregunta.texto,
                choices=choices,
                widget=forms.RadioSelect,
                required=pregunta.requerida
            )

        for pregunta in self.encuesta.preguntaescala_relacionadas.all():
            choices = [(i, str(i)) for i in range(pregunta.min_valor, pregunta.max_valor + 1, pregunta.paso)]
            self.fields[f'pregunta_{pregunta.id}'] = forms.ChoiceField(
                label=pregunta.texto,
                choices=choices,
                widget=forms.RadioSelect,
                required=pregunta.requerida
            )

        for pregunta in self.encuesta.preguntamatriz_relacionadas.all():
            for item in pregunta.items.all():
                choices = [(i, str(i)) for i in range(pregunta.escala.min_valor, pregunta.escala.max_valor + 1, pregunta.escala.paso)]
                self.fields[f'pregunta_{pregunta.id}_item_{item.id}'] = forms.ChoiceField(
                    label=item.texto,
                    choices=choices,
                    widget=forms.RadioSelect,
                    required=pregunta.requerida
                )

        for pregunta in self.encuesta.preguntafecha_relacionadas.all():
            if pregunta.incluir_hora:
                self.fields[f'pregunta_{pregunta.id}'] = forms.DateTimeField(
                    label=pregunta.texto,
                    widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
                    required=pregunta.requerida
                )
            else:
                self.fields[f'pregunta_{pregunta.id}'] = forms.DateField(
                    label=pregunta.texto,
                    widget=forms.DateInput(attrs={'type': 'date'}),
                    required=pregunta.requerida
                    )