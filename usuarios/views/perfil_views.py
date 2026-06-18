from django.shortcuts import render, redirect
from django.views import View
from django.db import DatabaseError, connection
from django.contrib import messages
from django.contrib.auth.hashers import make_password

from ..models import Persona, Usuario
from ..mixins import RequiereLogin, RequiereOyente, RequiereArtista
from ..forms import PerfilPersonaForm, PerfilUsuarioForm, AdminEditArtistaForm
from analitica.services.oyente_service import (
    sp_top_canciones_usuario,
    sp_tiempo_total_escucha,
    sp_generos_favoritos_usuario,
    sp_recomendaciones_semanales,
)
from biblioteca.services import get_canciones_liked


def _get_persona(request):
    uid = request.session.get('usuario_id')
    if not uid:
        return None
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
        uid = persona.id_usuario

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
            from django.db import connection as conn
            with conn.cursor() as cur:
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

        from analitica.views.artista import DashboardArtistaView as _DashAnalitica
        return _DashAnalitica.as_view()(request)


# ──────────────────────────────────────────────────────────
# PERFIL DEL OYENTE — editar datos propios
# ──────────────────────────────────────────────────────────
class PerfilOyenteView(RequiereOyente, View):
    template_name = 'usuarios/oyente/perfil.html'

    def _ctx(self, request, p_form, u_form):
        persona = _get_persona(request)
        return {
            'persona': persona,
            'perfil':  getattr(persona, 'usuario', None),
            'p_form':  p_form,
            'u_form':  u_form,
        }

    def get(self, request):
        persona = _get_persona(request)
        usuario = persona.usuario
        return render(request, self.template_name, self._ctx(
            request, PerfilPersonaForm(instance=persona),
            PerfilUsuarioForm(instance=usuario)))

    def post(self, request):
        persona = _get_persona(request)
        usuario = persona.usuario
        p_form = PerfilPersonaForm(request.POST, instance=persona)
        u_form = PerfilUsuarioForm(request.POST, instance=usuario)

        if p_form.is_valid() and u_form.is_valid():
            per = p_form.save(commit=False)
            nueva = request.POST.get('nueva_contrasena', '').strip()
            if nueva:
                per.contrasena = make_password(nueva)
            per.save()
            u_form.save()
            request.session['usuario_nombre'] = per.primer_nombre
            messages.success(request, 'Tu perfil se actualizó correctamente.')
            return redirect('perfil_oyente')

        messages.error(request, 'Revisa los campos marcados e inténtalo de nuevo.')
        return render(request, self.template_name, self._ctx(request, p_form, u_form))


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
        try:
            plan = self._plan_activo(persona.id_usuario)
        except DatabaseError:
            plan = None
        return render(request, self.template_name, {
            'persona': persona,
            'perfil':  getattr(persona, 'usuario', None),
            'plan':    plan,
        })

    def post(self, request):
        uid = request.session.get('usuario_id')
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
    template_name = 'usuarios/artista/perfil.html'

    def _ctx(self, request, p_form, a_form):
        persona = _get_persona(request)
        return {
            'persona': persona,
            'perfil':  getattr(persona, 'artista', None),
            'p_form':  p_form,
            'a_form':  a_form,
        }

    def get(self, request):
        persona = _get_persona(request)
        artista = persona.artista
        return render(request, self.template_name, self._ctx(
            request, PerfilPersonaForm(instance=persona),
            AdminEditArtistaForm(instance=artista)))

    def post(self, request):
        persona = _get_persona(request)
        artista = persona.artista
        p_form = PerfilPersonaForm(request.POST, instance=persona)
        a_form = AdminEditArtistaForm(request.POST, instance=artista)

        if p_form.is_valid() and a_form.is_valid():
            per = p_form.save(commit=False)
            nueva = request.POST.get('nueva_contrasena', '').strip()
            if nueva:
                per.contrasena = make_password(nueva)
            per.save()
            a_form.save()
            request.session['usuario_nombre'] = per.primer_nombre
            messages.success(request, 'Tu perfil se actualizó correctamente.')
            return redirect('perfil_artista')

        messages.error(request, 'Revisa los campos marcados e inténtalo de nuevo.')
        return render(request, self.template_name, self._ctx(request, p_form, a_form))


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