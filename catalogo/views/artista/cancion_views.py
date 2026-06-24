"""
Vistas de Cancion para el ARTISTA (migradas a MongoDB).
"""

from types import SimpleNamespace

from django.views.generic import View
from django.shortcuts import redirect, render
from django.contrib import messages

from usuarios.mixins import RequiereArtista
from ...services.cancion_mongo import (
    listar_canciones,
    listar_generos_disponibles,
    get_cancion_ns,
    crear_cancion,
    actualizar_cancion,
    desactivar_cancion,
)
from ...services.catalogo_mongo import listar_albumes
from ...forms.mongo_forms import MongoCancionForm


def _album_choices(artista_id):
    # Todos los álbumes del artista (no sólo activos) para que al EDITAR una
    # canción su álbum actual siempre esté entre las opciones del select.
    albumes = listar_albumes(artista_id=artista_id)
    albumes = [a for a in albumes if a.get('estadoAlbum') != 'eliminado']
    return [('', '-- Selecciona un álbum --')] + [
        (a['idAlbum'], a['tituloAlbum']) for a in albumes
    ]


def _generos_actuales(cancion_ns):
    """Devuelve set de nombres de género de un namespace de canción."""
    return {g.nombre_genero for g in (getattr(cancion_ns, 'generos', None) or [])}


# ──────────────────────────────────────────────────────────
# LIST
# ──────────────────────────────────────────────────────────
class ArtistaCancionListView(RequiereArtista, View):
    template_name = 'catalogo/artista/artista_cancion.html'

    def get(self, request):
        artista_id = request.session['usuario_id']
        busqueda = request.GET.get('q') or None
        album_id = request.GET.get('album') or None
        estado = request.GET.get('estado') or None

        try:
            canciones = listar_canciones(
                artista_id=artista_id,
                album_id=album_id,
                estado=estado,
                busqueda=busqueda,
            )
        except Exception as e:
            messages.error(request, f'No se pudo cargar el listado de canciones: {e}')
            canciones = []

        albumes_raw = listar_albumes(artista_id=artista_id)
        albumes = [
            SimpleNamespace(pk=a['idAlbum'], titulo_album=a['tituloAlbum'])
            for a in albumes_raw
        ]

        return render(request, self.template_name, {
            'canciones': canciones,
            'reproducciones_mes': [],
            'albumes': albumes,
            'busqueda': busqueda or '',
            'album_id': album_id or '',
            'estado_actual': estado or '',
            'estados': [('activa', 'Activa'), ('inactiva', 'Inactiva'),
                        ('bloqueada', 'Bloqueada')],
            'modo': 'list',
        })


# ──────────────────────────────────────────────────────────
# CREATE
# ──────────────────────────────────────────────────────────
class ArtistaCancionCreateView(RequiereArtista, View):
    template_name = 'catalogo/artista/artista_cancion.html'

    def get(self, request):
        artista_id = request.session['usuario_id']
        form = MongoCancionForm(album_choices=_album_choices(artista_id))
        return render(request, self.template_name, {
            'form': form,
            'modo': 'create',
            'all_generos': listar_generos_disponibles(),
            'generos_actuales_ids': set(),
        })

    def post(self, request):
        artista_id = request.session['usuario_id']
        choices = _album_choices(artista_id)
        form = MongoCancionForm(request.POST, album_choices=choices)
        generos_sel = request.POST.getlist('generos') or []
        if not form.is_valid():
            return render(request, self.template_name, {
                'form': form, 'modo': 'create',
                'all_generos': listar_generos_disponibles(),
                'generos_actuales_ids': set(generos_sel),
            })

        data = form.cleaned_data
        genero_str = data.get('genero', '').strip()
        generos = list({g for g in generos_sel if g}) or ([genero_str] if genero_str else [])

        try:
            crear_cancion(
                artista_id=artista_id,
                album_id=data['album_id'],
                nombre=data['titulo'],
                duracion=data['duracion'],
                fecha=data.get('fecha_lanzamiento'),
                calidad=data['calidad'],
                numero_pista=data['numero_pista'],
                letra=data.get('letra') or '',
                generos=generos,
            )
            messages.success(request, 'Canción creada correctamente.')
        except Exception as e:
            messages.error(request, f'Error al crear canción: {e}')
            return render(request, self.template_name, {
                'form': form, 'modo': 'create',
                'all_generos': listar_generos_disponibles(),
                'generos_actuales_ids': set(generos_sel),
            })
        return redirect('catalogo:artista_cancion_list')


