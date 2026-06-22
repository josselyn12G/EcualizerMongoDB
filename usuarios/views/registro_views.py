"""
Vistas de registro (Oyente / Artista / Administrador).

Incluyen logging detallado en cada paso del proceso para facilitar el
diagnóstico cuando la creación de cuentas falla. Los mensajes de éxito
y error se envían vía el framework de messages → se muestran como popups
gracias al partial `usuarios/_popups.html`.
"""

import logging

from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from pymongo.errors import DuplicateKeyError, PyMongoError

from usuarios.forms import (
    RegistroPersonaForm, RegistroUsuarioForm,
    RegistroArtistaForm, RegistroAdministradorForm,
)
from usuarios.mongo_service import create_user_document, session_payload


logger = logging.getLogger('ecualizer.registro')


def _log_errores(prefijo, form):
    """Loguea TODOS los errores del form (field + non_field)."""
    if not form.errors:
        return
    logger.warning('%s · errores en %s: %s',
                   prefijo, form.__class__.__name__, form.errors.as_json())
    for campo, errs in form.errors.items():
        for err in errs:
            logger.warning('  · %s → %s', campo, err)


def _propagar_errores_a_messages(request, *forms):
    """Convierte errores de formularios en messages.error para popups."""
    for f in forms:
        # non_field errors
        for err in f.non_field_errors():
            messages.error(request, str(err))
        # field-level errors
        for campo, errs in f.errors.items():
            if campo == '__all__':
                continue
            label = f.fields[campo].label or campo if campo in f.fields else campo
            for err in errs:
                messages.error(request, f'{label}: {err}')


# ──────────────────────────────────────────────────────────
# REGISTRO OYENTE
# ──────────────────────────────────────────────────────────
class RegistroOyenteView(View):
    template_name = 'usuarios/registro/oyente_registro.html'

    def get(self, request):
        logger.debug('GET RegistroOyenteView')
        return render(request, self.template_name, {
            'persona_form': RegistroPersonaForm(),
            'usuario_form': RegistroUsuarioForm(),
            'paso_inicial': 1,
        })

    def post(self, request):
        logger.info('POST RegistroOyenteView · keys=%s',
                    list(request.POST.keys()))

        persona_form = RegistroPersonaForm(request.POST)
        usuario_form = RegistroUsuarioForm(request.POST)

        p_ok = persona_form.is_valid()
        u_ok = usuario_form.is_valid()
        logger.info('Validación · persona=%s usuario=%s', p_ok, u_ok)

        if p_ok and u_ok:
            try:
                persona = create_user_document(
                    persona_form.cleaned_data,
                    'oyente',
                    usuario_form.cleaned_data,
                )
                logger.info('Registro oyente COMPLETADO id=%s', persona.id_usuario)

                request.session.update(session_payload(persona))

                messages.success(
                    request,
                    f'¡Bienvenido a Ecualizer, {persona.primer_nombre}! '
                    f'Tu cuenta de oyente fue creada correctamente.'
                )
                return redirect('dashboard_oyente')

            except (DuplicateKeyError, PyMongoError, ValueError, TypeError):
                persona_form.add_error(None, 'Ya existe una cuenta con esos datos.')
                messages.error(request, 'Ya existe una cuenta con esos datos.')
            except (KeyError, AttributeError) as e:
                logger.exception('Excepción inesperada al crear oyente')
                persona_form.add_error(None, f'Error inesperado: {e}')
                messages.error(request, f'Error inesperado: {e}')
        else:
            _log_errores('OYENTE persona', persona_form)
            _log_errores('OYENTE usuario',  usuario_form)
            _propagar_errores_a_messages(request, persona_form, usuario_form)
            messages.info(
                request,
                'Revisa los campos resaltados y vuelve a intentarlo.'
            )

        paso = 2 if (usuario_form.errors and not persona_form.errors) else 1
        return render(request, self.template_name, {
            'persona_form': persona_form,
            'usuario_form': usuario_form,
            'paso_inicial': paso,
        })


