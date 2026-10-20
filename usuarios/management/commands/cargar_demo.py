"""
Carga datos de demostración con las obras y artistas del prototipo de Figma.

    python manage.py cargar_demo

Contraseña de todas las cuentas demo: paintscope123
"""
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from obras import services as obras_services
from obras.models import Evento, Obra, Postulacion
from subastas.models import Puja, Subasta
from subastas.services import registrar_puja
from usuarios.models import MetodoPago, Usuario

CLAVE = "paintscope123"

U = "https://images.unsplash.com/"
OBRAS = [
    # titulo, artista, base, tecnica, categoria, año, medidas, imagen, horas restantes
    ("Jardín después de la lluvia", "Elena Montes", 1200, "Óleo sobre lienzo", "Paisaje", 2024, "80 × 110 cm", "photo-1689018159214-52338dc698fc?auto=format&fit=crop&w=1200&q=88", 2.2),
    ("Rosas de domingo", "Marina Sol", 650, "Óleo sobre tabla", "Naturaleza muerta", 2023, "50 × 38 cm", "photo-1685012851120-201c8cbaf77b?auto=format&fit=crop&w=900&q=88", 5.5),
    ("Pradera azul", "Tomás Rivas", 900, "Acrílico sobre lienzo", "Paisaje", 2024, "70 × 90 cm", "photo-1742294009985-a688e521f881?auto=format&fit=crop&w=1000&q=88", 32),
    ("Flores al viento", "Clara Vidal", 500, "Acuarela sobre papel", "Naturaleza muerta", 2022, "42 × 30 cm", "photo-1744572361096-fb9b48bbcbbc?auto=format&fit=crop&w=900&q=88", 0.7),
    ("Costa quieta", "Elena Montes", 1500, "Óleo sobre lienzo", "Paisaje", 2024, "90 × 120 cm", "photo-1775311406521-8f7897fda0aa?auto=format&fit=crop&w=1200&q=88", 3.8),
    ("Acantilado del norte", "Mateo Serra", 2000, "Óleo sobre tabla", "Paisaje", 2023, "100 × 140 cm", "photo-1784131164413-849ec9f15608?auto=format&fit=crop&w=1200&q=88", 8),
    ("Bouquet pálido", "Marina Sol", 740, "Óleo sobre lienzo", "Naturaleza muerta", 2024, "60 × 80 cm", "photo-1752312718801-b18f50e68f84?auto=format&fit=crop&w=1000&q=88", 36),
    ("Marea color", "Inés Alba", 820, "Técnica mixta", "Abstracto", 2023, "70 × 70 cm", "photo-1567061698906-fc74288ce52a?auto=format&fit=crop&w=1000&q=88", 6.3),
]


def _usuario(email, nombre, rol, **extra):
    usuario, creado = Usuario.objects.get_or_create(
        email=email, defaults={"first_name": nombre, "rol": rol, "is_staff": rol == "admin", **extra})
    if creado:
        usuario.set_password(CLAVE)
        usuario.save()
    return usuario


class Command(BaseCommand):
    help = "Crea usuarios, un evento y subastas de ejemplo basadas en el prototipo."

    @transaction.atomic
    def handle(self, *args, **options):
        admin = _usuario("admin@paintscope.demo", "Administrador", "admin")
        curador = _usuario("curador@paintscope.demo", "Curador Demo", "curador")
        compradores = [_usuario("lucia@paintscope.demo", "Lucía Prado", "comprador"),
                       _usuario("viajero@paintscope.demo", "Viajero", "comprador")]
        for c in compradores:
            if not c.metodos_pago.exists():
                MetodoPago.objects.create(usuario=c, tipo="credito", titular=c.first_name, ultimos4="4242", vencimiento="12/30")
        _usuario("sin-pago@paintscope.demo", "Comprador sin pago", "comprador")

        artistas = {}
        for nombre in ("Elena Montes", "Marina Sol", "Tomás Rivas", "Clara Vidal", "Mateo Serra", "Inés Alba"):
            correo = nombre.lower().replace(" ", ".").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o") + "@paintscope.demo"
            artistas[nombre] = _usuario(correo, nombre, "artista")

        ahora = timezone.now()
        evento, _ = Evento.objects.get_or_create(
            nombre="Artistas Locales", defaults=dict(
                tematica="Arte costarricense contemporáneo", temporada="Todo el año",
                fecha_inicio=ahora - timedelta(days=1), fecha_fin=ahora + timedelta(days=7),
                cierre_convocatoria=ahora + timedelta(days=5), publicado=True, creado_por=curador))

        if Obra.objects.exists():
            self.stdout.write("Ya había obras cargadas; solo se aseguraron usuarios y evento.")
            return

        for titulo, autor, base, tecnica, cat, anio, medidas, img, horas in OBRAS:
            obra = Obra.objects.create(
                artista=artistas[autor], titulo=titulo, tecnica=tecnica, categoria=cat, anio=anio,
                dimensiones=medidas, imagen_url=U + img,
                descripcion="Una escena íntima donde la luz atraviesa el paisaje en capas suaves. "
                            "La pincelada conserva el movimiento del aire y la memoria de una tarde húmeda.")
            post = obras_services.postular(obra, evento)
            subasta = obras_services.aprobar(post, curador, Decimal(base))
            Subasta.objects.filter(pk=subasta.pk).update(
                estado="activa", fecha_inicio=ahora - timedelta(hours=2), fecha_fin=ahora + timedelta(hours=horas))

        # Algunas pujas para que el dashboard tenga movimiento
        lucia, viajero = compradores
        for i, subasta in enumerate(Subasta.objects.order_by("pk")[:5]):
            registrar_puja(subasta.pk, viajero, subasta.precio_actual + 20)
            if i % 2 == 0:
                registrar_puja(subasta.pk, lucia, subasta.precio_actual + 30)

        # Un borrador y una postulación pendiente para probar el flujo del curador
        elena = artistas["Elena Montes"]
        Obra.objects.create(artista=elena, titulo="Luz sobre el estuario", tecnica="Acuarela sobre papel", categoria="Paisaje",
                            anio=2025, dimensiones="40 × 30 cm", imagen_url=U + "photo-1744572361096-fb9b48bbcbbc?auto=format&fit=crop&w=900&q=88",
                            descripcion="Borrador listo para postular.")
        pendiente = Obra.objects.create(artista=artistas["Inés Alba"], titulo="Mareas dobles", tecnica="Técnica mixta", categoria="Abstracto",
                                        anio=2025, dimensiones="60 × 60 cm", imagen_url=U + "photo-1567061698906-fc74288ce52a?auto=format&fit=crop&w=1000&q=88",
                                        descripcion="Pendiente de evaluación por el curador.")
        obras_services.postular(pendiente, evento)

        self.stdout.write(self.style.SUCCESS(
            "Datos de demostración listos. Cuentas: admin@, curador@, lucia@, viajero@, sin-pago@, "
            "elena.montes@ … @paintscope.demo · contraseña: " + CLAVE))
