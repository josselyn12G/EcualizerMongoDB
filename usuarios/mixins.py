from django.shortcuts import redirect
from django.contrib import messages


class RequiereLogin:
    """Redirige a login si no hay sesion activa."""
    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('usuario_id'):
            messages.error(request, 'Debes iniciar sesion para acceder.')
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)


class RequiereAdmin:
    """Redirige a login si el usuario no es administrador."""
    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('usuario_id'):
            messages.error(request, 'Debes iniciar sesion para acceder.')
            return redirect('login')
        if request.session.get('tipo_usuario') != 'administrador':
            messages.error(request, 'No tienes permisos para acceder al panel de administracion.')
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)


class RequiereArtista:
    """Solo artistas pueden acceder."""
    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('usuario_id'):
            messages.error(request, 'Debes iniciar sesion para acceder.')
            return redirect('login')
        if request.session.get('tipo_usuario') != 'artista':
            messages.error(request, 'Solo los artistas pueden acceder a esta seccion.')
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)


class RequiereOyente:
    """Solo oyentes (usuarios oyentes) pueden acceder."""
    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('usuario_id'):
            messages.error(request, 'Debes iniciar sesion para acceder.')
            return redirect('login')
        if request.session.get('tipo_usuario') != 'oyente':
            messages.error(request, 'Esta seccion es solo para oyentes.')
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)
