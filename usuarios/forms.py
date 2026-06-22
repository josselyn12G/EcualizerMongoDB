from django import forms
from datetime import date
import re

from usuarios.models import Persona, Usuario, Artista, Administrador
from usuarios.mongo_service import (
    authenticate_user,
    user_exists,
    user_exists_excluding,
)

CODIGO_ADMINISTRADOR = 'ECUALIZER-ADMIN-2026'

PAISES = [
    ('', 'Selecciona tu país'),
    ('Argentina', 'Argentina'),
    ('Bolivia', 'Bolivia'),
    ('Brasil', 'Brasil'),
    ('Chile', 'Chile'),
    ('Colombia', 'Colombia'),
    ('Costa Rica', 'Costa Rica'),
    ('Cuba', 'Cuba'),
    ('Ecuador', 'Ecuador'),
    ('El Salvador', 'El Salvador'),
    ('España', 'España'),
    ('Estados Unidos', 'Estados Unidos'),
    ('Guatemala', 'Guatemala'),
    ('Honduras', 'Honduras'),
    ('México', 'México'),
    ('Nicaragua', 'Nicaragua'),
    ('Panamá', 'Panamá'),
    ('Paraguay', 'Paraguay'),
    ('Perú', 'Perú'),
    ('Puerto Rico', 'Puerto Rico'),
    ('República Dominicana', 'República Dominicana'),
    ('Uruguay', 'Uruguay'),
    ('Venezuela', 'Venezuela'),
    ('Otro', 'Otro'),
]


# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────

class AdminLoginForm(forms.Form):
    """Login exclusivo para administradores. Verifica tipo de cuenta ademas de credenciales."""
    correo = forms.EmailField(
        label='Correo del administrador',
        widget=forms.EmailInput(attrs={
            'class': 'eq-input admin-input',
            'placeholder': 'admin@ecualizer.com',
            'autocomplete': 'email',
            'autofocus': True,
        })
    )
    contrasena = forms.CharField(
        label='Contrasena',
        widget=forms.PasswordInput(attrs={
            'class': 'eq-input admin-input',
            'placeholder': '••••••••',
            'id': 'id_contrasena_admin',
            'autocomplete': 'current-password',
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._persona = None

    def clean(self):
        cleaned_data = super().clean()
        correo = cleaned_data.get('correo')
        contrasena = cleaned_data.get('contrasena')

        if correo and contrasena:
            persona, error = authenticate_user(
                correo,
                contrasena,
                expected_tipo='admin',
            )
            if error:
                raise forms.ValidationError(error)
            self._persona = persona
        return cleaned_data

    def get_persona(self):
        return getattr(self, '_persona', None)


class LoginForm(forms.Form):

    correo = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'class': 'eq-input',
            'placeholder': 'tu@correo.com',
            'autocomplete': 'email',
            'autofocus': True,
        })
    )

    contrasena = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'eq-input',
            'placeholder': '••••••••',
            'id': 'id_contrasena_login',
            'autocomplete': 'current-password',
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._persona = None

    def clean(self):
        cleaned_data = super().clean()
        correo = cleaned_data.get('correo')
        contrasena = cleaned_data.get('contrasena')

        if correo and contrasena:
            persona, error = authenticate_user(correo, contrasena)
            if error:
                raise forms.ValidationError(error)
            self._persona = persona

        return cleaned_data

    def get_persona(self):
        return getattr(self, '_persona', None)

# ─────────────────────────────────────────────
# REGISTRO — DATOS PERSONA (compartido)
# ─────────────────────────────────────────────

