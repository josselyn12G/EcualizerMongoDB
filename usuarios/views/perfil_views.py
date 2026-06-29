from django.shortcuts import render, redirect
from django.views import View
from django.db import DatabaseError, connection
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.utils import timezone


def _saludo_por_hora():
    """Saludo contextual según la hora local (estilo 'Good afternoon')."""
    h = timezone.localtime().hour
    if h < 12:
        return 'Buenos días'
    if h < 19:
        return 'Buenas tardes'
    return 'Buenas noches'

from usuarios.models import Persona, Usuario
from usuarios.mixins import RequiereLogin, RequiereOyente, RequiereArtista
from usuarios.forms import (
    PerfilPersonaForm, PerfilUsuarioForm, AdminEditArtistaForm,
    MongoPerfilPersonaForm, MongoAdminOyenteForm, MongoAdminArtistaForm,
)
from usuarios.mongo_service import (
    build_empty_dashboard_stats, build_user_namespace, find_user_by_identifier,
    admin_get_user, admin_update_user,
)
from analitica.services.oyente_service import (
    sp_top_canciones_usuario,
    sp_tiempo_total_escucha,
    sp_generos_favoritos_usuario,
    sp_recomendaciones_semanales,
)
from biblioteca.mongo_service import get_canciones_liked


def _is_sql_uid(uid):
    return isinstance(uid, int) or (isinstance(uid, str) and uid.isdigit())


def _get_persona(request):
    uid = request.session.get('usuario_id')
    if not uid:
        return None
    # Usuario de MongoDB: el id es un ObjectId (24 hex), no un entero.
    # Se busca directo en Mongo para no tocar el ORM de SQL Server.
    if not _is_sql_uid(uid):
        mongo_doc = find_user_by_identifier(uid)
        return build_user_namespace(mongo_doc) if mongo_doc else None
    # Usuario heredado de SQL Server (id entero).
    try:
        return Persona.objects.get(pk=uid)
    except Persona.DoesNotExist:
        return None


class DashboardOyenteView(RequiereLogin, View):
    def get(self, request):
        if request.session.get('tipo_usuario') != 'oyente':
            from .auth_views import _redirect_por_tipo
            return _redirect_por_tipo(request.session.get('tipo_usuario', ''))

        persona = _get_persona(request)
        uid = getattr(persona, 'id_usuario', None)

        if not _is_sql_uid(uid):
            ctx = build_empty_dashboard_stats('oyente')
            # Refleja el plan activo real (módulo de pagos en Mongo).
            from pagos.mongo_service import plan_activo_oyente
            pa = plan_activo_oyente(uid)
            ctx['plan_activo'] = pa['nombrePlan'] if pa else 'Free'
            ctx.update({
                'persona': persona,
                'perfil': getattr(persona, 'usuario', None),
                'saludo': _saludo_por_hora(),
            })
            return render(request, 'usuarios/oyente/dashboard.html', ctx)

        try:
            perfil = persona.usuario
        except (Usuario.DoesNotExist, AttributeError):
            perfil = None

        try:
            top_canciones = sp_top_canciones_usuario(uid, 'mes')
        except DatabaseError:
            top_canciones = []

        try:
            tiempo = sp_tiempo_total_escucha(uid, 'mes')
            horas = tiempo[0]['TotalHoras'] if tiempo else 0
        except DatabaseError:
            horas = 0

        try:
            generos = sp_generos_favoritos_usuario(uid, 'mes')
        except DatabaseError:
            generos = []

        try:
            recomendaciones = sp_recomendaciones_semanales(uid)
        except DatabaseError:
            recomendaciones = []

        try:
            likes = get_canciones_liked(uid)
            n_likes = len(likes)
        except DatabaseError:
            n_likes = 0
        
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT tp.nombrePlan FROM Pagos.Suscripcion s
                    INNER JOIN Pagos.TipoPlan tp ON tp.idTipoPlan = s.TipoPlan_idTipoPlan
                    WHERE s.Usuario_idUsuario = %s AND s.estadoSuscripcion = 'activa'
                    """,
                    [uid]
                )
                row = cur.fetchone()
                plan_activo = row[0] if row else 'Free'
        except DatabaseError:
            plan_activo = 'Free'

        # ── Reproducciones recientes (carátula Deezer + reproducible) ──
        historial = []
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT TOP 8
                        c.idCancion        AS idCancion,
                        c.nombreCancion    AS nombreCancion,
                        ar.nombreArtistico AS nombreArtistico,
                        al.tituloAlbum     AS tituloAlbum,
                        c.duracion         AS duracion,
                        MAX(r.fechaHora)   AS ultima
                    FROM Analitica.Reproduccion r
                    JOIN Catalogo.Cancion c ON c.idCancion = r.Cancion_idCancion
                    JOIN Catalogo.Album   al ON al.idAlbum  = c.Album_idAlbum
                    JOIN Usuario.Artista  ar ON ar.idUsuario = al.Artista_idUsuario
                    WHERE r.Usuario_idUsuario = %s
                    GROUP BY c.idCancion, c.nombreCancion, ar.nombreArtistico,
                             al.tituloAlbum, c.duracion
                    ORDER BY ultima DESC;
                    """,
                    [uid],
                )
                cols = [d[0] for d in cur.description]
                filas = [dict(zip(cols, row)) for row in cur.fetchall()]

            # Portadas reales desde Deezer (añade 'coverUrl').
            from catalogo.services import deezer_enrich_canciones
            deezer_enrich_canciones(filas)

            for f in filas:
                seg = int(f.get('duracion') or 0)
                historial.append({
                    'id':       f.get('idCancion'),
                    'nombre':   f.get('nombreCancion', ''),
                    'artista':  f.get('nombreArtistico', ''),
                    'album':    f.get('tituloAlbum', ''),
                    'duracion': f'{seg // 60}:{seg % 60:02d}',
                    'cover':    f.get('coverUrl'),
                })
        except DatabaseError:
            historial = []

        return render(request, 'usuarios/oyente/dashboard.html', {
            'persona':         persona,
            'perfil':          perfil,
            'top_canciones':   top_canciones,
            'recomendaciones': recomendaciones,
            'generos':         generos,
            'historial':       historial,
            'plan_activo':     plan_activo,
            'saludo':          _saludo_por_hora(),
            'stats': {
                'canciones_favoritas': n_likes,
                'playlists':           0,
                'artistas_seguidos':   0,
                'horas_escuchadas':    horas,
            },
        })


