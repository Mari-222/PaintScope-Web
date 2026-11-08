import json
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from config import testutils as f
from notificaciones.models import Notificacion
from panel import parametros
from usuarios.models import MetodoPago
from . import services
from .models import Puja, Subasta


class PujaTests(TestCase):  # PAIN-22 · PAIN-24 · RF-09 · RF-16 · CU-06
    def setUp(self):
        self.subasta = f.subasta_activa(base=500)
        self.comprador = f.usuario("comprador", con_pago=True)
        self.client.force_login(self.comprador)

    def pujar(self, monto):
        return self.client.post(reverse("subastas:pujar", args=[self.subasta.pk]), {"monto": monto}, follow=True)

    def test_puja_valida_se_registra_y_actualiza_precio(self):
        r = self.pujar("550")
        self.subasta.refresh_from_db()
        self.assertEqual(self.subasta.precio_actual, Decimal("550"))
        self.assertEqual(Puja.objects.count(), 1)
        self.assertContains(r, "quedó registrada")

    def test_monto_igual_o_menor_se_rechaza_y_pide_mayor(self):
        for monto in ("500", "400"):
            r = self.pujar(monto)
            self.assertContains(r, "mayor a la puja actual")
        self.assertFalse(Puja.objects.exists())
        self.subasta.refresh_from_db()
        self.assertEqual(self.subasta.precio_actual, Decimal("500"))

    def test_monto_no_numerico_se_rechaza(self):
        self.assertContains(self.pujar("abc"), "monto numérico")

    def test_sin_metodo_de_pago_se_bloquea(self):
        sin_pago = f.usuario("comprador")
        self.client.force_login(sin_pago)
        r = self.pujar("600")
        self.assertContains(r, "método de pago")
        self.assertFalse(Puja.objects.exists())
        detalle = self.client.get(reverse("subastas:detalle", args=[self.subasta.pk]))
        self.assertContains(detalle, "método de pago registrado")

    def test_registrar_metodo_desbloquea_la_puja(self):
        sin_pago = f.usuario("comprador")
        self.client.force_login(sin_pago)
        self.client.post(reverse("agregar_metodo_pago"), {"tipo": "debito", "titular": "A", "numero": "4242424242424242", "vencimiento": "12/39"})
        self.pujar("650")
        self.assertEqual(Puja.objects.count(), 1)

    def test_solo_compradores_pujan(self):
        for rol in ("curador",):
            self.client.force_login(f.usuario(rol))
            self.assertEqual(self.client.post(reverse("subastas:pujar", args=[self.subasta.pk]), {"monto": "900"}).status_code, 403)
        with self.assertRaises(services.PujaRechazada):
            services.registrar_puja(self.subasta.pk, f.usuario("curador"), 900)

    def test_artista_con_metodo_de_pago_puede_pujar(self):
        otro = f.usuario("artista", con_pago=True)
        self.client.force_login(otro)
        self.pujar("550")
        self.assertEqual(Puja.objects.count(), 1)

    def test_artista_no_puede_pujar_por_su_propia_obra(self):
        self.client.force_login(self.subasta.obra.artista)
        MetodoPago.objects.create(usuario=self.subasta.obra.artista, titular="A", ultimos4="4242", vencimiento="12/39")
        self.assertContains(self.pujar("550"), "propia obra")
        self.assertFalse(Puja.objects.exists())

    def test_pujas_suspendidas_por_moderacion(self):
        Subasta.objects.filter(pk=self.subasta.pk).update(pujas_suspendidas=True)
        self.assertContains(self.pujar("700"), "suspendidas")
        self.assertFalse(Puja.objects.exists())

    def test_no_se_puja_en_subasta_vencida(self):
        Subasta.objects.filter(pk=self.subasta.pk).update(fecha_fin=timezone.now() - timedelta(minutes=1))
        with self.assertRaises(services.PujaRechazada):
            services.registrar_puja(self.subasta.pk, self.comprador, 900)
            
    def test_puja_confirmada_notifica_al_comprador(self):
        self.pujar("550")
        aviso = Notificacion.objects.get(usuario=self.comprador, tipo="puja_confirmada")
        self.assertIn("550", aviso.mensaje)

    def test_puja_rechazada_no_genera_confirmacion(self):
        self.pujar("100")
        self.assertFalse(Notificacion.objects.filter(tipo="puja_confirmada").exists())