class RegistroPersonaForm(forms.Form):
    cedula_usuario = forms.CharField(
        label='Cédula',
        widget=forms.TextInput(attrs={
            'class': 'eq-input',
            'placeholder': '10 dígitos numéricos',
            'maxlength': '10',
            'inputmode': 'numeric',
            'pattern': '[0-9]{10}',
        })
    )
    primer_nombre = forms.CharField(label='Nombre', widget=forms.TextInput(attrs={'class': 'eq-input', 'placeholder': 'Primer nombre'}))
    segundo_nombre = forms.CharField(label='Segundo nombre', required=False, widget=forms.TextInput(attrs={'class': 'eq-input', 'placeholder': 'Segundo nombre (opcional)'}))
    primer_apellido = forms.CharField(label='Primer apellido', widget=forms.TextInput(attrs={'class': 'eq-input', 'placeholder': 'Primer apellido'}))
    segundo_apellido = forms.CharField(label='Segundo apellido', required=False, widget=forms.TextInput(attrs={'class': 'eq-input', 'placeholder': 'Segundo apellido (opcional)'}))
    correo = forms.EmailField(label='Correo', widget=forms.EmailInput(attrs={'class': 'eq-input', 'placeholder': 'tu@correo.com', 'autocomplete': 'email'}))
    contrasena = forms.CharField(label='Contraseña', min_length=8, widget=forms.PasswordInput(attrs={'class': 'eq-input', 'placeholder': 'Mínimo 8 caracteres', 'id': 'id_contrasena_reg', 'autocomplete': 'new-password'}))
    confirmar_contrasena = forms.CharField(label='Confirmar contraseña', widget=forms.PasswordInput(attrs={'class': 'eq-input', 'placeholder': 'Repite tu contraseña', 'autocomplete': 'new-password'}))

    def clean_cedula_usuario(self):
        cedula = self.cleaned_data.get('cedula_usuario', '').strip()
        if not re.match(r'^\d{10}$', cedula):
            raise forms.ValidationError(
                'La cédula debe tener exactamente 10 dígitos numéricos.'
            )
        if user_exists({'cedulaUsuario': cedula}):
            raise forms.ValidationError('Ya existe una cuenta registrada con esta cédula.')
        return cedula

    def clean_correo(self):
        correo = self.cleaned_data.get('correo', '').strip().lower()
        if user_exists({'correo': correo}):
            raise forms.ValidationError('Ya existe una cuenta registrada con este correo.')
        return correo

    def clean_primer_nombre(self):
        nombre = self.cleaned_data.get('primer_nombre', '').strip()
        if len(nombre) < 2:
            raise forms.ValidationError('El nombre debe tener al menos 2 caracteres.')
        return nombre

    def clean_primer_apellido(self):
        apellido = self.cleaned_data.get('primer_apellido', '').strip()
        if len(apellido) < 2:
            raise forms.ValidationError('El apellido debe tener al menos 2 caracteres.')
        return apellido

    def clean_segundo_nombre(self):
        nombre = (self.cleaned_data.get('segundo_nombre') or '').strip()
        if nombre and len(nombre) < 2:
            raise forms.ValidationError('El segundo nombre debe tener al menos 2 caracteres.')
        return nombre or None

    def clean_segundo_apellido(self):
        apellido = (self.cleaned_data.get('segundo_apellido') or '').strip()
        if apellido and len(apellido) < 2:
            raise forms.ValidationError('El segundo apellido debe tener al menos 2 caracteres.')
        return apellido or None

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('contrasena')
        p2 = cleaned_data.get('confirmar_contrasena')
        if p1 and p2 and p1 != p2:
            self.add_error('confirmar_contrasena', 'Las contraseñas no coinciden.')
        return cleaned_data


# ─────────────────────────────────────────────
# REGISTRO OYENTE
# ─────────────────────────────────────────────