class DashboardArtistaView(RequiereLogin, View):
    """Dashboard del artista — delega a la vista analítica del módulo analitica."""

    def get(self, request):
        if request.session.get('tipo_usuario') != 'artista':
            from .auth_views import _redirect_por_tipo
            return _redirect_por_tipo(request.session.get('tipo_usuario', ''))

        persona = _get_persona(request)
        uid = getattr(persona, 'id_usuario', None)

        if not _is_sql_uid(uid):
            ctx = build_empty_dashboard_stats('artista')
            ctx.update({'persona': persona, 'perfil': getattr(persona, 'artista', None)})
            return render(request, 'usuarios/artista/dashboard.html', ctx)

        from analitica.views.artista import DashboardArtistaView as _DashAnalitica
        return _DashAnalitica.as_view()(request)


# ──────────────────────────────────────────────────────────
# PERFIL DEL OYENTE — editar datos propios
# ──────────────────────────────────────────────────────────
def _persona_initial_from(obj):
    """Valores iniciales del form de datos personales a partir del namespace."""
    p = obj.id_usuario
    return {
        'cedula_usuario': p.cedula_usuario,
        'primer_nombre': p.primer_nombre,
        'segundo_nombre': p.segundo_nombre,
        'primer_apellido': p.primer_apellido,
        'segundo_apellido': p.segundo_apellido,
        'correo': p.correo,
    }


class PerfilOyenteView(RequiereOyente, View):
    """Edición del propio perfil del oyente — datos en MongoDB."""
    template_name = 'usuarios/oyente/perfil.html'

    def get(self, request):
        persona = _get_persona(request)
        obj = admin_get_user(getattr(persona, 'id_usuario', None), 'oyente')
        p_form = MongoPerfilPersonaForm(initial=_persona_initial_from(obj), pk=obj.pk)
        u_form = MongoAdminOyenteForm(initial={
            'alias': obj.alias,
            'pais_usuario': obj.pais_usuario,
            'fecha_nacimiento': obj.fecha_nacimiento,
            'genero': obj.genero,
        }, pk=obj.pk)
        return render(request, self.template_name, {
            'persona': persona, 'perfil': obj, 'p_form': p_form, 'u_form': u_form,
        })

    def post(self, request):
        persona = _get_persona(request)
        obj = admin_get_user(getattr(persona, 'id_usuario', None), 'oyente')
        # La cédula está deshabilitada → su valor se toma del initial.
        p_form = MongoPerfilPersonaForm(
            request.POST, initial={'cedula_usuario': obj.id_usuario.cedula_usuario}, pk=obj.pk)
        u_form = MongoAdminOyenteForm(request.POST, pk=obj.pk)

        if p_form.is_valid() and u_form.is_valid():
            persona_data = dict(p_form.cleaned_data)
            persona_data['estado'] = persona.estado  # el usuario no cambia su estado
            admin_update_user(
                obj.pk, persona_data, u_form.cleaned_data, 'oyente',
                request.POST.get('nueva_contrasena', '').strip() or None,
            )
            request.session['usuario_nombre'] = persona_data['primer_nombre']
            messages.success(request, 'Tu perfil se actualizó correctamente.')
            return redirect('perfil_oyente')

        messages.error(request, 'Revisa los campos marcados e inténtalo de nuevo.')
        return render(request, self.template_name, {
            'persona': persona, 'perfil': obj, 'p_form': p_form, 'u_form': u_form,
        })


