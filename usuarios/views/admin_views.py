"""Panel de administración · Gestión de usuarios sobre MongoDB.

Todas las vistas leen y escriben en la colección `Usuarios` de MongoDB Atlas
a través de usuarios.mongo_service (conexión centralizada vía config). No se
usa el ORM de SQL Server. Los objetos que se pasan a las plantillas conservan
la forma anidada original (objeto de subtipo con `.id_usuario` = Persona).
"""

from types import SimpleNamespace

from django.shortcuts import render, redirect
from django.views import View
from django.http import Http404
from django.contrib import messages

from usuarios.mixins import RequiereAdmin
from usuarios.forms import (
    MongoAdminPersonaForm, MongoAdminOyenteForm,
    MongoAdminArtistaForm, MongoAdminAdministradorForm,
)
from usuarios.mongo_service import (
    admin_dashboard_stats, admin_recent_users,
    admin_list_users, admin_get_user,
    admin_list_personas, admin_get_persona_detail,
    admin_update_user, admin_soft_delete,
)


def _ctx_admin(request):
    """Contexto base (admin conectado) para el sidebar/topbar.
    Se construye desde la SESIÓN (sin consultar MongoDB en cada página) para
    no añadir un round-trip a Atlas por request."""
    s = request.session
    if not s.get('usuario_id'):
        return {'admin_persona': None, 'admin_perfil': None}
    persona_admin = SimpleNamespace(
        primer_nombre=s.get('usuario_nombre', ''),
        primer_apellido=s.get('usuario_apellido', ''),
    )
    perfil_admin = SimpleNamespace(
        get_rol_admin_display=s.get('admin_rol') or 'Administrador',
    )
    return {
        'admin_persona': persona_admin,
        'admin_perfil': perfil_admin,
    }


def _persona_initial(persona):
    """Valores iniciales del formulario de datos personales."""
    return {
        'cedula_usuario': persona.cedula_usuario,
        'primer_nombre': persona.primer_nombre,
        'segundo_nombre': persona.segundo_nombre,
        'primer_apellido': persona.primer_apellido,
        'segundo_apellido': persona.segundo_apellido,
        'correo': persona.correo,
        'estado': persona.estado,
    }


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

class AdminDashboardView(RequiereAdmin, View):
    def get(self, request):
        ctx = _ctx_admin(request)
        ctx['stats'] = admin_dashboard_stats()
        ctx['recientes'] = admin_recent_users(5)
        return render(request, 'usuarios/admin/dashboard.html', ctx)


# ─────────────────────────────────────────────
# CRUD OYENTES
# ─────────────────────────────────────────────

class AdminOyenteListView(RequiereAdmin, View):
    def get(self, request):
        q = request.GET.get('q', '').strip()
        estado = request.GET.get('estado', '')
        ctx = _ctx_admin(request)
        ctx.update({
            'oyentes': admin_list_users('oyente', q, estado),
            'q': q, 'estado_sel': estado,
        })
        return render(request, 'usuarios/admin/usuarios/lista.html', ctx)


class AdminOyenteDetailView(RequiereAdmin, View):
    def get(self, request, pk):
        oyente = admin_get_user(pk, 'oyente')
        if not oyente:
            raise Http404('Oyente no encontrado')
        ctx = _ctx_admin(request)
        ctx['oyente'] = oyente
        return render(request, 'usuarios/admin/usuarios/detalle.html', ctx)


class AdminOyenteEditView(RequiereAdmin, View):
    template_name = 'usuarios/admin/usuarios/editar.html'

    def get(self, request, pk):
        oyente = admin_get_user(pk, 'oyente')
        if not oyente:
            raise Http404('Oyente no encontrado')
        p_form = MongoAdminPersonaForm(initial=_persona_initial(oyente.id_usuario), pk=pk)
        u_form = MongoAdminOyenteForm(initial={
            'alias': oyente.alias,
            'pais_usuario': oyente.pais_usuario,
            'fecha_nacimiento': oyente.fecha_nacimiento,
            'genero': oyente.genero,
        }, pk=pk)
        ctx = _ctx_admin(request)
        ctx.update({'oyente': oyente, 'p_form': p_form, 'u_form': u_form})
        return render(request, self.template_name, ctx)

    def post(self, request, pk):
        oyente = admin_get_user(pk, 'oyente')
        if not oyente:
            raise Http404('Oyente no encontrado')
        p_form = MongoAdminPersonaForm(request.POST, pk=pk)
        u_form = MongoAdminOyenteForm(request.POST, pk=pk)

        if p_form.is_valid() and u_form.is_valid():
            admin_update_user(
                pk, p_form.cleaned_data, u_form.cleaned_data, 'oyente',
                request.POST.get('nueva_contrasena', '').strip() or None,
            )
            messages.success(request, 'Oyente actualizado correctamente.')
            return redirect('admin_oyente_list')

        ctx = _ctx_admin(request)
        ctx.update({'oyente': oyente, 'p_form': p_form, 'u_form': u_form})
        return render(request, self.template_name, ctx)