class RegistroUsuarioForm(forms.Form):
    alias = forms.CharField(label='Alias', widget=forms.TextInput(attrs={'class': 'eq-input', 'placeholder': 'Tu alias visible (máx. 15 caracteres)', 'maxlength': '15'}))
    pais_usuario = forms.ChoiceField(choices=PAISES, label='País', widget=forms.Select(attrs={'class': 'eq-select'}))
    fecha_nacimiento = forms.DateField(label='Fecha de nacimiento', widget=forms.DateInput(attrs={'type': 'date', 'class': 'eq-input'}))
    genero = forms.ChoiceField(label='Género', choices=[('F', 'Femenino'), ('M', 'Masculino'), ('O', 'Otro')], widget=forms.RadioSelect(attrs={'class': 'eq-radio-group'}))

    def clean_alias(self):
        alias = self.cleaned_data.get('alias', '').strip()
        if len(alias) < 3:
            raise forms.ValidationError('El alias debe tener al menos 3 caracteres.')
        if len(alias) > 15:
            raise forms.ValidationError('El alias no puede superar los 15 caracteres.')
        if user_exists({'perfilOyente.alias': alias}):
            raise forms.ValidationError('Este alias ya está en uso.')
        return alias

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data.get('fecha_nacimiento')
        if fecha:
            today = date.today()
            age = (
                today.year - fecha.year
                - ((today.month, today.day) < (fecha.month, fecha.day))
            )
            if age < 13:
                raise forms.ValidationError(
                    'Debes tener al menos 13 años para registrarte.'
                )
        return fecha

    def clean_pais_usuario(self):
        pais = self.cleaned_data.get('pais_usuario', '')
        if not pais:
            raise forms.ValidationError('Selecciona tu país.')
        return pais


# ─────────────────────────────────────────────
# REGISTRO ARTISTA
# ─────────────────────────────────────────────

class RegistroArtistaForm(forms.Form):
    nombre_artistico = forms.CharField(label='Nombre artístico', widget=forms.TextInput(attrs={'class': 'eq-input', 'placeholder': 'Tu nombre artístico', 'maxlength': '40'}))
    biografia = forms.CharField(required=False, label='Biografía', widget=forms.Textarea(attrs={'class': 'eq-input eq-textarea', 'rows': 4, 'placeholder': 'Cuéntanos sobre ti y tu música (opcional)'}))

    def clean_nombre_artistico(self):
        nombre = self.cleaned_data.get('nombre_artistico', '').strip()
        if len(nombre) < 2:
            raise forms.ValidationError(
                'El nombre artístico debe tener al menos 2 caracteres.'
            )
        if user_exists({'perfilArtista.nombreArtistico': nombre}):
            raise forms.ValidationError('Este nombre artístico ya está en uso.')
        return nombre


# ─────────────────────────────────────────────
# REGISTRO ADMINISTRADOR
# ─────────────────────────────────────────────

class RegistroAdministradorForm(forms.Form):
    codigo_autorizacion = forms.CharField(
        label='Código de autorización',
        widget=forms.PasswordInput(attrs={
            'class': 'eq-input',
            'placeholder': 'Código de acceso administrativo',
        })
    )

    rol_admin = forms.ChoiceField(
        label='Rol',
        choices=[
            ('Administrador general', 'Administrador general'),
            ('Gestion de usuarios', 'Gestion de usuarios'),
            ('Moderador de contenido', 'Moderador de contenido'),
            ('Soporte tecnico', 'Soporte tecnico'),
        ],
        widget=forms.Select(attrs={'class': 'eq-select'})
    )
    departamento = forms.ChoiceField(
        label='Departamento',
        choices=[
            ('Contenido', 'Contenido'),
            ('Finanzas', 'Finanzas'),
            ('Operaciones', 'Operaciones'),
            ('Soporte', 'Soporte'),
            ('Tecnologia', 'Tecnologia'),
        ],
        widget=forms.Select(attrs={'class': 'eq-select'})
    )

    def clean_codigo_autorizacion(self):
        codigo = self.cleaned_data.get('codigo_autorizacion', '')
        if codigo != CODIGO_ADMINISTRADOR:
            raise forms.ValidationError('Código de autorización incorrecto.')
        return codigo


# ─────────────────────────────────────────────
# CRUD ADMIN (uso interno / panel administrativo)
# ─────────────────────────────────────────────

class PersonaForm(forms.ModelForm):
    class Meta:
        model = Persona
        fields = [
            'cedula_usuario', 'primer_nombre', 'segundo_nombre',
            'primer_apellido', 'segundo_apellido', 'correo', 'contrasena', 'estado',
        ]
        widgets = {
            'contrasena': forms.PasswordInput(),
        }


class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['id_usuario', 'alias', 'pais_usuario', 'fecha_nacimiento', 'genero']
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
        }


class ArtistaForm(forms.ModelForm):
    class Meta:
        model = Artista
        fields = ['id_usuario', 'nombre_artistico', 'biografia']


