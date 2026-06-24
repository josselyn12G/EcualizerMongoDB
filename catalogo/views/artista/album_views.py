"""
Vistas de Album para el ARTISTA — migradas a MongoDB.
"""

from django.views.generic import View
from django.shortcuts import redirect, render
from django.contrib import messages

from usuarios.mixins import RequiereArtista
from ...forms.mongo_forms import MongoAlbumForm
from ...services.catalogo_mongo import (
    listar_albumes,
    get_album_ns,
    get_album_detalle,
    crear_album,
    actualizar_album,
    desactivar_album,
    eliminar_album,
    catalogo_tipos_album,
)


# ──────────────────────────────────────────────────────────
# LIST
# ──────────────────────────────────────────────────────────
class ArtistaAlbumListView(RequiereArtista, View):
    template_name = 'catalogo/artista/artista_album.html'

    def get(self, request):
        artista_id = request.session['usuario_id']
        busqueda = request.GET.get('q') or None
        estado = request.GET.get('estado') or None
        albumes = listar_albumes(artista_id=artista_id, estado=estado, busqueda=busqueda)
        return render(request, self.template_name, {
            'albumes': albumes,
            'busqueda': busqueda or '',
            'estado_actual': estado or '',
            'estados': [('activo', 'Activo'), ('inactivo', 'Inactivo')],
            'modo': 'list',
        })


# ──────────────────────────────────────────────────────────
# CREATE
# ──────────────────────────────────────────────────────────
class ArtistaAlbumCreateView(RequiereArtista, View):
    template_name = 'catalogo/artista/artista_album.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': MongoAlbumForm(tipo_choices=catalogo_tipos_album()),
            'modo': 'create',
        })

    def post(self, request):
        form = MongoAlbumForm(request.POST, tipo_choices=catalogo_tipos_album())
        if not form.is_valid():
            return render(request, self.template_name, {'form': form, 'modo': 'create'})
        d = form.cleaned_data
        try:
            crear_album(
                artista_id=request.session['usuario_id'],
                titulo=d['titulo'],
                fecha=d['fecha_lanzamiento'],
                descripcion=d.get('descripcion') or '',
                tipo=d['tipo'],
            )
            messages.success(request, 'Álbum creado correctamente.')
        except Exception as e:
            messages.error(request, f'Error al crear el álbum: {e}')
            return render(request, self.template_name, {'form': form, 'modo': 'create'})
        return redirect('catalogo:artista_album_list')


# ──────────────────────────────────────────────────────────
# DETAIL
# ──────────────────────────────────────────────────────────
class ArtistaAlbumDetailView(RequiereArtista, View):
    template_name = 'catalogo/artista/artista_album.html'

    def get(self, request, pk):
        artista_id = request.session['usuario_id']
        result = get_album_detalle(pk, artista_id=artista_id)
        if not result:
            messages.error(request, 'Álbum no encontrado o no es tuyo.')
            return redirect('catalogo:artista_album_list')
        album, canciones = result
        return render(request, self.template_name, {
            'album': album,
            'canciones': canciones,
            'modo': 'detail',
        })


# ──────────────────────────────────────────────────────────
# UPDATE
# ──────────────────────────────────────────────────────────
class ArtistaAlbumUpdateView(RequiereArtista, View):
    template_name = 'catalogo/artista/artista_album.html'

    def _get_album(self, pk, artista_id):
        return get_album_ns(pk, artista_id=artista_id)

    def get(self, request, pk):
        artista_id = request.session['usuario_id']
        album = self._get_album(pk, artista_id)
        if not album:
            messages.error(request, 'Álbum no encontrado.')
            return redirect('catalogo:artista_album_list')
        form = MongoAlbumForm(initial={
            'titulo': album.titulo_album,
            'fecha_lanzamiento': album.fecha_lanzamiento_album,
            'tipo': getattr(album.tipo_album, 'nombre_tipo', 'Album'),
            'descripcion': album.descripcion_album or '',
        }, tipo_choices=catalogo_tipos_album())
        return render(request, self.template_name, {
            'form': form, 'album': album, 'modo': 'update',
        })

    def post(self, request, pk):
        artista_id = request.session['usuario_id']
        album = self._get_album(pk, artista_id)
        if not album:
            messages.error(request, 'Álbum no encontrado.')
            return redirect('catalogo:artista_album_list')
        form = MongoAlbumForm(request.POST, tipo_choices=catalogo_tipos_album())
        if not form.is_valid():
            return render(request, self.template_name, {
                'form': form, 'album': album, 'modo': 'update',
            })
        d = form.cleaned_data
        ok = actualizar_album(
            pk=pk,
            titulo=d['titulo'],
            fecha=d['fecha_lanzamiento'],
            descripcion=d.get('descripcion') or '',
            tipo=d['tipo'],
            artista_id=artista_id,
        )
        if ok:
            messages.success(request, 'Álbum actualizado.')
        else:
            messages.error(request, 'No se pudo actualizar el álbum.')
        return redirect('catalogo:artista_album_list')


# ──────────────────────────────────────────────────────────
# DEACTIVATE
# ──────────────────────────────────────────────────────────
class ArtistaAlbumDeactivateView(RequiereArtista, View):
    def post(self, request, pk):
        artista_id = request.session['usuario_id']
        titulo = desactivar_album(pk, artista_id=artista_id)
        if titulo:
            messages.success(request, f'Álbum "{titulo}" desactivado.')
        else:
            messages.error(request, 'No se pudo desactivar (álbum no encontrado o no es tuyo).')
        return redirect('catalogo:artista_album_list')


# ──────────────────────────────────────────────────────────
# DELETE (permanente)
# ──────────────────────────────────────────────────────────
class ArtistaAlbumDeleteView(RequiereArtista, View):
    def post(self, request, pk):
        artista_id = request.session['usuario_id']
        titulo = eliminar_album(pk, artista_id=artista_id)
        if titulo:
            messages.success(request, f'Álbum "{titulo}" eliminado permanentemente.')
        else:
            messages.error(
                request,
                'No se pudo eliminar el álbum. Verifica que sea tuyo o usa "Desactivar".'
            )
        return redirect('catalogo:artista_album_list')
