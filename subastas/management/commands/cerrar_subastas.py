from django.core.management.base import BaseCommand

from subastas.services import sincronizar_estados


class Command(BaseCommand):
    help = "Abre las subastas que ya empezaron y cierra las vencidas (se puede programar con cron)."

    def handle(self, *args, **options):
        sincronizar_estados()
        self.stdout.write(self.style.SUCCESS("Estados de subastas sincronizados."))