class AdministradorForm(forms.ModelForm):
    class Meta:
        model = Administrador
        fields = ['id_usuario', 'rol_admin', 'departamento']


# ─────────────────────────────────────────────
# FORMULARIOS DE EDICION — Panel de administracion
# ─────────────────────────────────────────────

_INPUT = {'class': 'eq-input form-control'}
_SELECT = {'class': 'eq-select form-select'}


class AdminEditPersonaForm(forms.ModelForm):
    """Edita datos de Persona. La contrasena se maneja aparte en la vista."""
    class Meta:
        model = Persona
        fields = [
            'cedula_usuario', 'primer_nombre', 'segundo_nombre',
            'primer_apellido', 'segundo_apellido', 'correo', 'estado',
        ]
        widgets = {
            'cedula_usuario':  forms.TextInput(attrs={**_INPUT, 'maxlength': '10', 'inputmode': 'numeric'}),
            'primer_nombre':   forms.TextInput(attrs=_INPUT),
            'segundo_nombre':  forms.TextInput(attrs=_INPUT),
            'primer_apellido': forms.TextInput(attrs=_INPUT),
            'segundo_apellido': forms.TextInput(attrs=_INPUT),
            'correo':          forms.EmailInput(attrs=_INPUT),
            'estado':          forms.Select(attrs=_SELECT),
        }

    def clean_cedula_usuario(self):
        cedula = self.cleaned_data.get('cedula_usuario', '').strip()
        if not re.match(r'^\d{10}$', cedula):
            raise forms.ValidationError('La cedula debe tener exactamente 10 digitos numericos.')
        qs = Persona.objects.filter(cedula_usuario=cedula)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Ya existe una cuenta con esta cedula.')
        return cedula

    def clean_correo(self):
        correo = self.cleaned_data.get('correo', '').strip().lower()
        qs = Persona.objects.filter(correo=correo)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Ya existe una cuenta con este correo.')
        return correo

    def clean_primer_nombre(self):
        nombre = self.cleaned_data.get('primer_nombre', '').strip()
        if len(nombre) < 2:
            raise forms.ValidationError('El nombre debe tener al menos 2 caracteres.')
        return nombre

    def clean_primer_apellido(self):
        apellido = self.cleaned_data.get('primer_apellido', '').strip()
        if len(apellido) < 2:
            raise forms.ValidationError('El apellido debe tener al menos 2 caracteres.')
        return apellido

    def clean_segundo_nombre(self):
        nombre = (self.cleaned_data.get('segundo_nombre') or '').strip()
        if nombre and len(nombre) < 2:
            raise forms.ValidationError('El segundo nombre debe tener al menos 2 caracteres.')
        return nombre or None

    def clean_segundo_apellido(self):
        apellido = (self.cleaned_data.get('segundo_apellido') or '').strip()
        if apellido and len(apellido) < 2:
            raise forms.ValidationError('El segundo apellido debe tener al menos 2 caracteres.')
        return apellido or None


class AdminEditUsuarioForm(forms.ModelForm):
    pais_usuario = forms.ChoiceField(choices=PAISES, label='Pais', widget=forms.Select(attrs=_SELECT))

    class Meta:
        model = Usuario
        fields = ['alias', 'pais_usuario', 'fecha_nacimiento', 'genero']
        widgets = {
            'alias':           forms.TextInput(attrs={**_INPUT, 'maxlength': '15'}),
            'fecha_nacimiento': forms.DateInput(attrs={**_INPUT, 'type': 'date'}),
            'genero':          forms.Select(attrs=_SELECT),
        }

    def clean_alias(self):
        alias = self.cleaned_data.get('alias', '').strip()
        if len(alias) < 3:
            raise forms.ValidationError('El alias debe tener al menos 3 caracteres.')
        qs = Usuario.objects.filter(alias=alias)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Este alias ya esta en uso.')
        return alias


