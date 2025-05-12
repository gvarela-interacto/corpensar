from django import forms
from .models import *
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

class EncuestaForm(forms.ModelForm):
    class Meta:
        model = Encuesta
        fields = ['titulo', 'descripcion', 'fecha_inicio', 'fecha_fin', 'activa', 'es_publica', 'tema', 'region', 'categoria', 'subcategoria', 'grupo_interes']
        widgets = {
            'fecha_inicio': forms.DateTimeInput(attrs={'type': 'datetime-local'}), 
            'fecha_fin': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'tema': forms.Select(attrs={'class': 'form-control'}),
            'region': forms.Select(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-control'}),
            'subcategoria': forms.Select(attrs={'class': 'form-control'}),
            'grupo_interes': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'titulo': 'Título de la encuesta',
            'descripcion': 'Descripción (opcional)',
            'fecha_inicio': 'Fecha y hora de inicio',
            'fecha_fin': 'Fecha y hora de finalización',
            'activa': 'Encuesta activa',
            'es_publica': 'Encuesta pública',
            'tema': 'Tema de la encuesta',
            'region': 'Región',
            'categoria': 'Categoría',
            'subcategoria': 'Subcategoría',
            'grupo_interes': 'Grupo de Interés',
        }
        help_texts = {
            'es_publica': 'Si está marcada, cualquier usuario podrá responder sin necesidad de autenticarse',
            'region': 'Selecciona la región asociada a esta encuesta',
            'subcategoria': 'Selecciona la subcategoría de la encuesta',
            'grupo_interes': 'Selecciona el grupo de interés relacionado con esta encuesta',
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

class PQRSFDForm(forms.ModelForm):
    """Formulario para crear un nuevo PQRSFD"""
    
    archivos = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        label="Archivos adjuntos",
        help_text="Seleccione los archivos a adjuntar (uno a la vez)"
    )
    
    class Meta:
        model = PQRSFD
        fields = ['tipo', 'nombre', 'email', 'telefono', 'asunto', 'descripcion', 'es_anonimo']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Su nombre completo'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Su correo electrónico'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Su número de teléfono'}),
            'asunto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Asunto de su solicitud'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Describa detalladamente su solicitud'}),
            'es_anonimo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Añadir clases de Bootstrap y hacer que algunos campos no sean requeridos
        self.fields['nombre'].required = False
        self.fields['email'].required = False
        self.fields['telefono'].required = False
        
        # Cambiar las etiquetas para mejor UX
        self.fields['tipo'].label = "Tipo de solicitud"
        self.fields['es_anonimo'].label = "Enviar de forma anónima"
        
        # Añadir help_text
        self.fields['es_anonimo'].help_text = "Si marca esta opción, no se guardará su información personal"
        
    def clean(self):
        cleaned_data = super().clean()
        es_anonimo = cleaned_data.get('es_anonimo')
        nombre = cleaned_data.get('nombre')
        email = cleaned_data.get('email')
        
        # Si no es anónimo, validar que nombre y email estén presentes
        if not es_anonimo:
            if not nombre:
                self.add_error('nombre', 'El nombre es requerido cuando no es anónimo.')
            if not email:
                self.add_error('email', 'El correo electrónico es requerido cuando no es anónimo.')
        
        return cleaned_data

class CrearUsuarioForm(forms.Form):
    """Formulario para crear un nuevo usuario por parte de un administrador"""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario'}),
        help_text="Requerido. 150 caracteres o menos. Solo letras, números y @/./+/-/_"
    )
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'}),
        required=False
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido'}),
        required=False
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo electrónico'})
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'}),
        label="Contraseña"
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmar contraseña'}),
        label="Confirmar contraseña"
    )
    is_admin = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Es administrador"
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Este nombre de usuario ya está en uso.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está en uso.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            self.add_error('password2', "Las contraseñas no coinciden.")

        return cleaned_data

    def save(self):
        username = self.cleaned_data.get('username')
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password1')
        first_name = self.cleaned_data.get('first_name', '')
        last_name = self.cleaned_data.get('last_name', '')
        is_admin = self.cleaned_data.get('is_admin', False)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        # Si es administrador, asignar permisos de staff y superusuario
        if is_admin:
            user.is_staff = True
            user.is_superuser = True
            user.save()

        return user

class CaracterizacionMunicipalForm(forms.ModelForm):
    class Meta:
        model = CaracterizacionMunicipal
        exclude = ['creador', 'fecha_creacion', 'fecha_actualizacion']
        widgets = {
            'municipio': forms.Select(attrs={'class': 'form-control select2'}),
            'nombre_alcalde': forms.TextInput(attrs={'class': 'form-control'}),
            'periodo_gobierno': forms.TextInput(attrs={'class': 'form-control'}),
            'poblacion_total': forms.NumberInput(attrs={'class': 'form-control'}),
            'poblacion_urbana': forms.NumberInput(attrs={'class': 'form-control'}),
            'poblacion_rural': forms.NumberInput(attrs={'class': 'form-control'}),
            'extension_territorial': forms.NumberInput(attrs={'class': 'form-control'}),
            'altitud': forms.NumberInput(attrs={'class': 'form-control'}),
            'temperatura_promedio': forms.NumberInput(attrs={'class': 'form-control'}),
            'principales_actividades_economicas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'numero_escuelas': forms.NumberInput(attrs={'class': 'form-control'}),
            'numero_centros_salud': forms.NumberInput(attrs={'class': 'form-control'}),
            'cobertura_agua_potable': forms.NumberInput(attrs={'class': 'form-control'}),
            'cobertura_energia_electrica': forms.NumberInput(attrs={'class': 'form-control'}),
            'cobertura_alcantarillado': forms.NumberInput(attrs={'class': 'form-control'}),
            'resena_historica': forms.Textarea(attrs={'class': 'form-control rich-editor', 'rows': 4}),
            'sitios_turisticos': forms.Textarea(attrs={'class': 'form-control rich-editor', 'rows': 4}),
            'fiestas_tradicionales': forms.Textarea(attrs={'class': 'form-control rich-editor', 'rows': 4}),
            'direccion_alcaldia': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono_alcaldia': forms.TextInput(attrs={'class': 'form-control'}),
            'sitio_web': forms.URLInput(attrs={'class': 'form-control'}),
            'email_contacto': forms.EmailInput(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['municipio'].empty_label = "Seleccione un municipio"
        
        # Hacer algunos campos opcionales
        for field in self.fields:
            if field not in ['municipio']:
                self.fields[field].required = False


class DocumentoCaracterizacionForm(forms.ModelForm):
    class Meta:
        model = DocumentoCaracterizacion
        fields = ['titulo', 'descripcion', 'archivo']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'archivo': forms.FileInput(attrs={'class': 'form-control-file'}),
        }