class AdminOyenteDeleteView(RequiereAdmin, View):
    def get(self, request, pk):
        oyente = admin_get_user(pk, 'oyente')
        if not oyente:
            raise Http404('Oyente no encontrado')
        ctx = _ctx_admin(request)
        ctx.update({'objeto': oyente.id_usuario, 'tipo': 'oyente', 'pk': pk})
        return render(request, 'usuarios/admin/confirmar_eliminar.html', ctx)

    def post(self, request, pk):
        persona = admin_soft_delete(pk)
        if persona:
            messages.success(request, f'Oyente {persona.primer_nombre} desactivado.')
        return redirect('admin_oyente_list')


# ─────────────────────────────────────────────
# CRUD ARTISTAS
# ─────────────────────────────────────────────

class AdminArtistaListView(RequiereAdmin, View):
    def get(self, request):
        q = request.GET.get('q', '').strip()
        estado = request.GET.get('estado', '')
        ctx = _ctx_admin(request)
        ctx.update({
            'artistas': admin_list_users('artista', q, estado),
            'q': q, 'estado_sel': estado,
        })
        return render(request, 'usuarios/admin/artistas/lista.html', ctx)


class AdminArtistaDetailView(RequiereAdmin, View):
    def get(self, request, pk):
        artista = admin_get_user(pk, 'artista')
        if not artista:
            raise Http404('Artista no encontrado')
        ctx = _ctx_admin(request)
        ctx['artista'] = artista
        return render(request, 'usuarios/admin/artistas/detalle.html', ctx)


class AdminArtistaEditView(RequiereAdmin, View):
    template_name = 'usuarios/admin/artistas/editar.html'

    def get(self, request, pk):
        artista = admin_get_user(pk, 'artista')
        if not artista:
            raise Http404('Artista no encontrado')
        p_form = MongoAdminPersonaForm(initial=_persona_initial(artista.id_usuario), pk=pk)
        a_form = MongoAdminArtistaForm(initial={
            'nombre_artistico': artista.nombre_artistico,
            'biografia': artista.biografia,
        }, pk=pk)
        ctx = _ctx_admin(request)
        ctx.update({'artista': artista, 'p_form': p_form, 'a_form': a_form})
        return render(request, self.template_name, ctx)

    def post(self, request, pk):
        artista = admin_get_user(pk, 'artista')
        if not artista:
            raise Http404('Artista no encontrado')
        p_form = MongoAdminPersonaForm(request.POST, pk=pk)
        a_form = MongoAdminArtistaForm(request.POST, pk=pk)

        if p_form.is_valid() and a_form.is_valid():
            admin_update_user(
                pk, p_form.cleaned_data, a_form.cleaned_data, 'artista',
                request.POST.get('nueva_contrasena', '').strip() or None,
            )
            messages.success(request, 'Artista actualizado correctamente.')
            return redirect('admin_artista_list')

        ctx = _ctx_admin(request)
        ctx.update({'artista': artista, 'p_form': p_form, 'a_form': a_form})
        return render(request, self.template_name, ctx)


class AdminArtistaDeleteView(RequiereAdmin, View):
    def get(self, request, pk):
        artista = admin_get_user(pk, 'artista')
        if not artista:
            raise Http404('Artista no encontrado')
        ctx = _ctx_admin(request)
        ctx.update({'objeto': artista.id_usuario, 'tipo': 'artista', 'pk': pk})
        return render(request, 'usuarios/admin/confirmar_eliminar.html', ctx)

    def post(self, request, pk):
        persona = admin_soft_delete(pk)
        if persona:
            messages.success(request, f'Artista {persona.primer_nombre} desactivado.')
        return redirect('admin_artista_list')


# ─────────────────────────────────────────────
# CRUD PERSONAS · vista global de todas las personas
# ─────────────────────────────────────────────

