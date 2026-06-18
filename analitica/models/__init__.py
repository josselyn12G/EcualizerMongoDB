"""
Modelos de la app `analitica` — reflejan el esquema [Analitica] de SQL Server.

Tablas:
  - [Analitica].[Reproduccion] → modelo `Reproduccion`
  - [Analitica].[Regalia]      → modelo `Regalia`

Las cargas (INSERT) las hace SP_RegistrarReproduccion / SPs de regalías;
desde Django los usamos sobre todo en modo lectura para reportes/analítica.
"""

from .reproduccion import Reproduccion
from .regalia import Regalia

__all__ = ['Reproduccion', 'Regalia']
