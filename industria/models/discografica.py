"""
Modelo Discografica — refleja [Industria].[Discografica]

CHECKs replicados del DDL:
  - correoContacto LIKE '%@%.%'
  - telefonoContacto: exactamente 10 dígitos numéricos
  - nombreDiscografica UNIQUE
"""

import re
from django.db import models
from django.core.exceptions import ValidationError


def _validar_correo(value: str):
    if not value or '@' not in value or '.' not in value.split('@')[-1]:
        raise ValidationError('Formato de correo inválido.')


def _validar_telefono(value: str):
    if not re.fullmatch(r'\d{10}', value or ''):
        raise ValidationError('El teléfono debe tener exactamente 10 dígitos numéricos.')


class Discografica(models.Model):
    id_discografica = models.AutoField(
        db_column='idDiscografica',
        primary_key=True,
    )
    nombre_discografica = models.CharField(
        db_column='nombreDiscografica',
        max_length=150,
        unique=True,
    )
    pais_origen = models.CharField(
        db_column='paisOrigen',
        max_length=50,
        blank=True, null=True,
    )
    correo_contacto = models.CharField(
        db_column='correoContacto',
        max_length=150,
        validators=[_validar_correo],
    )
    telefono_contacto = models.CharField(
        db_column='telefonoContacto',
        max_length=10,
        validators=[_validar_telefono],
        help_text='10 dígitos numéricos.',
    )

    class Meta:
        managed = False
        db_table = '[Industria].[Discografica]'
        ordering = ['nombre_discografica']
        verbose_name = 'Discográfica'
        verbose_name_plural = 'Discográficas'

    def __str__(self):
        return self.nombre_discografica