# ──────────────────────────────────────────────────────────
# CONFIGURACIÓN DEL OYENTE — preferencias simples
# ──────────────────────────────────────────────────────────
class ConfiguracionOyenteView(RequiereOyente, View):
    template_name = 'usuarios/oyente/configuracion.html'

    def _plan_activo(self, uid):
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT tp.nombrePlan, s.renovacionAutomatica, s.fechaFin, tp.precio
                FROM Pagos.Suscripcion s
                JOIN Pagos.TipoPlan tp ON tp.idTipoPlan = s.TipoPlan_idTipoPlan
                WHERE s.Usuario_idUsuario = %s AND s.estadoSuscripcion = 'activa'
                """,
                [uid],
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                'nombrePlan': row[0],
                'renovacion': row[1],
                'fechaFin':   row[2],
                'precio':     row[3],
            }

    def get(self, request):
        persona = _get_persona(request)
        plan = None
        uid = getattr(persona, 'id_usuario', None)
        if _is_sql_uid(uid):
            try:
                plan = self._plan_activo(uid)
            except DatabaseError:
                plan = None
        else:
            # Plan activo desde MongoDB (módulo de pagos). Garantiza el plan
            # Free por defecto si el oyente aún no tiene suscripción.
            from pagos.mongo_service import asegurar_plan_free, plan_activo_oyente
            asegurar_plan_free(uid)
            plan = plan_activo_oyente(uid)
        return render(request, self.template_name, {
            'persona': persona,
            'perfil':  getattr(persona, 'usuario', None),
            'plan':    plan,
        })

    def post(self, request):
        uid = request.session.get('usuario_id')
        if not _is_sql_uid(uid):
            # Renovación automática sobre la suscripción de MongoDB.
            from pagos.mongo_service import set_renovacion_oyente
            set_renovacion_oyente(uid, bool(request.POST.get('auto_renovacion')))
            messages.success(request, 'Tus preferencias se guardaron correctamente.')
            return redirect('configuracion_oyente')
        renovacion = 'S' if request.POST.get('auto_renovacion') else 'N'
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    UPDATE Pagos.Suscripcion
                    SET renovacionAutomatica = %s
                    WHERE Usuario_idUsuario = %s AND estadoSuscripcion = 'activa'
                    """,
                    [renovacion, uid],
                )
            messages.success(request, 'Tus preferencias se guardaron correctamente.')
        except DatabaseError:
            messages.error(request, 'No se pudieron guardar las preferencias.')
        return redirect('configuracion_oyente')


# ──────────────────────────────────────────────────────────
# PERFIL DEL ARTISTA — editar datos propios
# ──────────────────────────────────────────────────────────
class PerfilArtistaView(RequiereArtista, View):
    """Edición del propio perfil del artista — datos en MongoDB."""
    template_name = 'usuarios/artista/perfil.html'

    def get(self, request):
        persona = _get_persona(request)
        obj = admin_get_user(getattr(persona, 'id_usuario', None), 'artista')
        p_form = MongoPerfilPersonaForm(initial=_persona_initial_from(obj), pk=obj.pk)
        a_form = MongoAdminArtistaForm(initial={
            'nombre_artistico': obj.nombre_artistico,
            'biografia': obj.biografia,
        }, pk=obj.pk)
        return render(request, self.template_name, {
            'persona': persona, 'perfil': obj, 'p_form': p_form, 'a_form': a_form,
        })

    def post(self, request):
        persona = _get_persona(request)
        obj = admin_get_user(getattr(persona, 'id_usuario', None), 'artista')
        p_form = MongoPerfilPersonaForm(
            request.POST, initial={'cedula_usuario': obj.id_usuario.cedula_usuario}, pk=obj.pk)
        a_form = MongoAdminArtistaForm(request.POST, pk=obj.pk)

        if p_form.is_valid() and a_form.is_valid():
            persona_data = dict(p_form.cleaned_data)
            persona_data['estado'] = persona.estado
            admin_update_user(
                obj.pk, persona_data, a_form.cleaned_data, 'artista',
                request.POST.get('nueva_contrasena', '').strip() or None,
            )
            request.session['usuario_nombre'] = persona_data['primer_nombre']
            messages.success(request, 'Tu perfil se actualizó correctamente.')
            return redirect('perfil_artista')

        messages.error(request, 'Revisa los campos marcados e inténtalo de nuevo.')
        return render(request, self.template_name, {
            'persona': persona, 'perfil': obj, 'p_form': p_form, 'a_form': a_form,
        })


# ──────────────────────────────────────────────────────────
# CONFIGURACIÓN DEL ARTISTA — info de cuenta (simple)
# ──────────────────────────────────────────────────────────
class ConfiguracionArtistaView(RequiereArtista, View):
    template_name = 'usuarios/artista/configuracion.html'

    def get(self, request):
        persona = _get_persona(request)
        return render(request, self.template_name, {
            'persona': persona,
            'perfil':  getattr(persona, 'artista', None),
        })