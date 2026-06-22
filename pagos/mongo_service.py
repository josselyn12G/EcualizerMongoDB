"""
Servicio de datos del módulo de PAGOS sobre MongoDB Atlas.

Reusa la conexión centralizada de `usuarios.mongo_service` (config/credenciales.json).
Colecciones (ver scripts/Creación de Base NOSQL/Hackolade):
  • Plan         → catálogo de planes (planId, nombrePlan, precio, duracion, descripcionPlan)
  • Suscripcion  → contrato del usuario; embebe un snapshot `plan` {planId, nombrePlan, precio}
  • Pagos        → transacciones; embebe `usuario` {usuarioId, primerNombre, primerApellido}

Las funciones devuelven las MISMAS claves que esperan las plantillas (que
fueron escritas para el modelo SQL), por lo que el HTML casi no cambia.
"""

from datetime import datetime, timedelta, timezone

from bson import ObjectId
from django.core.cache import cache

from usuarios.mongo_service import get_database

_PLANES_CACHE_KEY = 'pagos:catalogo_planes'


# ── Colecciones ───────────────────────────────────────────────────────
def _col(nombre):
    return get_database()[nombre]


def planes_col():        return _col('Plan')
def suscripciones_col(): return _col('Suscripcion')
def pagos_col():         return _col('Pagos')
def usuarios_col():      return _col('Usuarios')


MESES_ES = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']


# ── Helpers ───────────────────────────────────────────────────────────
def _oid(value):
    """Convierte a ObjectId si es válido; si no, None."""
    value = str(value) if value is not None else ''
    return ObjectId(value) if ObjectId.is_valid(value) else None


def _fmt_fecha(value):
    """Formatea fechas a dd/mm/aaaa. fechaFin puede ser string ISO o null."""
    if value is None or value == '':
        return '—'
    if isinstance(value, datetime):
        return value.strftime('%d/%m/%Y')
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value[:19]).strftime('%d/%m/%Y')
        except ValueError:
            return value[:10]
    if hasattr(value, 'strftime'):
        return value.strftime('%d/%m/%Y')
    return str(value)


def _usuario_min(usuario_id):
    """Datos mínimos del dueño (nombre/correo) desde la colección Usuarios."""
    oid = _oid(usuario_id)
    if not oid:
        return {}
    doc = usuarios_col().find_one(
        {'$or': [{'_id': oid}, {'usuarioId': oid}]},
        {'primerNombre': 1, 'primerApellido': 1, 'correo': 1},
    )
    return doc or {}


def _nombre_completo(doc):
    return f"{doc.get('primerNombre', '')} {doc.get('primerApellido', '')}".strip()


def _ids_suscripcion(s):
    """IDs por los que un Pago puede referenciar a la suscripción."""
    return [x for x in [s.get('suscripcionId'), s.get('_id')] if x is not None]


def _plan_de_suscripcion(suscripcion_id):
    oid = _oid(suscripcion_id)
    if not oid:
        return '—'
    s = suscripciones_col().find_one(
        {'$or': [{'suscripcionId': oid}, {'_id': oid}]}, {'plan.nombrePlan': 1})
    if not s:
        return '—'
    return (s.get('plan') or {}).get('nombrePlan', '—')


def _usuarios_map(ids):
    """Carga en UN solo query los usuarios indicados → {id: doc} (por _id y
    usuarioId). Evita el anti-patrón N+1 (un lookup por fila)."""
    ids = [i for i in set(ids) if i is not None]
    if not ids:
        return {}
    cursor = usuarios_col().find(
        {'$or': [{'_id': {'$in': ids}}, {'usuarioId': {'$in': ids}}]},
        {'primerNombre': 1, 'primerApellido': 1, 'correo': 1, 'usuarioId': 1},
    )
    mapa = {}
    for d in cursor:
        mapa[d['_id']] = d
        if d.get('usuarioId') is not None:
            mapa[d['usuarioId']] = d
    return mapa


def _planes_por_suscripcion(ids):
    """Carga en UN solo query el nombre de plan de las suscripciones → {id: nombre}."""
    ids = [i for i in set(ids) if i is not None]
    if not ids:
        return {}
    cursor = suscripciones_col().find(
        {'$or': [{'suscripcionId': {'$in': ids}}, {'_id': {'$in': ids}}]},
        {'plan.nombrePlan': 1, 'suscripcionId': 1},
    )
    mapa = {}
    for d in cursor:
        nombre = (d.get('plan') or {}).get('nombrePlan', '—')
        mapa[d['_id']] = nombre
        if d.get('suscripcionId') is not None:
            mapa[d['suscripcionId']] = nombre
    return mapa


