"""
Catálogo de tarifas por país (USD por reproducción).

Espejo del catálogo SQL `Analitica.TasaPorPais`. Se mantiene aquí para
que el código Python pueda mostrar / referenciar la tarifa esperada sin
hacer un round-trip a la base. La fuente de verdad para el cálculo de
regalías sigue siendo la tabla SQL — esta constante es solo informativa.
"""

TARIFA_BASE_PAIS: float = 0.004  # fallback cuando un país no figura

TARIFAS_POR_PAIS: dict[str, float] = {
    'Estados Unidos': 0.0050,
    'Reino Unido':    0.0048,
    'España':         0.0045,
    'Alemania':       0.0045,
    'Francia':        0.0045,
    'México':         0.0040,
    'Brasil':         0.0040,
    'Argentina':      0.0035,
    'Chile':          0.0035,
    'Uruguay':        0.0035,
    'Colombia':       0.0032,
    'Perú':           0.0030,
    'Ecuador':        0.0030,
    'Venezuela':      0.0028,
    'Bolivia':        0.0028,
    'Paraguay':       0.0028,
}


def tarifa_pais(pais: str | None) -> float:
    """Devuelve la tarifa por reproducción para `pais`, o la base si no figura."""
    if not pais:
        return TARIFA_BASE_PAIS
    return TARIFAS_POR_PAIS.get(pais, TARIFA_BASE_PAIS)
