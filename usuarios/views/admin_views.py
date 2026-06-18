from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.hashers import make_password

from ..models import Persona, Usuario, Artista, Administrador
from ..mixins import RequiereAdmin
from ..forms import (
    AdminEditPersonaForm, AdminEditUsuarioForm,
    AdminEditArtistaForm, AdminEditAdministradorForm,
)


def _ctx_admin(request):
    """Contexto base para todas las vistas del panel admin."""
    uid = request.session.get('usuario_id')
    perfil_admin = None
    persona_admin = None
    if uid:
        try:
            persona_admin = Persona.objects.get(pk=uid)
            perfil_admin = persona_admin.administrador
        except (Persona.DoesNotExist, Administrador.DoesNotExist):
            pass
    return {
        'admin_persona': persona_admin,
        'admin_perfil': perfil_admin,
    }


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

class AdminDashboardView(RequiereAdmin, View):
    def get(self, request):
        total_oyentes = Usuario.objects.count()
        total_artistas = Artista.objects.count()
        total_admins = Administrador.objects.count()

        activos = Persona.objects.filter(estado='activo').count()
        inactivos = Persona.objects.filter(estado='inactivo').count()
        suspendidos = Persona.objects.filter(estado='suspendido').count()

        recientes = Persona.objects.order_by('-fecha_registro', '-id_usuario')[:5]

        ctx = _ctx_admin(request)
        ctx.update({
            'stats': {
                'oyentes': total_oyentes,
                'artistas': total_artistas,
                'admins': total_admins,
                'activos': activos,
                'inactivos': inactivos,
                'suspendidos': suspendidos,
            },
            'recientes': recientes,
        })
        return render(request, 'usuarios/admin/dashboard.html', ctx)


# ─────────────────────────────────────────────
# CRUD OYENTES
# ─────────────────────────────────────────────

class AdminOyenteListView(RequiereAdmin, View):
    def get(self, request):
        qs = Usuario.objects.select_related('id_usuario').all()
        q = request.GET.get('q', '').strip()
        estado = request.GET.get('estado', '')

        if q:
            qs = qs.filter(
                Q(id_usuario__primer_nombre__icontains=q) |
                Q(id_usuario__primer_apellido__icontains=q) |
                Q(id_usuario__correo__icontains=q) |
                Q(alias__icontains=q)
            )
        if estado:
            qs = qs.filter(id_usuario__estado=estado)

        ctx = _ctx_admin(request)
        ctx.update({'oyentes': qs, 'q': q, 'estado_sel': estado})
        return render(request, 'usuarios/admin/usuarios/lista.html', ctx)


class AdminOyenteDetailView(RequiereAdmin, View):
    def get(self, request, pk):
        oyente = get_object_or_404(Usuario, pk=pk)
        ctx = _ctx_admin(request)
        ctx['oyente'] = oyente
        return render(request, 'usuarios/admin/usuarios/detalle.html', ctx)


class AdminOyenteEditView(RequiereAdmin, View):
    template_name = 'usuarios/admin/usuarios/editar.html'

    def _get_forms(self, request, oyente, data=None):
        return (
            AdminEditPersonaForm(data, instance=oyente.id_usuario),
            AdminEditUsuarioForm(data, instance=oyente),
        )

    def get(self, request, pk):
        oyente = get_object_or_404(Usuario, pk=pk)
        p_form, u_form = self._get_forms(request, oyente)
        ctx = _ctx_admin(request)
        ctx.update({'oyente': oyente, 'p_form': p_form, 'u_form': u_form})
        return render(request, self.template_name, ctx)

    def post(self, request, pk):
        oyente = get_object_or_404(Usuario, pk=pk)
        p_form, u_form = self._get_forms(request, oyente, request.POST)

        if p_form.is_valid() and u_form.is_valid():
            persona = p_form.save(commit=False)
            nueva_pass = request.POST.get('nueva_contrasena', '').strip()
            if nueva_pass:
                persona.contrasena = make_password(nueva_pass)
            persona.save()
            u_form.save()
            messages.success(request, 'Oyente actualizado correctamente.')
            return redirect('admin_oyente_list')

        ctx = _ctx_admin(request)
        ctx.update({'oyente': oyente, 'p_form': p_form, 'u_form': u_form})
        return render(request, self.template_name, ctx)


class AdminOyenteDeleteView(RequiereAdmin, View):
    def get(self, request, pk):
        oyente = get_object_or_404(Usuario, pk=pk)
        ctx = _ctx_admin(request)
        ctx.update({'objeto': oyente.id_usuario, 'tipo': 'oyente', 'pk': pk})
        return render(request, 'usuarios/admin/confirmar_eliminar.html', ctx)

    def post(self, request, pk):
        oyente = get_object_or_404(Usuario, pk=pk)
        persona = oyente.id_usuario
        persona.estado = 'inactivo'
        persona.save()
        messages.success(request, f'Oyente {persona.primer_nombre} desactivado.')
        return redirect('admin_oyente_list')


