"""
Comando para crear o actualizar el usuario administrador en MongoDB.
Uso: python manage.py crear_admin
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from datetime import datetime, timezone
from bson import ObjectId

from usuarios.mongo_service import get_database


ADMIN_CORREO = 'adminecualizer@hotmail.com'
ADMIN_CONTRASENA = 'admin12345'
ADMIN_CEDULA = '0000000001'


class Command(BaseCommand):
    help = 'Crea o actualiza el usuario administrador en MongoDB'

    def handle(self, *args, **options):
        db = get_database()
        col = db['Usuarios']

        # Verificar si ya existe
        existing = col.find_one({'correo': ADMIN_CORREO})

        hashed_pw = make_password(ADMIN_CONTRASENA)

        if existing:
            col.update_one(
                {'correo': ADMIN_CORREO},
                {'$set': {
                    'contrasena': hashed_pw,
                    'estado': 'activo',
                    'tipoUsuario': 'admin',
                    'perfilAdmin': {
                        'rolAdmin': 'Administrador general',
                        'departamento': 'Tecnologia',
                    }
                }}
            )
            self.stdout.write(self.style.SUCCESS(
                f'Admin actualizado: {ADMIN_CORREO}'
            ))
        else:
            doc = {
                'usuarioId': ObjectId(),
                'cedulaUsuario': ADMIN_CEDULA,
                'primerNombre': 'Admin',
                'segundoNombre': None,
                'primerApellido': 'Ecualizer',
                'segundoApellido': None,
                'correo': ADMIN_CORREO,
                'contrasena': hashed_pw,
                'fechaRegistro': datetime.now(timezone.utc),
                'estado': 'activo',
                'tipoUsuario': 'admin',
                'perfilAdmin': {
                    'rolAdmin': 'Administrador general',
                    'departamento': 'Tecnologia',
                }
            }
            col.insert_one(doc)
            self.stdout.write(self.style.SUCCESS(
                f'Admin creado: {ADMIN_CORREO}'
            ))

        self.stdout.write(self.style.SUCCESS('Listo. Ya puedes iniciar sesión.'))
