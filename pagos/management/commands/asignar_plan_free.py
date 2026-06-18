"""
Comando: asigna el plan Free por defecto a todos los oyentes que aún
no tengan una suscripción activa.

Uso:
    python manage.py asignar_plan_free          # aplica los cambios
    python manage.py asignar_plan_free --dry-run  # solo muestra a cuántos afectaría
"""

from django.core.management.base import BaseCommand
from django.db import connection

from pagos.services import asegurar_plan_free


class Command(BaseCommand):
    help = 'Asigna el plan Free a los oyentes sin suscripción activa.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='No inserta nada; solo informa cuántos oyentes recibirían Free.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT u.idUsuario
                FROM Usuario.Usuario u
                WHERE NOT EXISTS (
                    SELECT 1 FROM Pagos.Suscripcion s
                    WHERE s.Usuario_idUsuario = u.idUsuario
                      AND s.estadoSuscripcion = 'activa'
                );
                """
            )
            ids = [r[0] for r in cur.fetchall()]

        if not ids:
            self.stdout.write(self.style.SUCCESS(
                'Todos los oyentes ya tienen una suscripción activa. Nada que hacer.'))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'[DRY-RUN] {len(ids)} oyente(s) recibirían el plan Free: {ids}'))
            return

        creados = 0
        for uid in ids:
            if asegurar_plan_free(uid):
                creados += 1

        self.stdout.write(self.style.SUCCESS(
            f'Plan Free asignado a {creados} oyente(s).'))
