import json
import logging
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

import bcrypt
from bson import ObjectId
from django.contrib.auth.hashers import check_password, make_password
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError


logger = logging.getLogger('ecualizer.auth')


BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_PATH = BASE_DIR / 'config' / 'credenciales.json'


@lru_cache(maxsize=1)
def get_database():
    with CREDENTIALS_PATH.open('r', encoding='utf-8') as file:
        credentials = json.load(file)

    client = MongoClient(
        credentials['uri'],
        serverSelectionTimeoutMS=8000,
    )
    client.admin.command('ping')
    logger.info('Conexion exitosa a MongoDB Atlas.')
    return client[credentials['nombre_bd']]


def usuarios_collection():
    return get_database()['Usuarios']


def _normalize_email(value):
    return (value or '').strip().lower()


def _as_utc_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if hasattr(value, 'year') and hasattr(value, 'month') and hasattr(value, 'day'):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    return value


def _profile_namespace(profile_data, fallback_key):
    """Crea un namespace a partir del subdocumento de perfil. Garantiza que
    `fallback_key` exista (cadena vacía si falta) SIN sobrescribir su valor
    real (antes lo ponía en True, lo que mostraba 'True' en vez del alias)."""
    profile_data = profile_data or {}
    namespace = SimpleNamespace(**profile_data)
    if not hasattr(namespace, fallback_key):
        setattr(namespace, fallback_key, '')
    return namespace


def build_user_namespace(document):
    if not document:
        return None

    user_id = document.get('usuarioId') or document.get('_id')
    if isinstance(user_id, ObjectId):
        user_id_value = str(user_id)
    else:
        user_id_value = str(user_id) if user_id is not None else None

    profile_oyente = document.get('perfilOyente') or {}
    profile_artista = document.get('perfilArtista') or {}
    profile_admin = document.get('perfilAdmin') or {}

    payload = dict(document)
    payload.update({
        'id_usuario': user_id_value,
        'usuarioId': user_id_value,
        'cedula_usuario': document.get('cedulaUsuario'),
        'primer_nombre': document.get('primerNombre'),
        'segundo_nombre': document.get('segundoNombre'),
        'primer_apellido': document.get('primerApellido'),
        'segundo_apellido': document.get('segundoApellido'),
        'correo': document.get('correo'),
        'contrasena': document.get('contrasena'),
        'fecha_registro': document.get('fechaRegistro'),
        'estado': document.get('estado'),
        'tipo_usuario': document.get('tipoUsuario'),
        'usuario': _profile_namespace(profile_oyente, 'alias') if profile_oyente else None,
        'artista': _profile_namespace(profile_artista, 'nombre_artistico') if profile_artista else None,
        'administrador': _profile_namespace(profile_admin, 'rolAdmin') if profile_admin else None,
    })

    if payload['usuario'] is not None:
        setattr(payload['usuario'], 'nombre_artistico', profile_oyente.get('nombreArtistico'))
        setattr(payload['usuario'], 'pais_usuario', profile_oyente.get('paisUsuario'))
        setattr(payload['usuario'], 'fecha_nacimiento', profile_oyente.get('fechaNacimiento'))
        setattr(payload['usuario'], 'genero', profile_oyente.get('genero'))
    if payload['artista'] is not None:
        setattr(payload['artista'], 'nombre_artistico', profile_artista.get('nombreArtistico'))
        setattr(payload['artista'], 'biografia', profile_artista.get('biografia'))
    if payload['administrador'] is not None:
        setattr(payload['administrador'], 'rol_admin', profile_admin.get('rolAdmin'))
        setattr(payload['administrador'], 'departamento', profile_admin.get('departamento'))

    return SimpleNamespace(**payload)


def find_user_by_filter(filter_spec):
    return usuarios_collection().find_one(filter_spec)


def find_user_by_identifier(identifier):
    identifier = (identifier or '').strip()
    clauses = [
        {'correo': _normalize_email(identifier)},
        {'cedulaUsuario': identifier},
    ]
    if ObjectId.is_valid(identifier):
        object_id = ObjectId(identifier)
        clauses.extend([
            {'_id': object_id},
            {'usuarioId': object_id},
        ])
    return find_user_by_filter({'$or': clauses})


def user_exists(filter_spec):
    return usuarios_collection().count_documents(filter_spec, limit=1) > 0