# ──────────────────────────────────────────────────────────
# UPDATE
# ──────────────────────────────────────────────────────────
class ArtistaCancionUpdateView(RequiereArtista, View):
    template_name = 'catalogo/artista/artista_cancion.html'

    def _get_cancion(self, pk, artista_id):
        ns = get_cancion_ns(pk)
        if not ns:
            return None
        artistas_ids = [
            str(a.get('artistaId', ''))
            for a in (getattr(ns, '_artistas_raw', None) or [])
        ]
        return ns

    def _load_cancion(self, pk, artista_id):
        """Devuelve SimpleNamespace o None si no pertenece al artista."""
        from ...services.cancion_mongo import _find_cancion, _oid
        raw = _find_cancion(pk)
        if not raw:
            return None
        artista_oid = _oid(artista_id)
        artistas = raw.get('artistas') or []
        if not any(a.get('artistaId') == artista_oid for a in artistas):
            return None
        return get_cancion_ns(pk)

    def get(self, request, pk):
        artista_id = request.session['usuario_id']
        cancion = self._load_cancion(pk, artista_id)
        if not cancion:
            messages.error(request, 'Canción no encontrada o sin acceso.')
            return redirect('catalogo:artista_cancion_list')

        choices = _album_choices(artista_id)
        initial = {
            'titulo': cancion.nombre_cancion,
            'album_id': cancion.album.pk,
            'duracion': cancion.duracion,
            'numero_pista': cancion.numero_pista,
            'calidad': cancion.calidad_kbps,
            'letra': cancion.letra_cancion or '',
        }
        form = MongoCancionForm(initial=initial, album_choices=choices)
        return render(request, self.template_name, {
            'form': form,
            'cancion': cancion,
            'modo': 'update',
            'all_generos': listar_generos_disponibles(),
            'generos_actuales_ids': _generos_actuales(cancion),
        })

    def post(self, request, pk):
        artista_id = request.session['usuario_id']
        cancion = self._load_cancion(pk, artista_id)
        if not cancion:
            messages.error(request, 'Canción no encontrada o sin acceso.')
            return redirect('catalogo:artista_cancion_list')

        choices = _album_choices(artista_id)
        form = MongoCancionForm(request.POST, album_choices=choices)
        generos_sel = request.POST.getlist('generos') or []
        if not form.is_valid():
            return render(request, self.template_name, {
                'form': form, 'cancion': cancion, 'modo': 'update',
                'all_generos': listar_generos_disponibles(),
                'generos_actuales_ids': set(generos_sel),
            })

        data = form.cleaned_data
        genero_str = data.get('genero', '').strip()
        generos = list({g for g in generos_sel if g}) or ([genero_str] if genero_str else None)

        try:
            actualizar_cancion(
                pk=pk,
                nombre=data['titulo'],
                duracion=data['duracion'],
                fecha=data.get('fecha_lanzamiento'),
                calidad=data['calidad'],
                numero_pista=data['numero_pista'],
                letra=data.get('letra') or '',
                generos=generos,
                artista_id=artista_id,
            )
            messages.success(request, 'Canción actualizada.')
        except Exception as e:
            messages.error(request, f'Error al editar: {e}')
            return render(request, self.template_name, {
                'form': form, 'cancion': cancion, 'modo': 'update',
                'all_generos': listar_generos_disponibles(),
                'generos_actuales_ids': set(generos_sel),
            })
        return redirect('catalogo:artista_cancion_list')


# ──────────────────────────────────────────────────────────
# DEACTIVATE
# ──────────────────────────────────────────────────────────
class ArtistaCancionDeactivateView(RequiereArtista, View):
    def post(self, request, pk):
        artista_id = request.session['usuario_id']
        nombre = desactivar_cancion(pk, artista_id=artista_id)
        if nombre:
            messages.success(request, f'Canción "{nombre}" desactivada.')
        else:
            messages.error(request, 'No puedes desactivar esta canción.')
        return redirect('catalogo:artista_cancion_list')