def _get_plan(plan_id):
    """Busca un plan del catálogo. OJO: en los datos migrados `planId` es un
    ENTERO (1..5), aunque el esquema lo defina como objectId. Aceptamos planId
    entero, string u ObjectId, y también el _id."""
    plan_id = str(plan_id)
    ors = [{'planId': plan_id}]
    if plan_id.isdigit():
        ors.append({'planId': int(plan_id)})
    oid = _oid(plan_id)
    if oid:
        ors.extend([{'planId': oid}, {'_id': oid}])
    return planes_col().find_one({'$or': ors})


# ══════════════════════════════════════════════════════════════════════
# CATÁLOGO DE PLANES
# ══════════════════════════════════════════════════════════════════════
def _plan_dict(p):
    return {
        'idTipoPlan': str(p.get('planId') or p['_id']),
        'nombrePlan': p.get('nombrePlan'),
        'precio': p.get('precio'),
        'duracion': p.get('duracion'),
        'descripcionPlan': p.get('descripcionPlan'),
    }


def listar_planes():
    """Catálogo de planes (cacheado 5 min; cambia poco). Se invalida al
    crear/editar un plan."""
    cached = cache.get(_PLANES_CACHE_KEY)
    if cached is not None:
        return cached
    data = [_plan_dict(p) for p in planes_col().find().sort('precio', 1)]
    cache.set(_PLANES_CACHE_KEY, data, 300)
    return data


def admin_get_plan(pk):
    """Plan individual (forma para el formulario de edición)."""
    p = _get_plan(pk)
    return _plan_dict(p) if p else None


def crear_plan(data):
    """Crea un plan nuevo. Genera el siguiente planId entero (la data real
    usa planId entero, no ObjectId)."""
    col = planes_col()
    nums = [p['planId'] for p in col.find({}, {'planId': 1})
            if isinstance(p.get('planId'), int)]
    siguiente = (max(nums) + 1) if nums else 1
    doc = {
        'planId': siguiente,
        'nombrePlan': data['nombre_plan'].strip(),
        'precio': float(data['precio']),
        'duracion': data['duracion'],
        'descripcionPlan': (data.get('descripcion') or '').strip() or None,
    }
    col.insert_one(doc)
    cache.delete(_PLANES_CACHE_KEY)
    return doc


def actualizar_plan(pk, data):
    """Actualiza un plan del catálogo. NOTA: el nuevo precio solo afecta a
    futuras compras; las suscripciones existentes conservan su snapshot."""
    plan = _get_plan(pk)
    if not plan:
        return False
    planes_col().update_one({'_id': plan['_id']}, {'$set': {
        'nombrePlan': data['nombre_plan'].strip(),
        'precio': float(data['precio']),
        'duracion': data['duracion'],
        'descripcionPlan': (data.get('descripcion') or '').strip() or None,
    }})
    cache.delete(_PLANES_CACHE_KEY)
    return True


# ══════════════════════════════════════════════════════════════════════
# ADMIN · Suscripciones
# ══════════════════════════════════════════════════════════════════════
def admin_listar_suscripciones(q='', estado=''):
    filtro = {}
    if estado:
        filtro['estadoSuscripcion'] = estado
    q = (q or '').strip().lower()

    subs = list(suscripciones_col().find(filtro).sort('fechaInicio', -1))
    umap = _usuarios_map([s.get('usuarioId') for s in subs])

    filas = []
    for s in subs:
        usuario = umap.get(s.get('usuarioId'), {})
        nombre = _nombre_completo(usuario)
        correo = usuario.get('correo', '')
        if q and q not in nombre.lower() and q not in correo.lower():
            continue
        plan = s.get('plan') or {}
        filas.append({
            'idSuscripcion': str(s.get('suscripcionId') or s['_id']),
            'nombreUsuario': nombre or '—',
            'correo': correo or '—',
            'nombrePlan': plan.get('nombrePlan', '—'),
            'fechaInicio': _fmt_fecha(s.get('fechaInicio')),
            'fechaFin': _fmt_fecha(s.get('fechaFin')),
            'estadoSuscripcion': s.get('estadoSuscripcion'),
        })
    return filas