def verify_password(raw_password, stored_password):
    if not stored_password:
        return False

    if isinstance(stored_password, bytes):
        stored_password = stored_password.decode('utf-8', errors='ignore')

    if stored_password.startswith('pbkdf2_') or stored_password.startswith('argon2$') or stored_password.startswith('scrypt$'):
        return check_password(raw_password, stored_password)

    if stored_password.startswith('$2'):
        try:
            return bcrypt.checkpw(raw_password.encode('utf-8'), stored_password.encode('utf-8'))
        except ValueError:
            return False

    return check_password(raw_password, stored_password)


def authenticate_user(identifier, password, expected_tipo=None):
    identifier = (identifier or '').strip()
    if not identifier or not password:
        return None, 'Credenciales incorrectas.'

    normalized_email = _normalize_email(identifier)
    filter_spec = {
        '$or': [
            {'correo': normalized_email},
            {'cedulaUsuario': identifier},
        ]
    }

    document = find_user_by_filter(filter_spec)
    if not document:
        return None, 'Correo o contraseña incorrectos.'

    if expected_tipo and document.get('tipoUsuario') != expected_tipo:
        return None, 'Esta cuenta no tiene acceso a este panel.'

    if document.get('estado') == 'inactivo':
        return None, 'Tu cuenta está inactiva. Contacta al soporte.'
    if document.get('estado') == 'suspendido':
        return None, 'Tu cuenta ha sido suspendida por un administrador.'

    if not verify_password(password, document.get('contrasena')):
        return None, 'Correo o contraseña incorrectos.'

    return build_user_namespace(document), None


def _base_user_document(persona_data, tipo_usuario):
    return {
        'usuarioId': ObjectId(),
        'cedulaUsuario': (persona_data.get('cedula_usuario') or '').strip(),
        'primerNombre': (persona_data.get('primer_nombre') or '').strip(),
        'segundoNombre': (persona_data.get('segundo_nombre') or None) or None,
        'primerApellido': (persona_data.get('primer_apellido') or '').strip(),
        'segundoApellido': (persona_data.get('segundo_apellido') or None) or None,
        'correo': _normalize_email(persona_data.get('correo')),
        'contrasena': make_password(persona_data.get('contrasena') or ''),
        'fechaRegistro': _as_utc_datetime(datetime.now(timezone.utc)),
        'estado': 'activo',
        'tipoUsuario': tipo_usuario,
    }


def create_user_document(persona_data, tipo_usuario, profile_data):
    collection = usuarios_collection()
    document = _base_user_document(persona_data, tipo_usuario)

    if tipo_usuario == 'oyente':
        document['perfilOyente'] = {
            'alias': (profile_data.get('alias') or '').strip(),
            'paisUsuario': profile_data.get('pais_usuario'),
            'fechaNacimiento': _as_utc_datetime(profile_data.get('fecha_nacimiento')),
            'genero': profile_data.get('genero'),
            'ArtistasSeguidos': [],
        }
    elif tipo_usuario == 'artista':
        document['perfilArtista'] = {
            'nombreArtistico': (profile_data.get('nombre_artistico') or '').strip(),
            'biografia': (profile_data.get('biografia') or '').strip() or None,
        }
    elif tipo_usuario == 'admin':
        document['perfilAdmin'] = {
            'rolAdmin': profile_data.get('rol_admin'),
            'departamento': profile_data.get('departamento'),
        }

    result = collection.insert_one(document)
    saved = collection.find_one({'_id': result.inserted_id})
    return build_user_namespace(saved)


def session_payload(user):
    if user is None:
        return {}

    display_name = getattr(user, 'primer_nombre', '')
    if getattr(user, 'tipo_usuario', '') == 'artista' and getattr(user, 'artista', None):
        display_name = getattr(user.artista, 'nombre_artistico', display_name)
    elif getattr(user, 'tipo_usuario', '') == 'oyente' and getattr(user, 'usuario', None):
        display_name = getattr(user.usuario, 'alias', display_name)

    admin_rol = ''
    if getattr(user, 'tipo_usuario', '') == 'admin' and getattr(user, 'administrador', None):
        admin_rol = getattr(user.administrador, 'rol_admin', '') or ''

    return {
        'usuario_id': getattr(user, 'id_usuario', None),
        'usuario_nombre': getattr(user, 'primer_nombre', ''),
        'usuario_apellido': getattr(user, 'primer_apellido', ''),
        'usuario_correo': getattr(user, 'correo', ''),
        'usuario_display_name': display_name,
        'tipo_usuario': getattr(user, 'tipo_usuario', ''),
        'usuario_tipo_detalle': getattr(user, 'tipo_usuario', ''),
        'admin_rol': admin_rol,
    }