# ─────────────────────────────────────────────
# CRUD ARTISTAS
# ─────────────────────────────────────────────

class AdminArtistaListView(RequiereAdmin, View):
    def get(self, request):
        qs = Artista.objects.select_related('id_usuario').all()
        q = request.GET.get('q', '').strip()
        estado = request.GET.get('estado', '')

        if q:
            qs = qs.filter(
                Q(id_usuario__primer_nombre__icontains=q) |
                Q(id_usuario__primer_apellido__icontains=q) |
                Q(id_usuario__correo__icontains=q) |
                Q(nombre_artistico__icontains=q)
            )
        if estado:
            qs = qs.filter(id_usuario__estado=estado)

        ctx = _ctx_admin(request)
        ctx.update({'artistas': qs, 'q': q, 'estado_sel': estado})
        return render(request, 'usuarios/admin/artistas/lista.html', ctx)


class AdminArtistaDetailView(RequiereAdmin, View):
    def get(self, request, pk):
        artista = get_object_or_404(Artista, pk=pk)
        ctx = _ctx_admin(request)
        ctx['artista'] = artista
        return render(request, 'usuarios/admin/artistas/detalle.html', ctx)


class AdminArtistaEditView(RequiereAdmin, View):
    template_name = 'usuarios/admin/artistas/editar.html'

    def _get_forms(self, request, artista, data=None):
        return (
            AdminEditPersonaForm(data, instance=artista.id_usuario),
            AdminEditArtistaForm(data, instance=artista),
        )

    def get(self, request, pk):
        artista = get_object_or_404(Artista, pk=pk)
        p_form, a_form = self._get_forms(request, artista)
        ctx = _ctx_admin(request)
        ctx.update({'artista': artista, 'p_form': p_form, 'a_form': a_form})
        return render(request, self.template_name, ctx)

    def post(self, request, pk):
        artista = get_object_or_404(Artista, pk=pk)
        p_form, a_form = self._get_forms(request, artista, request.POST)

        if p_form.is_valid() and a_form.is_valid():
            persona = p_form.save(commit=False)
            nueva_pass = request.POST.get('nueva_contrasena', '').strip()
            if nueva_pass:
                persona.contrasena = make_password(nueva_pass)
            persona.save()
            a_form.save()
            messages.success(request, 'Artista actualizado correctamente.')
            return redirect('admin_artista_list')

        ctx = _ctx_admin(request)
        ctx.update({'artista': artista, 'p_form': p_form, 'a_form': a_form})
        return render(request, self.template_name, ctx)


class AdminArtistaDeleteView(RequiereAdmin, View):
    def get(self, request, pk):
        artista = get_object_or_404(Artista, pk=pk)
        ctx = _ctx_admin(request)
        ctx.update({'objeto': artista.id_usuario, 'tipo': 'artista', 'pk': pk})
        return render(request, 'usuarios/admin/confirmar_eliminar.html', ctx)

    def post(self, request, pk):
        artista = get_object_or_404(Artista, pk=pk)
        persona = artista.id_usuario
        persona.estado = 'inactivo'
        persona.save()
        messages.success(request, f'Artista {artista.nombre_artistico} desactivado.')
        return redirect('admin_artista_list')


# ─────────────────────────────────────────────
# CRUD PERSONAS · vista global de todas las personas
# (Persona es el supertipo de Oyente/Artista/Admin)
# ─────────────────────────────────────────────

class AdminPersonaListView(RequiereAdmin, View):
    """Lista todas las Personas con su rol calculado.
    No tiene paginación → muestra todos los registros."""

    def get(self, request):
        qs = Persona.objects.all().order_by('-fecha_registro', '-id_usuario')

        q = request.GET.get('q', '').strip()
        estado = request.GET.get('estado', '')
        tipo = request.GET.get('tipo', '')

        if q:
            qs = qs.filter(
                Q(primer_nombre__icontains=q) |
                Q(primer_apellido__icontains=q) |
                Q(correo__icontains=q) |
                Q(cedula_usuario__icontains=q)
            )
        if estado:
            qs = qs.filter(estado=estado)

        # Materializamos para poder calcular tipo por cada persona.
        # Las queries de subtype son rápidas (PK lookups).
        oyente_ids = set(Usuario.objects.values_list('id_usuario_id', flat=True))
        artista_ids = set(Artista.objects.values_list('id_usuario_id', flat=True))
        admin_ids = set(Administrador.objects.values_list('id_usuario_id', flat=True))

        personas = []
        for p in qs:
            tipo_persona = []
            if p.id_usuario in oyente_ids:
                tipo_persona.append('oyente')
            if p.id_usuario in artista_ids:
                tipo_persona.append('artista')
            if p.id_usuario in admin_ids:
                tipo_persona.append('administrador')
            p.tipos = tipo_persona  # atributo dinámico para el template
            p.tipo_principal = tipo_persona[0] if tipo_persona else 'sin rol'
            if not tipo or p.tipo_principal == tipo:
                personas.append(p)

        ctx = _ctx_admin(request)
        ctx.update({
            'personas': personas,
            'q': q, 'estado_sel': estado, 'tipo_sel': tipo,
            'total': len(personas),
        })
        return render(request, 'usuarios/admin/personas/lista.html', ctx)


