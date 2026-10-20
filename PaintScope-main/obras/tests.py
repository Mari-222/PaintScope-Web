from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from config import testutils as f
from notificaciones.models import Notificacion
from subastas.models import Subasta
from .models import Evento, Obra, Postulacion


@override_settings(MEDIA_ROOT="/tmp/paintscope_media_test")
class PortafolioTests(TestCase):  # PAIN-17 · RF-04 · CU-03
    def setUp(self):
        self.artista = f.usuario("artista")
        self.client.force_login(self.artista)

    def datos(self, **extra):
        d = {"titulo": "Luz", "descripcion": "Acuarela", "tecnica": "Acuarela sobre papel", "categoria": "Paisaje",
             "dimensiones": "40 × 30 cm", "anio": 2025, "imagen": f.imagen()}
        d.update(extra)
        return d

    def test_guarda_obra_en_estado_borrador(self):
        r = self.client.post(reverse("obras:obra_nueva"), self.datos())
        obra = Obra.objects.get()
        self.assertRedirects(r, reverse("obras:postular", args=[obra.pk]))
        self.assertEqual((obra.estado, obra.artista), ("borrador", self.artista))

    def test_campo_obligatorio_faltante_se_senala_y_no_guarda(self):
        r = self.client.post(reverse("obras:obra_nueva"), self.datos(titulo=""))
        self.assertContains(r, "obligatorio")
        self.assertFalse(Obra.objects.exists())

    def test_exige_imagen(self):
        d = self.datos(); del d["imagen"]
        r = self.client.post(reverse("obras:obra_nueva"), d)
        self.assertContains(r, "Sube una imagen")
        self.assertFalse(Obra.objects.exists())

    def test_solo_edita_sus_borradores(self):
        ajena = f.obra(f.usuario("artista"))
        self.assertEqual(self.client.get(reverse("obras:obra_editar", args=[ajena.pk])).status_code, 404)
        propia = f.obra(self.artista, estado="pendiente")
        r = self.client.get(reverse("obras:obra_editar", args=[propia.pk]))
        self.assertRedirects(r, reverse("obras:portafolio"))

    def test_portafolio_filtra_borradores(self):
        f.obra(self.artista, titulo="Borrador uno")
        f.obra(self.artista, titulo="En revisión", estado="pendiente")
        r = self.client.get(reverse("obras:portafolio") + "?ver=borradores")
        self.assertContains(r, "Borrador uno")
        self.assertNotContains(r, "En revisión")


class PostulacionTests(TestCase):  # PAIN-18 · RF-05 · CU-04
    def setUp(self):
        self.artista = f.usuario("artista")
        self.curador = f.usuario("curador")
        self.obra = f.obra(self.artista)
        self.client.force_login(self.artista)

    def test_postulacion_queda_pendiente_y_avisa_al_curador(self):
        evt = f.evento()
        r = self.client.post(reverse("obras:postular", args=[self.obra.pk]), {"evento": evt.pk})
        self.assertRedirects(r, reverse("obras:mis_postulaciones"))
        p = Postulacion.objects.get()
        self.assertEqual(p.estado, "pendiente")
        self.obra.refresh_from_db()
        self.assertEqual(self.obra.estado, "pendiente")
        self.assertTrue(Notificacion.objects.filter(usuario=self.curador, tipo="postulacion").exists())

    def test_convocatoria_cerrada_no_permite_postular(self):
        cerrado = f.evento(abierta=False)
        r = self.client.post(reverse("obras:postular", args=[self.obra.pk]), {"evento": cerrado.pk})
        self.assertContains(r, "ya cerró")
        self.assertFalse(Postulacion.objects.exists())

    def test_evento_sin_publicar_no_aparece_ni_se_acepta(self):
        borrador = f.evento(publicado=False)
        r = self.client.post(reverse("obras:postular", args=[self.obra.pk]), {"evento": borrador.pk})
        self.assertFalse(Postulacion.objects.exists())
        self.assertEqual(r.status_code, 200)

    def test_no_se_puede_postular_obra_ajena(self):
        ajena = f.obra(f.usuario("artista"))
        r = self.client.post(reverse("obras:postular", args=[ajena.pk]), {"evento": f.evento().pk})
        self.assertEqual(r.status_code, 404)