# ══════════════════════════════════════════════════════════════════════
# ADMIN · Pagos
# ══════════════════════════════════════════════════════════════════════
def admin_listar_pagos(q='', resultado=''):
    filtro = {}
    if resultado:
        filtro['resultadoPago'] = resultado
    q = (q or '').strip().lower()

    pagos = list(pagos_col().find(filtro).sort('fechaPago', -1))
    umap = _usuarios_map([(pg.get('usuario') or {}).get('usuarioId') for pg in pagos])
    pmap = _planes_por_suscripcion([pg.get('suscripcionId') for pg in pagos])

    filas = []
    for pg in pagos:
        usuario = pg.get('usuario') or {}
        nombre = _nombre_completo(usuario)
        correo = umap.get(usuario.get('usuarioId'), {}).get('correo', '')
        if q and q not in nombre.lower() and q not in correo.lower():
            continue
        filas.append({
            'idPago': str(pg.get('pagoId') or pg['_id']),
            'nombreUsuario': nombre or '—',
            'correo': correo or '—',
            'nombrePlan': pmap.get(pg.get('suscripcionId'), '—'),
            'monto': pg.get('monto'),
            'metodoPago': pg.get('metodoPago'),
            'fechaPago': _fmt_fecha(pg.get('fechaPago')),
            'resultadoPago': pg.get('resultadoPago'),
        })
    return filas


# ══════════════════════════════════════════════════════════════════════
# ADMIN · Ingresos mensuales (agregación de Pagos completados)
# ══════════════════════════════════════════════════════════════════════
def ultimo_anio_con_pagos():
    pg = pagos_col().find_one({'resultadoPago': 'Completado'}, sort=[('fechaPago', -1)])
    if pg and isinstance(pg.get('fechaPago'), datetime):
        return pg['fechaPago'].year
    return datetime.now().year


def admin_ingresos_mensuales(anio):
    try:
        anio = int(anio)
    except (TypeError, ValueError):
        anio = datetime.now().year

    inicio = datetime(anio, 1, 1, tzinfo=timezone.utc)
    fin = datetime(anio + 1, 1, 1, tzinfo=timezone.utc)

    cursor = list(pagos_col().find({
        'resultadoPago': 'Completado',
        'fechaPago': {'$gte': inicio, '$lt': fin},
    }))
    pmap = _planes_por_suscripcion([pg.get('suscripcionId') for pg in cursor])

    agrupado = {}
    for pg in cursor:
        fecha = pg.get('fechaPago')
        if not isinstance(fecha, datetime):
            continue
        clave = (fecha.month, pmap.get(pg.get('suscripcionId'), '—'))
        d = agrupado.setdefault(clave, {'count': 0, 'total': 0.0})
        d['count'] += 1
        d['total'] += float(pg.get('monto') or 0)

    filas = []
    for (mes, plan), d in sorted(agrupado.items()):
        filas.append({
            'Mes': MESES_ES[mes],
            'NombrePlan': plan,
            'PagosCompletados': d['count'],
            'TotalIngresos': d['total'],
            'IngresoPromedio': d['total'] / d['count'] if d['count'] else 0,
        })
    return filas


# ══════════════════════════════════════════════════════════════════════
# OYENTE · Suscripción / historial / cambio de plan
# ══════════════════════════════════════════════════════════════════════
def _suscripcion_activa(usuario_id):
    oid = _oid(usuario_id)
    if not oid:
        return None
    return suscripciones_col().find_one({'usuarioId': oid, 'estadoSuscripcion': 'activa'})


def plan_activo_oyente(usuario_id):
    s = _suscripcion_activa(usuario_id)
    if not s:
        return None
    plan = s.get('plan') or {}
    return {
        'idTipoPlan': str(plan.get('planId') or ''),
        'nombrePlan': plan.get('nombrePlan'),
        'precio': plan.get('precio'),
        'fechaFin': _fmt_fecha(s.get('fechaFin')),
        'renovacion': 'S' if s.get('renovacionAutomatica') else 'N',
    }