class AdminEditArtistaForm(forms.ModelForm):
    class Meta:
        model = Artista
        fields = ['nombre_artistico', 'biografia']
        widgets = {
            'nombre_artistico': forms.TextInput(attrs={**_INPUT, 'maxlength': '40'}),
            'biografia':        forms.Textarea(attrs={**_INPUT, 'rows': 4}),
        }

    def clean_nombre_artistico(self):
        nombre = self.cleaned_data.get('nombre_artistico', '').strip()
        if len(nombre) < 2:
            raise forms.ValidationError('El nombre artistico debe tener al menos 2 caracteres.')
        qs = Artista.objects.filter(nombre_artistico=nombre)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Este nombre artistico ya esta en uso.')
        return nombre


class AdminEditAdministradorForm(forms.ModelForm):
    class Meta:
        model = Administrador
        fields = ['rol_admin', 'departamento']
        widgets = {
            'rol_admin':    forms.Select(attrs=_SELECT),
            'departamento': forms.Select(attrs=_SELECT),
        }


# ─────────────────────────────────────────────
# PERFIL DEL OYENTE — edición de sus propios datos
# ─────────────────────────────────────────────

class PerfilPersonaForm(AdminEditPersonaForm):
    """Datos personales editables por el propio oyente.

    Reutiliza las validaciones de AdminEditPersonaForm pero SIN el campo
    'estado' (un usuario no puede cambiar su propio estado) y con la
    cédula en solo-lectura (no se modifica)."""

    class Meta(AdminEditPersonaForm.Meta):
        fields = [
            'cedula_usuario', 'primer_nombre', 'segundo_nombre',
            'primer_apellido', 'segundo_apellido', 'correo',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # La cédula se muestra pero no se puede modificar.
        self.fields['cedula_usuario'].disabled = True


class PerfilUsuarioForm(AdminEditUsuarioForm):
    """Datos de perfil de oyente (alias, país, nacimiento, género)
    editables por el propio usuario. Reutiliza AdminEditUsuarioForm."""


# ─────────────────────────────────────────────
# PANEL DE ADMINISTRACIÓN · Formularios sobre MongoDB
# ----------------------------------------------------
# Versiones en forms.Form (sin ORM) usadas por el panel admin para editar
# usuarios almacenados en MongoDB. Validan unicidad contra Mongo excluyendo
# el propio registro (se les pasa pk=<ObjectId str> al instanciar).
# ─────────────────────────────────────────────

ESTADO_CHOICES = [
    ('activo', 'Activo'),
    ('inactivo', 'Inactivo'),
    ('suspendido', 'Suspendido'),
]
GENERO_CHOICES = [('F', 'Femenino'), ('M', 'Masculino'), ('O', 'Otro')]
ROL_ADMIN_CHOICES = [
    ('Administrador general', 'Administrador general'),
    ('Gestion de usuarios', 'Gestion de usuarios'),
    ('Moderador de contenido', 'Moderador de contenido'),
    ('Soporte tecnico', 'Soporte tecnico'),
]
DEPARTAMENTO_CHOICES = [
    ('Contenido', 'Contenido'),
    ('Finanzas', 'Finanzas'),
    ('Operaciones', 'Operaciones'),
    ('Soporte', 'Soporte'),
    ('Tecnologia', 'Tecnologia'),
]


class _MongoPkFormMixin:
    """Guarda el pk del usuario que se edita para excluirlo en la unicidad."""
    def __init__(self, *args, pk=None, **kwargs):
        self.pk = pk
        super().__init__(*args, **kwargs)


class MongoAdminPersonaForm(_MongoPkFormMixin, forms.Form):
    """Datos personales (comunes) de un usuario de MongoDB."""
    cedula_usuario = forms.CharField(label='Cedula', widget=forms.TextInput(attrs={**_INPUT, 'maxlength': '10', 'inputmode': 'numeric'}))
    primer_nombre = forms.CharField(label='Primer nombre', widget=forms.TextInput(attrs=_INPUT))
    segundo_nombre = forms.CharField(label='Segundo nombre', required=False, widget=forms.TextInput(attrs=_INPUT))
    primer_apellido = forms.CharField(label='Primer apellido', widget=forms.TextInput(attrs=_INPUT))
    segundo_apellido = forms.CharField(label='Segundo apellido', required=False, widget=forms.TextInput(attrs=_INPUT))
    correo = forms.EmailField(label='Correo', widget=forms.EmailInput(attrs=_INPUT))
    estado = forms.ChoiceField(label='Estado', choices=ESTADO_CHOICES, widget=forms.Select(attrs=_SELECT))

    def clean_cedula_usuario(self):
        cedula = self.cleaned_data.get('cedula_usuario', '').strip()
        if not re.match(r'^\d{10}$', cedula):
            raise forms.ValidationError('La cedula debe tener exactamente 10 digitos numericos.')
        if user_exists_excluding({'cedulaUsuario': cedula}, self.pk):
            raise forms.ValidationError('Ya existe una cuenta con esta cedula.')
        return cedula

    def clean_correo(self):
        correo = self.cleaned_data.get('correo', '').strip().lower()
        if user_exists_excluding({'correo': correo}, self.pk):
            raise forms.ValidationError('Ya existe una cuenta con este correo.')
        return correo

    def clean_primer_nombre(self):
        nombre = self.cleaned_data.get('primer_nombre', '').strip()
        if len(nombre) < 2:
            raise forms.ValidationError('El nombre debe tener al menos 2 caracteres.')
        return nombre

    def clean_primer_apellido(self):
        apellido = self.cleaned_data.get('primer_apellido', '').strip()
        if len(apellido) < 2:
            raise forms.ValidationError('El apellido debe tener al menos 2 caracteres.')
        return apellido


class MongoAdminOyenteForm(_MongoPkFormMixin, forms.Form):
    """Perfil de oyente editable desde el panel admin."""
    alias = forms.CharField(label='Alias', widget=forms.TextInput(attrs={**_INPUT, 'maxlength': '15'}))
    pais_usuario = forms.ChoiceField(label='Pais', choices=PAISES, widget=forms.Select(attrs=_SELECT))
    fecha_nacimiento = forms.DateField(label='Fecha de nacimiento', widget=forms.DateInput(attrs={**_INPUT, 'type': 'date'}))
    genero = forms.ChoiceField(label='Genero', choices=GENERO_CHOICES, widget=forms.Select(attrs=_SELECT))

    def clean_alias(self):
        alias = self.cleaned_data.get('alias', '').strip()
        if len(alias) < 3:
            raise forms.ValidationError('El alias debe tener al menos 3 caracteres.')
        if user_exists_excluding({'perfilOyente.alias': alias}, self.pk):
            raise forms.ValidationError('Este alias ya esta en uso.')
        return alias


class MongoAdminArtistaForm(_MongoPkFormMixin, forms.Form):
    """Perfil de artista editable desde el panel admin."""
    nombre_artistico = forms.CharField(label='Nombre artistico', widget=forms.TextInput(attrs={**_INPUT, 'maxlength': '40'}))
    biografia = forms.CharField(label='Biografia', required=False, widget=forms.Textarea(attrs={**_INPUT, 'rows': 4}))

    def clean_nombre_artistico(self):
        nombre = self.cleaned_data.get('nombre_artistico', '').strip()
        if len(nombre) < 2:
            raise forms.ValidationError('El nombre artistico debe tener al menos 2 caracteres.')
        if user_exists_excluding({'perfilArtista.nombreArtistico': nombre}, self.pk):
            raise forms.ValidationError('Este nombre artistico ya esta en uso.')
        return nombre


class MongoAdminAdministradorForm(_MongoPkFormMixin, forms.Form):
    """Datos administrativos editables desde el panel admin."""
    rol_admin = forms.ChoiceField(label='Rol', choices=ROL_ADMIN_CHOICES, widget=forms.Select(attrs=_SELECT))
    departamento = forms.ChoiceField(label='Departamento', choices=DEPARTAMENTO_CHOICES, widget=forms.Select(attrs=_SELECT))


class MongoPerfilPersonaForm(MongoAdminPersonaForm):
    """Datos personales editables por el PROPIO usuario (oyente/artista):
    sin el campo 'estado' (no puede cambiar su estado) y con la cédula en
    solo lectura. Reutiliza las validaciones de MongoAdminPersonaForm."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('estado', None)
        self.fields['cedula_usuario'].disabled = True
