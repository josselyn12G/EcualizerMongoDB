"""
Vistas de Album para el USUARIO (oyente) — migradas a MongoDB.
"""

from django.views.generic import View
from django.shortcuts import render, redirect

from usuarios.mixins import RequiereOyente
from ...services import (
    deezer_enrich_albumes,
    deezer_get_album_image,
    deezer_get_artist_image,
)
from ...services.catalogo_mongo import listar_albumes, get_album_detalle
from biblioteca.mongo_service import get_canciones_liked_ids


def _canciones_a_dicts(canciones_ns, cover_url):
    """Convierte la lista de SimpleNamespace de canciones a dicts para el template."""
    out = []
    for c in canciones_ns:
        out.append({
            'pk': getattr(c, 'pk', None) or getattr(c, 'idCancion', ''),
            'numero_pista': getattr(c, 'numero_pista', None),
            'nombre_cancion': getattr(c, 'nombre_cancion', ''),
            'duracion': getattr(c, 'duracion', 0) or 0,
            'duracion_formateada': _fmt_duracion(getattr(c, 'duracion', 0) or 0),
            'calidad_kbps': getattr(c, 'calidad_kbps', None),
            'total_reproducciones': getattr(c, 'total_reproducciones', 0) or 0,
            'coverUrl': cover_url,
        })
    return out


def _fmt_duracion(segundos):
    try:
        s = int(segundos)
        return f'{s // 60}:{s % 60:02d}'
    except (TypeError, ValueError):
        return '0:00'


# ──────────────────────────────────────────────────────────
# LIST
# ──────────────────────────────────────────────────────────
class UsuarioAlbumListView(RequiereOyente, View):
    template_name = 'catalogo/usuario/usuario_album.html'

    def get(self, request):
        busqueda = request.GET.get('q') or None
        try:
            albumes = listar_albumes(estado='activo', busqueda=busqueda)
        except Exception:
            albumes = []
        deezer_enrich_albumes(albumes)

        return render(request, self.template_name, {
            'albumes': albumes,
            'busqueda': busqueda or '',
            'modo': 'list',
            'saved_ids': set(),
        })


# ──────────────────────────────────────────────────────────
# DETAIL
# ──────────────────────────────────────────────────────────
class UsuarioAlbumDetailView(RequiereOyente, View):
    template_name = 'catalogo/usuario/usuario_album.html'

    def get(self, request, pk):
        result = get_album_detalle(pk)
        if not result:
            return redirect('catalogo:usuario_album_list')
        album, canciones_ns = result

        if getattr(album, 'estado_album', '') != 'activo':
            return redirect('catalogo:usuario_album_list')

        cover_url = deezer_get_album_image(
            album.titulo_album or '',
            album.artista.nombre_artistico or '',
        )
        artist_image = deezer_get_artist_image(album.artista.nombre_artistico or '')

        canciones = _canciones_a_dicts(canciones_ns, cover_url)

        total_seg = sum(c['duracion'] for c in canciones)
        total_min = round(total_seg / 60)

        liked_ids = set()
        try:
            liked_ids = get_canciones_liked_ids(request.session.get('usuario_id'))
        except Exception:
            pass

        return render(request, self.template_name, {
            'album': album,
            'canciones': canciones,
            'cover_url': cover_url,
            'artist_image': artist_image,
            'total_canciones': len(canciones),
            'duracion_total_min': total_min,
            'modo': 'detail',
            'album_guardado': False,
            'liked_ids': liked_ids,
        })


# ──────────────────────────────────────────────────────────
# SEARCH
# ──────────────────────────────────────────────────────────
class UsuarioAlbumSearchView(RequiereOyente, View):
    template_name = 'catalogo/usuario/usuario_album.html'

    def get(self, request):
        q = request.GET.get('q', '').strip()
        try:
            resultados = listar_albumes(estado='activo', busqueda=q if q else None)
        except Exception:
            resultados = []
        deezer_enrich_albumes(resultados)

        return render(request, self.template_name, {
            'albumes': resultados,
            'busqueda': q,
            'modo': 'search',
            'es_busqueda': True,
        })
