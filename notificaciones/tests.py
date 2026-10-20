from django.test import TestCase
from django.urls import reverse

from config import testutils as f
from .models import Notificacion
from .servicio import notificar


class NotificacionesTests(TestCase):  # PAIN-28 · RF-14
    def setUp(self):
        self.u = f.usuario("comprador")
        self.client.force_login(self.u)

    def test_pantalla_lista_solo_las_propias(self):
        notificar(self.u, "sistema", "Para mí", "mensaje mío")
        notificar(f.usuario("artista"), "sistema", "Para otro", "mensaje ajeno")
        r = self.client.get(reverse("notificaciones:lista"))
        self.assertContains(r, "Para mí")
        self.assertNotContains(r, "Para otro")

    def test_contador_de_sin_leer_y_marcar_todas(self):
        notificar(self.u, "sistema", "Uno", "a"); notificar(self.u, "sistema", "Dos", "b")
        self.assertEqual(self.client.get(reverse("subastas:explorar")).context["sin_leer"], 2)
        self.client.post(reverse("notificaciones:marcar_todas"))
        self.assertEqual(self.client.get(reverse("subastas:explorar")).context["sin_leer"], 0)

    def test_abrir_marca_leida_y_redirige(self):
        n = notificar(self.u, "sistema", "Ir", "x", "/subastas/en-vivo/")
        r = self.client.get(reverse("notificaciones:abrir", args=[n.pk]))
        self.assertRedirects(r, "/subastas/en-vivo/", fetch_redirect_response=False)
        n.refresh_from_db()
        self.assertTrue(n.leida)

    def test_no_se_puede_abrir_la_de_otro(self):
        ajena = notificar(f.usuario("artista"), "sistema", "x", "y")
        self.assertEqual(self.client.get(reverse("notificaciones:abrir", args=[ajena.pk])).status_code, 404)
