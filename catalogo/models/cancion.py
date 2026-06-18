"""
Modelo Cancion — refleja [Catalogo].[Cancion]

CHECKs del SQL:
  - duracion > 0
  - estadoCancion IN ('activa', 'bloqueada', 'eliminada', 'inactiva')
  - calidadKbps IN (128, 192, 256, 320)
  - totalReproducciones >= 0
  - numeroPista > 0
"""

from django.db import models
from django.core.validators import MinValueValidator

from .album import Album
from .genero_musical import GeneroMusical


class Cancion(models.Model):
    ESTADO_CHOICES = [
        ('activa',    'Activa'),
        ('inactiva',  'Inactiva'),
        ('bloqueada', 'Bloqueada'),
        ('eliminada', 'Eliminada'),
    ]

    CALIDAD_CHOICES = [
        (128, '128 kbps'),
        (192, '192 kbps'),
        (256, '256 kbps'),
        (320, '320 kbps'),
    ]

    id_cancion = models.AutoField(
        db_column='idCancion',
        primary_key=True,
    )
    nombre_cancion = models.CharField(
        db_column='nombreCancion',
        max_length=150,
    )
    duracion = models.SmallIntegerField(
        db_column='duracion',
        validators=[MinValueValidator(1)],
        help_text='Duración en segundos',
    )
    fecha_lanzamiento = models.DateField(
        db_column='fechaLanzamiento',
    )
    estado_cancion = models.CharField(
        db_column='estadoCancion',
        max_length=20,
        choices=ESTADO_CHOICES,
        default='activa',
    )
    calidad_kbps = models.SmallIntegerField(
        db_column='calidadKbps',
        choices=CALIDAD_CHOICES,
        default=192,
    )
    total_reproducciones = models.BigIntegerField(
        db_column='totalReproducciones',
        default=0,
        validators=[MinValueValidator(0)],
    )
    letra_cancion = models.TextField(
        db_column='letraCancion',
        blank=True,
        null=True,
    )
    album = models.ForeignKey(
        Album,
        db_column='Album_idAlbum',
        on_delete=models.DO_NOTHING,
        related_name='canciones',
    )
    numero_pista = models.SmallIntegerField(
        db_column='numeroPista',
        validators=[MinValueValidator(1)],
    )

    # Relación M:N con GeneroMusical mediante la tabla intermedia
    generos = models.ManyToManyField(
        GeneroMusical,
        through='CancionGeneroMusical',
        related_name='canciones',
        blank=True,
    )

    class Meta:
        managed = False
        db_table = '[Catalogo].[Cancion]'
        ordering = ['album', 'numero_pista']
        verbose_name = 'Canción'
        verbose_name_plural = 'Canciones'

    def __str__(self):
        return self.nombre_cancion

    @property
    def es_activa(self):
        return self.estado_cancion == 'activa'

    @property
    def duracion_formateada(self):
        """Devuelve la duración en formato mm:ss."""
        minutos = self.duracion // 60
        segundos = self.duracion % 60
        return f'{minutos:02d}:{segundos:02d}'

    @property
    def artista(self):
        """Atajo: artista propietario via el álbum."""
        return self.album.artista
