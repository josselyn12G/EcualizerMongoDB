"""
Servicios de analítica — wrappers a stored procedures.

Estructura preparada para soportar dashboards de varios roles:
  - admin_service   → SPs del Dashboard del Administrador
  - artista_service → métricas individuales del artista logueado

Cada wrapper devuelve list[dict] o dict, listo para pasar a un template.
"""

from .admin_service import *  # noqa: F401,F403
from . import artista_service  # noqa: F401