class AdminPersonaListView(RequiereAdmin, View):
    """Lista todas las personas (cualquier tipo) con su rol calculado."""

    def get(self, request):
        q = request.GET.get('q', '').strip()
        estado = request.GET.get('estado', '')
        tipo = request.GET.get('tipo', '')
        personas = admin_list_personas(q, estado, tipo)
        ctx = _ctx_admin(request)
        ctx.update({
            'personas': personas,
            'q': q, 'estado_sel': estado, 'tipo_sel': tipo,
            'total': len(personas),
        })
        return render(request, 'usuarios/admin/personas/lista.html', ctx)


class AdminPersonaDetailView(RequiereAdmin, View):
    def get(self, request, pk):
        detalle = admin_get_persona_detail(pk)
        if not detalle:
            raise Http404('Persona no encontrada')
        persona, oyente_p, artista_p, admin_p = detalle
        ctx = _ctx_admin(request)
        ctx.update({
            'persona': persona,
            'oyente_p': oyente_p,
            'artista_p': artista_p,
            'admin_p': admin_p,
        })
        return render(request, 'usuarios/admin/personas/detalle.html', ctx)


# ─────────────────────────────────────────────
# CRUD ADMINISTRADORES
# ─────────────────────────────────────────────

class AdminAdminListView(RequiereAdmin, View):
    def get(self, request):
        q = request.GET.get('q', '').strip()
        estado = request.GET.get('estado', '')
        ctx = _ctx_admin(request)
        ctx.update({
            'admins': admin_list_users('admin', q, estado),
            'q': q, 'estado_sel': estado,
        })
        return render(request, 'usuarios/admin/admins/lista.html', ctx)


class AdminAdminDetailView(RequiereAdmin, View):
    def get(self, request, pk):
        admin = admin_get_user(pk, 'admin')
        if not admin:
            raise Http404('Administrador no encontrado')
        ctx = _ctx_admin(request)
        ctx['admin_obj'] = admin
        return render(request, 'usuarios/admin/admins/detalle.html', ctx)


class AdminAdminEditView(RequiereAdmin, View):
    template_name = 'usuarios/admin/admins/editar.html'

    def get(self, request, pk):
        admin = admin_get_user(pk, 'admin')
        if not admin:
            raise Http404('Administrador no encontrado')
        p_form = MongoAdminPersonaForm(initial=_persona_initial(admin.id_usuario), pk=pk)
        a_form = MongoAdminAdministradorForm(initial={
            'rol_admin': admin.rol_admin,
            'departamento': admin.departamento,
        }, pk=pk)
        ctx = _ctx_admin(request)
        ctx.update({'admin_obj': admin, 'p_form': p_form, 'a_form': a_form})
        return render(request, self.template_name, ctx)

    def post(self, request, pk):
        admin = admin_get_user(pk, 'admin')
        if not admin:
            raise Http404('Administrador no encontrado')
        p_form = MongoAdminPersonaForm(request.POST, pk=pk)
        a_form = MongoAdminAdministradorForm(request.POST, pk=pk)

        if p_form.is_valid() and a_form.is_valid():
            admin_update_user(
                pk, p_form.cleaned_data, a_form.cleaned_data, 'admin',
                request.POST.get('nueva_contrasena', '').strip() or None,
            )
            messages.success(request, 'Administrador actualizado correctamente.')
            return redirect('admin_admin_list')

        ctx = _ctx_admin(request)
        ctx.update({'admin_obj': admin, 'p_form': p_form, 'a_form': a_form})
        return render(request, self.template_name, ctx)


class AdminAdminDeleteView(RequiereAdmin, View):
    def get(self, request, pk):
        admin = admin_get_user(pk, 'admin')
        if not admin:
            raise Http404('Administrador no encontrado')
        ctx = _ctx_admin(request)
        ctx.update({'objeto': admin.id_usuario, 'tipo': 'administrador', 'pk': pk})
        return render(request, 'usuarios/admin/confirmar_eliminar.html', ctx)

    def post(self, request, pk):
        # Protección: un admin no puede desactivar su propia cuenta.
        if str(pk) == str(request.session.get('usuario_id')):
            messages.error(request, 'No puedes desactivar tu propia cuenta.')
            return redirect('admin_admin_list')
        persona = admin_soft_delete(pk)
        if persona:
            messages.success(request, f'Administrador {persona.primer_nombre} desactivado.')
        return redirect('admin_admin_list')