# ──────────────────────────────────────────────────────────
# REGISTRO ARTISTA
# ──────────────────────────────────────────────────────────
class RegistroArtistaView(View):
    template_name = 'usuarios/registro/artista_registro.html'

    def get(self, request):
        logger.debug('GET RegistroArtistaView')
        return render(request, self.template_name, {
            'persona_form': RegistroPersonaForm(),
            'artista_form': RegistroArtistaForm(),
            'paso_inicial': 1,
        })

    def post(self, request):
        logger.info('POST RegistroArtistaView · keys=%s',
                    list(request.POST.keys()))

        persona_form = RegistroPersonaForm(request.POST)
        artista_form = RegistroArtistaForm(request.POST)

        p_ok = persona_form.is_valid()
        a_ok = artista_form.is_valid()
        logger.info('Validación · persona=%s artista=%s', p_ok, a_ok)

        if p_ok and a_ok:
            try:
                persona = create_user_document(
                    persona_form.cleaned_data,
                    'artista',
                    artista_form.cleaned_data,
                )
                logger.info('Registro artista COMPLETADO id=%s', persona.id_usuario)

                request.session.update(session_payload(persona))

                messages.success(
                    request,
                    f'¡Bienvenido a Ecualizer, {persona.artista.nombre_artistico}! '
                    f'Tu cuenta de artista fue creada correctamente.'
                )
                return redirect('dashboard_artista')

            except (DuplicateKeyError, PyMongoError, ValueError, TypeError):
                persona_form.add_error(None, 'Ya existe una cuenta con esos datos.')
                messages.error(request, 'Ya existe una cuenta con esos datos.')
            except (KeyError, AttributeError) as e:
                logger.exception('Excepción inesperada al crear artista')
                persona_form.add_error(None, f'Error inesperado: {e}')
                messages.error(request, f'Error inesperado: {e}')
        else:
            _log_errores('ARTISTA persona', persona_form)
            _log_errores('ARTISTA artista', artista_form)
            _propagar_errores_a_messages(request, persona_form, artista_form)
            messages.info(
                request,
                'Revisa los campos resaltados y vuelve a intentarlo.'
            )

        paso = 2 if (artista_form.errors and not persona_form.errors) else 1
        return render(request, self.template_name, {
            'persona_form': persona_form,
            'artista_form': artista_form,
            'paso_inicial': paso,
        })


# ──────────────────────────────────────────────────────────
# REGISTRO ADMIN
# ──────────────────────────────────────────────────────────
class RegistroAdminView(View):
    template_name = 'usuarios/registro/admin_registro.html'

    def get(self, request):
        return render(request, self.template_name, {
            'persona_form': RegistroPersonaForm(),
            'admin_form': RegistroAdministradorForm(),
            'paso_inicial': 1,
        })

    def post(self, request):
        logger.info('POST RegistroAdminView · keys=%s',
                    list(request.POST.keys()))

        persona_form = RegistroPersonaForm(request.POST)
        admin_form = RegistroAdministradorForm(request.POST)

        p_ok = persona_form.is_valid()
        a_ok = admin_form.is_valid()
        logger.info('Validación · persona=%s admin=%s', p_ok, a_ok)

        if p_ok and a_ok:
            try:
                persona = create_user_document(
                    persona_form.cleaned_data,
                    'admin',
                    admin_form.cleaned_data,
                )
                request.session.update(session_payload(persona))
                request.session['tipo_usuario'] = 'admin'
                messages.success(
                    request,
                    f'¡Bienvenido al panel, {persona.primer_nombre}!'
                )
                return redirect('admin_dashboard')
            except (DuplicateKeyError, PyMongoError, ValueError, TypeError):
                persona_form.add_error(None, 'Ya existe una cuenta con esos datos.')
                messages.error(request, 'Ya existe una cuenta con esos datos.')
            except (KeyError, AttributeError) as e:
                logger.exception('Excepción inesperada al crear admin')
                persona_form.add_error(None, f'Error inesperado: {e}')
                messages.error(request, f'Error inesperado: {e}')
        else:
            _log_errores('ADMIN persona', persona_form)
            _log_errores('ADMIN admin',    admin_form)
            _propagar_errores_a_messages(request, persona_form, admin_form)
            messages.info(
                request,
                'Revisa los campos resaltados y vuelve a intentarlo.'
            )

        paso = 2 if (admin_form.errors and not persona_form.errors) else 1
        return render(request, self.template_name, {
            'persona_form': persona_form,
            'admin_form': admin_form,
            'paso_inicial': paso,
        })