class EvaluacionTests(TestCase):  # PAIN-19 · RF-06 · CU-05
    def setUp(self):
        self.artista = f.usuario("artista")
        self.curador = f.usuario("curador")
        self.evento = f.evento()
        self.obra = f.obra(self.artista)
        from . import services
        self.post = services.postular(self.obra, self.evento)
        self.client.force_login(self.curador)
        self.url = reverse("obras:evaluar", args=[self.post.pk])

    def test_aprobar_define_precio_base_crea_subasta_y_notifica(self):
        r = self.client.post(self.url, {"decision": "aprobar", "precio_base": "800"})
        self.assertRedirects(r, reverse("obras:postulaciones"))
        self.obra.refresh_from_db()
        self.assertEqual((self.obra.estado, self.obra.precio_base, self.obra.curador), ("en_subasta", Decimal("800"), self.curador))
        s = Subasta.objects.get(obra=self.obra)
        self.assertEqual((s.precio_actual, s.estado), (Decimal("800"), "activa"))
        self.assertTrue(Notificacion.objects.filter(usuario=self.artista, tipo="obra_aprobada").exists())

    def test_aprobar_sin_precio_se_rechaza(self):
        r = self.client.post(self.url, {"decision": "aprobar"})
        self.assertContains(r, "precio base")
        self.assertFalse(Subasta.objects.exists())

    def test_rechazar_devuelve_a_borrador_con_motivo_y_notifica(self):
        r = self.client.post(self.url, {"decision": "rechazar", "motivo": "Falta una foto más nítida"})
        self.assertRedirects(r, reverse("obras:postulaciones"))
        self.obra.refresh_from_db()
        self.assertEqual((self.obra.estado, self.obra.motivo_rechazo), ("borrador", "Falta una foto más nítida"))
        self.assertTrue(Notificacion.objects.filter(usuario=self.artista, tipo="obra_rechazada", mensaje__contains="nítida").exists())

    def test_rechazar_sin_motivo_se_rechaza(self):
        r = self.client.post(self.url, {"decision": "rechazar", "motivo": " "})
        self.assertContains(r, "motivo")
        self.obra.refresh_from_db()
        self.assertEqual(self.obra.estado, "pendiente")

    def test_artista_no_puede_evaluar(self):
        self.client.force_login(self.artista)
        self.assertEqual(self.client.get(self.url).status_code, 403)


class EventosTests(TestCase):  # PAIN-20 · RF-07
    def setUp(self):
        self.curador = f.usuario("curador")
        self.client.force_login(self.curador)

    def datos(self, **extra):
        ahora = timezone.now()
        fmt = "%Y-%m-%dT%H:%M"
        d = {"nombre": "Semana Santa", "tematica": "Arte sacro", "temporada": "Semana Santa",
             "fecha_inicio": (ahora + timedelta(days=1)).strftime(fmt), "fecha_fin": (ahora + timedelta(days=8)).strftime(fmt),
             "cierre_convocatoria": (ahora + timedelta(days=5)).strftime(fmt)}
        d.update(extra)
        return d

    def test_crea_edita_y_publica(self):
        self.client.post(reverse("obras:evento_nuevo"), self.datos())
        e = Evento.objects.get()
        self.assertFalse(e.publicado)
        self.client.post(reverse("obras:evento_editar", args=[e.pk]), self.datos(nombre="Semana Santa Gregoriana"))
        e.refresh_from_db()
        self.assertEqual(e.nombre, "Semana Santa Gregoriana")
        self.client.post(reverse("obras:evento_publicar", args=[e.pk]))
        e.refresh_from_db()
        self.assertTrue(e.publicado)

    def test_valida_fechas(self):
        ahora = timezone.now()
        r = self.client.post(reverse("obras:evento_nuevo"), self.datos(fecha_fin=(ahora - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")))
        self.assertContains(r, "posterior al inicio")

    def test_asocia_obra_aprobada_a_evento_publicado(self):
        artista = f.usuario("artista")
        obra = f.obra(artista, estado="aprobada", precio_base=Decimal("300"))
        evt = f.evento()
        self.client.post(reverse("obras:evento_incluir_obra", args=[evt.pk]), {"obra": obra.pk})
        obra.refresh_from_db()
        self.assertEqual(obra.estado, "en_subasta")
        self.assertTrue(Subasta.objects.filter(obra=obra, evento=evt).exists())

    def test_no_asocia_a_evento_sin_publicar(self):
        obra = f.obra(f.usuario("artista"), estado="aprobada", precio_base=Decimal("300"))
        evt = f.evento(publicado=False)
        self.client.post(reverse("obras:evento_incluir_obra", args=[evt.pk]), {"obra": obra.pk})
        self.assertFalse(Subasta.objects.exists())