class AdminPersonaDetailView(RequiereAdmin, View):
    def get(self, request, pk):
        persona = get_object_or_404(Persona, pk=pk)
        # Detectar todos los perfiles asociados
        try:
            oyente = Usuario.objects.get(pk=persona.pk)
        except Usuario.DoesNotExist:
            oyente = None
        try:
            artista = Artista.objects.get(pk=persona.pk)
        except Artista.DoesNotExist:
            artista = None
        try:
            admin_perfil = Administrador.objects.get(pk=persona.pk)
        except Administrador.DoesNotExist:
            admin_perfil = None

        ctx = _ctx_admin(request)
        ctx.update({
            'persona': persona,
            'oyente_p': oyente,
            'artista_p': artista,
            'admin_p': admin_perfil,
        })
        return render(request, 'usuarios/admin/personas/detalle.html', ctx)


# ─────────────────────────────────────────────
# CRUD ADMINISTRADORES
# ─────────────────────────────────────────────

class AdminAdminListView(RequiereAdmin, View):
    def get(self, request):
        qs = Administrador.objects.select_related('id_usuario').all()
        q = request.GET.get('q', '').strip()
        estado = request.GET.get('estado', '')

        if q:
            qs = qs.filter(
                Q(id_usuario__primer_nombre__icontains=q) |
                Q(id_usuario__primer_apellido__icontains=q) |
                Q(id_usuario__correo__icontains=q)
            )
        if estado:
            qs = qs.filter(id_usuario__estado=estado)

        ctx = _ctx_admin(request)
        ctx.update({'admins': qs, 'q': q, 'estado_sel': estado})
        return render(request, 'usuarios/admin/admins/lista.html', ctx)


class AdminAdminDetailView(RequiereAdmin, View):
    def get(self, request, pk):
        admin = get_object_or_404(Administrador, pk=pk)
        ctx = _ctx_admin(request)
        ctx['admin_obj'] = admin
        return render(request, 'usuarios/admin/admins/detalle.html', ctx)


class AdminAdminEditView(RequiereAdmin, View):
    template_name = 'usuarios/admin/admins/editar.html'

    def _get_forms(self, request, admin, data=None):
        return (
            AdminEditPersonaForm(data, instance=admin.id_usuario),
            AdminEditAdministradorForm(data, instance=admin),
        )

    def get(self, request, pk):
        admin = get_object_or_404(Administrador, pk=pk)
        p_form, a_form = self._get_forms(request, admin)
        ctx = _ctx_admin(request)
        ctx.update({'admin_obj': admin, 'p_form': p_form, 'a_form': a_form})
        return render(request, self.template_name, ctx)

    def post(self, request, pk):
        admin = get_object_or_404(Administrador, pk=pk)
        p_form, a_form = self._get_forms(request, admin, request.POST)

        if p_form.is_valid() and a_form.is_valid():
            persona = p_form.save(commit=False)
            nueva_pass = request.POST.get('nueva_contrasena', '').strip()
            if nueva_pass:
                persona.contrasena = make_password(nueva_pass)
            persona.save()
            a_form.save()
            messages.success(request, 'Administrador actualizado correctamente.')
            return redirect('admin_admin_list')

        ctx = _ctx_admin(request)
        ctx.update({'admin_obj': admin, 'p_form': p_form, 'a_form': a_form})
        return render(request, self.template_name, ctx)


class AdminAdminDeleteView(RequiereAdmin, View):
    def get(self, request, pk):
        admin = get_object_or_404(Administrador, pk=pk)
        ctx = _ctx_admin(request)
        ctx.update({'objeto': admin.id_usuario, 'tipo': 'administrador', 'pk': pk})
        return render(request, 'usuarios/admin/confirmar_eliminar.html', ctx)

    def post(self, request, pk):
        admin = get_object_or_404(Administrador, pk=pk)
        persona = admin.id_usuario
        # Proteger: no desactivar al propio admin logueado
        if persona.id_usuario == request.session.get('usuario_id'):
            messages.error(request, 'No puedes desactivar tu propia cuenta.')
            return redirect('admin_admin_list')
        persona.estado = 'inactivo'
        persona.save()
        messages.success(request, f'Administrador {persona.primer_nombre} desactivado.')
        return redirect('admin_admin_list')