class ExtensionDinamicaTests(TestCase):  # PAIN-23 · RF-10
    def setUp(self):
        self.subasta = f.subasta_activa(base=100)
        self.comprador = f.usuario("comprador", con_pago=True)

    def fijar_fin(self, minutos):
        Subasta.objects.filter(pk=self.subasta.pk).update(fecha_fin=timezone.now() + timedelta(minutes=minutos))
        self.subasta.refresh_from_db()
        return self.subasta.fecha_fin

    def test_puja_en_los_ultimos_minutos_extiende_6_horas(self):
        fin = self.fijar_fin(3)
        puja = services.registrar_puja(self.subasta.pk, self.comprador, 150)
        self.subasta.refresh_from_db()
        self.assertTrue(puja.extendida)
        self.assertEqual(self.subasta.fecha_fin - fin, timedelta(hours=6))
        self.assertEqual(self.subasta.extensiones, 1)

    def test_puja_fuera_de_la_ventana_no_extiende(self):
        fin = self.fijar_fin(120)
        puja = services.registrar_puja(self.subasta.pk, self.comprador, 150)
        self.subasta.refresh_from_db()
        self.assertFalse(puja.extendida)
        self.assertEqual(self.subasta.fecha_fin, fin)

    def test_parametros_globales_cambian_la_regla(self):
        parametros.guardar("ventana_extension_minutos", 30)
        parametros.guardar("horas_extension", 2)
        fin = self.fijar_fin(20)
        services.registrar_puja(self.subasta.pk, self.comprador, 150)
        self.subasta.refresh_from_db()
        self.assertEqual(self.subasta.fecha_fin - fin, timedelta(hours=2))


class CierreTests(TestCase):  # RF-14 · cierre de subasta
    def setUp(self):
        self.artista = f.usuario("artista")
        self.subasta = f.subasta_activa(artista=self.artista, base=200)
        self.a = f.usuario("comprador", con_pago=True)
        self.b = f.usuario("comprador", con_pago=True)

    def vencer(self):
        Subasta.objects.filter(pk=self.subasta.pk).update(fecha_fin=timezone.now() - timedelta(seconds=5))

    def test_puja_superada_notifica_al_anterior(self):
        services.registrar_puja(self.subasta.pk, self.a, 250)
        services.registrar_puja(self.subasta.pk, self.b, 300)
        self.assertTrue(Notificacion.objects.filter(usuario=self.a, tipo="puja_superada").exists())
        self.assertFalse(Notificacion.objects.filter(usuario=self.b, tipo="puja_superada").exists())

    def test_al_cerrar_define_ganador_y_notifica_a_todos(self):
        services.registrar_puja(self.subasta.pk, self.a, 250)
        services.registrar_puja(self.subasta.pk, self.b, 300)
        self.vencer()
        services.sincronizar_estados()
        self.subasta.refresh_from_db()
        self.assertEqual((self.subasta.estado, self.subasta.ganador), ("cerrada", self.b))
        self.subasta.obra.refresh_from_db()
        self.assertEqual(self.subasta.obra.estado, "vendida")
        self.assertTrue(Notificacion.objects.filter(usuario=self.b, tipo="subasta_ganada").exists())
        self.assertTrue(Notificacion.objects.filter(usuario=self.a, tipo="subasta_cerrada").exists())
        self.assertTrue(Notificacion.objects.filter(usuario=self.artista, tipo="subasta_cerrada").exists())

    def test_cierre_es_idempotente(self):
        services.registrar_puja(self.subasta.pk, self.a, 250)
        self.vencer()
        services.sincronizar_estados(); services.sincronizar_estados()
        self.assertEqual(Notificacion.objects.filter(usuario=self.a, tipo="subasta_ganada").count(), 1)

    def test_sin_pujas_la_obra_vuelve_a_aprobada(self):
        self.vencer()
        services.sincronizar_estados()
        self.subasta.obra.refresh_from_db()
        self.assertEqual(self.subasta.obra.estado, "aprobada")
        self.subasta.refresh_from_db()
        self.assertIsNone(self.subasta.ganador)

    def test_subasta_programada_se_activa_sola(self):
        evt = f.evento(fecha_inicio=timezone.now() + timedelta(hours=1))
        s = f.subasta_activa(evt=evt, titulo="Futura")
        self.assertEqual(s.estado, "programada")
        Subasta.objects.filter(pk=s.pk).update(fecha_inicio=timezone.now() - timedelta(seconds=1))
        services.sincronizar_estados()
        s.refresh_from_db()
        self.assertEqual(s.estado, "activa")