def build_empty_dashboard_stats(role):
    if role == 'admin':
        return {
            'stats': {
                'oyentes': 0,
                'artistas': 0,
                'admins': 0,
                'activos': 0,
                'inactivos': 0,
                'suspendidos': 0,
            },
            'recientes': [],
        }

    if role == 'artista':
        return {
            'persona': None,
            'perfil': None,
            'stats': {
                'oyentes_mensuales': 0,
                'oyentes_trend': 0,
                'reproducciones': 0,
                'repro_trend': 0,
                'likes': 0,
                'likes_trend': 0,
                'regalias_mes': 0,
                'regalias_trend': 0,
            },
        }

    return {
        'persona': None,
        'perfil': None,
        'top_canciones': [],
        'recomendaciones': [],
        'generos': [],
        'historial': [],
        'plan_activo': 'Free',
        'stats': {
            'canciones_favoritas': 0,
            'playlists': 0,
            'artistas_seguidos': 0,
            'horas_escuchadas': 0,
        },
    }


# ══════════════════════════════════════════════════════════════════════
# PANEL DE ADMINISTRACIÓN · Gestión de usuarios (todo desde MongoDB)
# ----------------------------------------------------------------------
# Las plantillas del panel admin fueron escritas para los modelos ORM de
# SQL Server, con una forma ANIDADA: el objeto de subtipo (oyente/artista/
# admin) expone `.id_usuario` (la Persona) y sus propios campos de perfil.
# Aquí reconstruimos esa misma forma con SimpleNamespace a partir de los
# documentos de la colección `Usuarios`, para no tener que tocar el HTML.
# ══════════════════════════════════════════════════════════════════════

GENERO_DISPLAY = {'F': 'Femenino', 'M': 'Masculino', 'O': 'Otro'}
TIPOS_VALIDOS = ('oyente', 'artista', 'admin')
# Cómo se etiqueta cada tipo en la UI de Personas ('admin' → 'administrador').
TIPO_UI = {'oyente': 'oyente', 'artista': 'artista', 'admin': 'administrador'}


def _doc_pk(document):
    """Identificador en string (ObjectId) que usan las plantillas y las URLs."""
    return str(document.get('usuarioId') or document.get('_id'))


def _find_by_pk(pk):
    """Busca un usuario por su id (ObjectId en string), ya sea _id o usuarioId."""
    if not pk or not ObjectId.is_valid(str(pk)):
        return None
    oid = ObjectId(str(pk))
    return usuarios_collection().find_one({'$or': [{'_id': oid}, {'usuarioId': oid}]})


