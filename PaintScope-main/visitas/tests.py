from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from config import testutils as f
from notificaciones.models import Notificacion
from panel import parametros
from . import services
from .models import Visita


class VisitasTests(TestCase):  # PAIN-26 · RF-12 · CU-07
    def setUp(self):
        self.artista = f.usuario("artista")
        self.subasta = f.subasta_activa(artista=self.artista)
        self.obra = self.subasta.obra
        self.comprador = f.usuario("comprador", con_pago=True)
        self.client.force_login(self.comprador)

    def primer_horario(self, tipo="presencial"):
        libres = services.horarios_disponibles(self.obra, tipo)
        return next(iter(libres.values()))[0]

    def test_muestra_horarios_por_tipo(self):
        r = self.client.get(reverse("visitas:agendar", args=[self.obra.pk]) + "?tipo=virtual")
        self.assertContains(r, "Confirmar visita virtual")

    def test_agenda_confirma_y_notifica(self):
        h = self.primer_horario()
        r = self.client.post(reverse("visitas:agendar", args=[self.obra.pk]), {"tipo": "presencial", "horario": timezone.localtime(h).strftime("%Y-%m-%dT%H:%M")})
        self.assertRedirects(r, reverse("visitas:mis_visitas"))
        v = Visita.objects.get()
        self.assertEqual((v.obra, v.comprador, v.tipo, v.fecha_hora), (self.obra, self.comprador, "presencial", h))
        self.assertTrue(Notificacion.objects.filter(usuario=self.comprador, tipo="visita").exists())
        self.assertTrue(Notificacion.objects.filter(usuario=self.artista, tipo="visita").exists())
        self.assertContains(self.client.get(reverse("visitas:mis_visitas")), "Costa quieta")

    def test_franja_ocupada_deja_de_estar_disponible(self):
        h = self.primer_horario()
        services.agendar(self.obra, self.comprador, "presencial", h)
        todas = [x for fr in services.horarios_disponibles(self.obra, "presencial").values() for x in fr]
        self.assertNotIn(h, todas)
        with self.assertRaises(services.HorarioNoDisponible):
            services.agendar(self.obra, f.usuario("comprador"), "presencial", h)

    def test_virtual_y_presencial_no_se_bloquean_entre_si(self):
        h = self.primer_horario()
        services.agendar(self.obra, self.comprador, "presencial", h)
        todas = [x for fr in services.horarios_disponibles(self.obra, "virtual").values() for x in fr]
        self.assertIn(h, todas)

    def test_sin_horarios_lo_indica_y_sugiere_otras_fechas(self):
        parametros.guardar("visitas_dias_adelante", 1)
        parametros.guardar("visitas_hora_inicio", 0)
        parametros.guardar("visitas_hora_fin", 1)
        # La única franja del día (00:00) ya pasó, así que hoy no hay cupo
        r = self.client.get(reverse("visitas:agendar", args=[self.obra.pk]))
        self.assertContains(r, "No hay horarios disponibles")
        self.assertContains(r, "Otras fechas que sí tienen cupo")

    def test_horario_inventado_se_rechaza(self):
        r = self.client.post(reverse("visitas:agendar", args=[self.obra.pk]), {"tipo": "presencial", "horario": "2030-01-01T03:00"})
        self.assertContains(r, "ya no está disponible")
        self.assertFalse(Visita.objects.exists())

    def test_cancelar_libera_la_franja(self):
        h = self.primer_horario()
        v = services.agendar(self.obra, self.comprador, "presencial", h)
        self.client.post(reverse("visitas:cancelar", args=[v.pk]))
        v.refresh_from_db()
        self.assertEqual(v.estado, "cancelada")
        todas = [x for fr in services.horarios_disponibles(self.obra, "presencial").values() for x in fr]
        self.assertIn(h, todas)

    def test_solo_compradores_agendan(self):
        self.client.force_login(self.artista)
        self.assertEqual(self.client.get(reverse("visitas:agendar", args=[self.obra.pk])).status_code, 403)