class InsigniaTests(TestCase):  # PAIN-27 · RF-13
    def test_otorga_insignia_al_alcanzar_el_umbral_de_ventas(self):
        artista = f.usuario("artista")
        parametros.guardar("ventas_para_verificado", 2)
        comprador = f.usuario("comprador", con_pago=True)
        for n in range(2):
            s = f.subasta_activa(artista=artista, titulo=f"Obra {n}", base=100)
            services.registrar_puja(s.pk, comprador, 150)
            Subasta.objects.filter(pk=s.pk).update(fecha_fin=timezone.now() - timedelta(seconds=1))
            services.sincronizar_estados()
            artista.refresh_from_db()
            self.assertEqual(artista.insignia_verificado, n == 1)
        self.assertTrue(Notificacion.objects.filter(usuario=artista, titulo__contains="verificado").exists())

    def test_insignia_visible_en_el_perfil_del_artista(self):
        artista = f.usuario("artista", insignia_verificado=True, nombre="Elena")
        self.client.force_login(f.usuario("comprador"))
        self.assertContains(self.client.get(reverse("obras:perfil_artista", args=[artista.pk])), "Artista verificado")


class ConsultasTests(TestCase):  # PAIN-21 · RF-08 · RNF-03
    def setUp(self):
        self.subasta = f.subasta_activa(base=300)
        self.comprador = f.usuario("comprador", con_pago=True)
        self.client.force_login(self.comprador)

    def test_dashboard_lista_activas_con_puja_y_tiempo(self):
        services.registrar_puja(self.subasta.pk, self.comprador, 350)
        r = self.client.get(reverse("subastas:en_vivo"))
        self.assertContains(r, "Costa quieta")
        self.assertContains(r, "350")
        self.assertContains(r, 'data-poll="dashboard"')

    def test_api_devuelve_estado_en_json(self):
        services.registrar_puja(self.subasta.pk, self.comprador, 350)
        datos = json.loads(self.client.get(reverse("subastas:api_dashboard")).content)
        self.assertEqual(datos["subastas"][0]["precio"], 350.0)
        self.assertEqual(datos["subastas"][0]["pujas"], 1)
        uno = json.loads(self.client.get(reverse("subastas:api_estado", args=[self.subasta.pk])).content)
        self.assertGreater(uno["segundos"], 0)

    def test_mis_pujas_clasifica_ganando_superado_y_ganadas(self):
        otro = f.usuario("comprador", con_pago=True)
        services.registrar_puja(self.subasta.pk, self.comprador, 350)
        r = self.client.get(reverse("subastas:mis_pujas") + "?tab=ganando")
        self.assertContains(r, "Costa quieta")
        services.registrar_puja(self.subasta.pk, otro, 400)
        self.assertContains(self.client.get(reverse("subastas:mis_pujas") + "?tab=superado"), "Costa quieta")
        Subasta.objects.filter(pk=self.subasta.pk).update(fecha_fin=timezone.now() - timedelta(seconds=1))
        self.client.force_login(otro)
        self.assertContains(self.client.get(reverse("subastas:mis_pujas") + "?tab=ganadas"), "Costa quieta")

    def test_explorar_filtra_busca_y_oculta_restringidas(self):
        f.subasta_activa(titulo="Acuarela azul", tecnica="Acuarela sobre papel", base=100)
        r = self.client.get(reverse("subastas:explorar") + "?f=Acuarela")
        self.assertContains(r, "Acuarela azul")
        self.assertNotContains(r, "Costa quieta")
        self.assertContains(self.client.get(reverse("subastas:explorar") + "?q=quieta"), "Costa quieta")
        self.subasta.obra.restringida = True
        self.subasta.obra.save()
        self.assertNotContains(self.client.get(reverse("subastas:explorar")), "Costa quieta")

    def test_comprador_ve_formulario_y_curador_solo_lectura(self):
        url = reverse("subastas:detalle", args=[self.subasta.pk])
        self.assertContains(self.client.get(url), "Pujar ahora")
        self.client.force_login(f.usuario("curador"))
        r = self.client.get(url)
        self.assertNotContains(r, "Pujar ahora")
        self.assertContains(r, "Solo los compradores pueden pujar")