def _parse_date(value):
    """Normaliza fechas a `date` para que el filtro |date de Django funcione.
    En Mongo la fecha de nacimiento se guarda como string 'YYYY-MM-DD'."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.strptime(value[:10], '%Y-%m-%d').date()
        except ValueError:
            return None
    return value  # ya es date


def _persona_ns(document):
    """Namespace con la forma del modelo Persona (datos comunes a todo usuario)."""
    pk = _doc_pk(document)
    return SimpleNamespace(
        pk=pk,
        id_usuario=pk,
        cedula_usuario=document.get('cedulaUsuario'),
        primer_nombre=document.get('primerNombre'),
        segundo_nombre=document.get('segundoNombre'),
        primer_apellido=document.get('primerApellido'),
        segundo_apellido=document.get('segundoApellido'),
        correo=document.get('correo'),
        estado=document.get('estado'),
        fecha_registro=document.get('fechaRegistro'),
    )


def _admin_user_ns(document):
    """Namespace anidado de subtipo (oyente/artista/admin) para el panel admin.
    Expone `.id_usuario` = Persona y los campos de perfil + sus *_display."""
    tipo = document.get('tipoUsuario')
    persona = _persona_ns(document)
    obj = SimpleNamespace(pk=persona.pk, id_usuario=persona, tipo_usuario=tipo)

    if tipo == 'oyente':
        perfil = document.get('perfilOyente') or {}
        obj.alias = perfil.get('alias')
        obj.pais_usuario = perfil.get('paisUsuario')
        obj.fecha_nacimiento = _parse_date(perfil.get('fechaNacimiento'))
        obj.genero = perfil.get('genero')
        # Las plantillas llaman {{ obj.get_genero_display }} (sin paréntesis):
        # basta con exponer el valor ya traducido como atributo.
        obj.get_genero_display = GENERO_DISPLAY.get(obj.genero, obj.genero or '')
    elif tipo == 'artista':
        perfil = document.get('perfilArtista') or {}
        obj.nombre_artistico = perfil.get('nombreArtistico')
        obj.biografia = perfil.get('biografia')
    elif tipo == 'admin':
        perfil = document.get('perfilAdmin') or {}
        obj.rol_admin = perfil.get('rolAdmin')
        obj.get_rol_admin_display = perfil.get('rolAdmin') or ''
        obj.departamento = perfil.get('departamento')

    return obj


def user_exists_excluding(filter_spec, pk):
    """Como user_exists pero ignorando el documento con id `pk` (para validar
    unicidad al EDITAR sin chocar contra el propio registro)."""
    col = usuarios_collection()
    if pk and ObjectId.is_valid(str(pk)):
        oid = ObjectId(str(pk))
        filter_spec = {'$and': [
            filter_spec,
            {'_id': {'$ne': oid}, 'usuarioId': {'$ne': oid}},
        ]}
    return col.count_documents(filter_spec, limit=1) > 0


# ── Dashboard ─────────────────────────────────────────────────────────

def admin_dashboard_stats():
    """Conteos para las tarjetas del dashboard admin.
    Una sola agregación ($facet) en vez de 6 count_documents → 1 round-trip."""
    pipeline = [{'$facet': {
        'tipos': [{'$group': {'_id': '$tipoUsuario', 'n': {'$sum': 1}}}],
        'estados': [{'$group': {'_id': '$estado', 'n': {'$sum': 1}}}],
    }}]
    res = list(usuarios_collection().aggregate(pipeline))
    tipos, estados = {}, {}
    if res:
        tipos = {r['_id']: r['n'] for r in res[0].get('tipos', [])}
        estados = {r['_id']: r['n'] for r in res[0].get('estados', [])}
    return {
        'oyentes': tipos.get('oyente', 0),
        'artistas': tipos.get('artista', 0),
        'admins': tipos.get('admin', 0),
        'activos': estados.get('activo', 0),
        'inactivos': estados.get('inactivo', 0),
        'suspendidos': estados.get('suspendido', 0),
    }


def admin_recent_users(limit=5):
    """Últimos usuarios registrados (para la tabla del dashboard)."""
    cursor = (usuarios_collection()
              .find()
              .sort([('fechaRegistro', -1), ('_id', -1)])
              .limit(limit))
    return [_persona_ns(d) for d in cursor]


# ── Listados por tipo (CRUD) ──────────────────────────────────────────

def _texto_regex(q):
    return {'$regex': re.escape(q.strip()), '$options': 'i'}


def admin_list_users(tipo, q='', estado=''):
    """Lista usuarios de un tipo con búsqueda por texto y filtro de estado."""
    filtro = {'tipoUsuario': tipo}
    if estado:
        filtro['estado'] = estado
    if q:
        regex = _texto_regex(q)
        ors = [
            {'primerNombre': regex},
            {'primerApellido': regex},
            {'correo': regex},
        ]
        if tipo == 'oyente':
            ors.append({'perfilOyente.alias': regex})
        elif tipo == 'artista':
            ors.append({'perfilArtista.nombreArtistico': regex})
        filtro['$or'] = ors
    cursor = usuarios_collection().find(filtro).sort([('fechaRegistro', -1), ('_id', -1)])
    return [_admin_user_ns(d) for d in cursor]


def admin_get_user(pk, tipo=None):
    """Obtiene un usuario (forma anidada) por id; valida el tipo si se indica."""
    doc = _find_by_pk(pk)
    if not doc:
        return None
    if tipo and doc.get('tipoUsuario') != tipo:
        return None
    return _admin_user_ns(doc)


# ── Listado global de Personas ────────────────────────────────────────

def admin_list_personas(q='', estado='', tipo=''):
    """Vista global de todas las personas con su rol calculado."""
    filtro = {}
    if estado:
        filtro['estado'] = estado
    if q:
        regex = _texto_regex(q)
        filtro['$or'] = [
            {'primerNombre': regex},
            {'primerApellido': regex},
            {'correo': regex},
            {'cedulaUsuario': regex},
        ]
    # Filtro por tipo: la UI usa 'administrador' pero en Mongo es 'admin'.
    inverso = {'oyente': 'oyente', 'artista': 'artista', 'administrador': 'admin'}
    if tipo in inverso:
        filtro['tipoUsuario'] = inverso[tipo]
    elif tipo == 'sin rol':
        filtro['tipoUsuario'] = {'$nin': list(TIPOS_VALIDOS)}

    cursor = usuarios_collection().find(filtro).sort([('fechaRegistro', -1), ('_id', -1)])
    personas = []
    for d in cursor:
        p = _persona_ns(d)
        t = d.get('tipoUsuario')
        # En el patrón Single Collection cada usuario tiene exactamente un tipo.
        p.tipos = [TIPO_UI[t]] if t in TIPOS_VALIDOS else []
        p.tipo_principal = p.tipos[0] if p.tipos else 'sin rol'
        personas.append(p)
    return personas


def admin_get_persona_detail(pk):
    """Devuelve (persona, oyente_p, artista_p, admin_p) para el detalle global."""
    doc = _find_by_pk(pk)
    if not doc:
        return None
    persona = _persona_ns(doc)
    tipo = doc.get('tipoUsuario')
    oyente_p = artista_p = admin_p = None
    if tipo == 'oyente':
        oyente_p = _admin_user_ns(doc)
    elif tipo == 'artista':
        artista_p = _admin_user_ns(doc)
    elif tipo == 'admin':
        admin_p = _admin_user_ns(doc)
    return persona, oyente_p, artista_p, admin_p


# ── Actualización y baja lógica ───────────────────────────────────────

def admin_update_user(pk, persona_data, profile_data, tipo, nueva_contrasena=None):
    """Actualiza datos personales + perfil de un usuario. `persona_data` y
    `profile_data` vienen de los formularios ya validados (cleaned_data)."""
    doc = _find_by_pk(pk)
    if not doc:
        raise ValueError('Usuario no encontrado.')

    update = {
        'cedulaUsuario': (persona_data.get('cedula_usuario') or '').strip(),
        'primerNombre': (persona_data.get('primer_nombre') or '').strip(),
        'segundoNombre': (persona_data.get('segundo_nombre') or None) or None,
        'primerApellido': (persona_data.get('primer_apellido') or '').strip(),
        'segundoApellido': (persona_data.get('segundo_apellido') or None) or None,
        'correo': _normalize_email(persona_data.get('correo')),
        'estado': persona_data.get('estado'),
    }
    if nueva_contrasena:
        update['contrasena'] = make_password(nueva_contrasena)

    if tipo == 'oyente':
        fn = profile_data.get('fecha_nacimiento')
        update['perfilOyente.alias'] = (profile_data.get('alias') or '').strip()
        update['perfilOyente.paisUsuario'] = profile_data.get('pais_usuario')
        update['perfilOyente.fechaNacimiento'] = fn.isoformat() if hasattr(fn, 'isoformat') else fn
        update['perfilOyente.genero'] = profile_data.get('genero')
    elif tipo == 'artista':
        update['perfilArtista.nombreArtistico'] = (profile_data.get('nombre_artistico') or '').strip()
        update['perfilArtista.biografia'] = (profile_data.get('biografia') or '').strip() or None
    elif tipo == 'admin':
        update['perfilAdmin.rolAdmin'] = profile_data.get('rol_admin')
        update['perfilAdmin.departamento'] = profile_data.get('departamento')

    usuarios_collection().update_one({'_id': doc['_id']}, {'$set': update})
    return True


def admin_soft_delete(pk):
    """Baja lógica: cambia el estado a 'inactivo' (no borra el documento)."""
    doc = _find_by_pk(pk)
    if not doc:
        return None
    usuarios_collection().update_one({'_id': doc['_id']}, {'$set': {'estado': 'inactivo'}})
    return _persona_ns(doc)