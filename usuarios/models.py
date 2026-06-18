from django.db import models


class Persona(models.Model):
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('suspendido', 'Suspendido'),
    ]

    id_usuario = models.AutoField(
        db_column='idUsuario',
        primary_key=True
    )
    cedula_usuario = models.CharField(
        db_column='cedulaUsuario',
        max_length=10,
        unique=True
    )
    primer_nombre = models.CharField(
        db_column='primerNombre',
        max_length=40
    )
    segundo_nombre = models.CharField(
        db_column='segundoNombre',
        max_length=40,
        blank=True,
        null=True
    )
    primer_apellido = models.CharField(
        db_column='primerApellido',
        max_length=40
    )
    segundo_apellido = models.CharField(
        db_column='segundoApellido',
        max_length=40,
        blank=True,
        null=True
    )
    correo = models.EmailField(
        db_column='correo',
        max_length=150,
        unique=True
    )
    contrasena = models.CharField(
        db_column='contrasena',
        max_length=255
    )
    fecha_registro = models.DateField(
        db_column='fechaRegistro',
        blank=True,
        null=True
    )
    estado = models.CharField(
        db_column='estado',
        max_length=20,
        choices=ESTADO_CHOICES,
        default='activo'
    )

    class Meta:
        managed = False
        db_table = '[Usuario].[Persona]'

    def __str__(self):
        return f'{self.primer_nombre} {self.primer_apellido}'


class Usuario(models.Model):
    GENERO_CHOICES = [
        ('F', 'Femenino'),
        ('M', 'Masculino'),
        ('O', 'Otro'),
    ]

    id_usuario = models.OneToOneField(
        Persona,
        db_column='idUsuario',
        primary_key=True,
        on_delete=models.DO_NOTHING
    )
    alias = models.CharField(
        db_column='alias',
        max_length=15
    )
    pais_usuario = models.CharField(
        db_column='paisUsuario',
        max_length=50
    )
    fecha_nacimiento = models.DateField(
        db_column='fechaNacimiento'
    )
    genero = models.CharField(
        db_column='genero',
        max_length=1,
        choices=GENERO_CHOICES
    )

    class Meta:
        managed = False
        db_table = '[Usuario].[Usuario]'

    def __str__(self):
        return self.alias


class Artista(models.Model):
    id_usuario = models.OneToOneField(
        Persona,
        db_column='idUsuario',
        primary_key=True,
        on_delete=models.DO_NOTHING
    )
    nombre_artistico = models.CharField(
        db_column='nombreArtistico',
        max_length=40,
        unique=True
    )
    biografia = models.TextField(
        db_column='biografia',
        blank=True,
        null=True
    )

    class Meta:
        managed = False
        db_table = '[Usuario].[Artista]'

    def __str__(self):
        return self.nombre_artistico


class Administrador(models.Model):
    ROL_ADMIN_CHOICES = [
        ('Administrador general', 'Administrador general'),
        ('Gestion de usuarios', 'Gestión de usuarios'),
        ('Moderador de contenido', 'Moderador de contenido'),
        ('Soporte tecnico', 'Soporte técnico'),
    ]

    DEPARTAMENTO_CHOICES = [
        ('Contenido', 'Contenido'),
        ('Finanzas', 'Finanzas'),
        ('Operaciones', 'Operaciones'),
        ('Soporte', 'Soporte'),
        ('Tecnología', 'Tecnología'),
    ]

    id_usuario = models.OneToOneField(
        Persona,
        db_column='idUsuario',
        primary_key=True,
        on_delete=models.DO_NOTHING
    )
    rol_admin = models.CharField(
        db_column='rolAdmin',
        max_length=30,
        choices=ROL_ADMIN_CHOICES,
        default='Administrador general'
    )
    departamento = models.CharField(
        db_column='departamento',
        max_length=50,
        choices=DEPARTAMENTO_CHOICES
    )

    class Meta:
        managed = False
        db_table = '[Usuario].[Administrador]'

    def __str__(self):
        return f'{self.id_usuario} - {self.rol_admin}'