def historial_oyente(usuario_id):
    oid = _oid(usuario_id)
    if not oid:
        return []
    subs = list(suscripciones_col().find({'usuarioId': oid}).sort('fechaInicio', -1))

    # Un solo query para TODOS los pagos de las suscripciones del usuario.
    todos_ids = [i for s in subs for i in _ids_suscripcion(s)]
    pagos_por_sus = {}
    if todos_ids:
        for pg in pagos_col().find({'suscripcionId': {'$in': todos_ids}}).sort('fechaPago', -1):
            pagos_por_sus.setdefault(pg.get('suscripcionId'), []).append(pg)

    filas = []
    for s in subs:
        plan = s.get('plan') or {}
        reno = 'S' if s.get('renovacionAutomatica') else 'N'
        base = {
            'PlanContratado': plan.get('nombrePlan'),
            'Inicio': _fmt_fecha(s.get('fechaInicio')),
            'Fin': _fmt_fecha(s.get('fechaFin')),
            'EstadoSuscripcion': s.get('estadoSuscripcion'),
            'RenovacionAutomatica': reno,
        }
        pagos = [pg for sid in _ids_suscripcion(s) for pg in pagos_por_sus.get(sid, [])]
        if pagos:
            for pg in pagos:
                filas.append({**base,
                              'Monto': pg.get('monto'),
                              'EstadoPago': pg.get('resultadoPago'),
                              'FechaPago': _fmt_fecha(pg.get('fechaPago'))})
        else:
            filas.append({**base, 'Monto': None, 'EstadoPago': None, 'FechaPago': None})
    return filas


METODOS_PAGO = ('Tarjeta de credito', 'Tarjeta de debito', 'Paypal')


def cambiar_plan_oyente(usuario_id, plan_id, renovacion_auto, metodo_pago='Tarjeta de credito'):
    """Inactiva la suscripción activa y crea una nueva con snapshot del plan.
    Registra un Pago (con el método elegido) si el plan tiene precio > 0.
    Devuelve True si tuvo éxito."""
    uoid = _oid(usuario_id)
    plan = _get_plan(plan_id)
    if not uoid or not plan:
        return False
    if metodo_pago not in METODOS_PAGO:
        metodo_pago = 'Tarjeta de credito'

    suscripciones_col().update_many(
        {'usuarioId': uoid, 'estadoSuscripcion': 'activa'},
        {'$set': {'estadoSuscripcion': 'inactiva'}},
    )

    ahora = datetime.now(timezone.utc)
    fin = ahora + timedelta(days=365 if plan.get('duracion') == 'Anual' else 30)
    precio = float(plan.get('precio') or 0)
    nueva_sus_id = ObjectId()

    suscripciones_col().insert_one({
        'suscripcionId': nueva_sus_id,
        'usuarioId': uoid,
        'fechaInicio': ahora,
        # El validador real exige date/null en fechaFin (no string).
        'fechaFin': fin,
        'estadoSuscripcion': 'activa',
        'renovacionAutomatica': bool(renovacion_auto),
        'plan': {
            'planId': plan.get('planId') or plan['_id'],
            'nombrePlan': plan.get('nombrePlan'),
            'precio': precio,
        },
    })

    if precio > 0:
        u = _usuario_min(usuario_id)
        pagos_col().insert_one({
            'pagoId': ObjectId(),
            'suscripcionId': nueva_sus_id,
            'monto': precio,
            'fechaPago': ahora,
            'metodoPago': metodo_pago,
            'resultadoPago': 'Completado',
            'usuario': {
                'usuarioId': uoid,
                'primerNombre': u.get('primerNombre') or 'NA',
                'primerApellido': u.get('primerApellido') or 'NA',
            },
        })
    return True


def set_renovacion_oyente(usuario_id, activar):
    """Activa/desactiva la renovación automática de la suscripción activa."""
    uoid = _oid(usuario_id)
    if not uoid:
        return False
    res = suscripciones_col().update_one(
        {'usuarioId': uoid, 'estadoSuscripcion': 'activa'},
        {'$set': {'renovacionAutomatica': bool(activar)}},
    )
    return res.matched_count > 0


def asegurar_plan_free(usuario_id):
    """Si el oyente no tiene suscripción activa, le asigna el plan Free
    (nombre 'Free' o precio 0). Idempotente. Devuelve True si la creó."""
    uoid = _oid(usuario_id)
    if not uoid:
        return False
    if _suscripcion_activa(usuario_id):
        return False
    plan = planes_col().find_one({'$or': [{'nombrePlan': 'Free'}, {'precio': 0}]})
    if not plan:
        return False
    ahora = datetime.now(timezone.utc)
    suscripciones_col().insert_one({
        'suscripcionId': ObjectId(),
        'usuarioId': uoid,
        'fechaInicio': ahora,
        'fechaFin': None,
        'estadoSuscripcion': 'activa',
        'renovacionAutomatica': False,
        'plan': {
            'planId': plan.get('planId') or plan['_id'],
            'nombrePlan': plan.get('nombrePlan'),
            'precio': float(plan.get('precio') or 0),
        },
    })
    return True
