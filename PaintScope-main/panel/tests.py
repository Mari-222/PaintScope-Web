from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from config import testutils as f
from subastas.models import Subasta
from usuarios.models import Usuario
from . import parametros


class PanelBase(TestCase):
    def setUp(self):
        self.admin = f.usuario("admin")
        self.client.force_login(self.admin)


class UsuariosPanelTests(PanelBase):  # PAIN-29 · RF-15 · CU-08
    def test_solo_el_admin_entra(self):
        for rol in ("artista", "curador", "comprador"):
            self.client.force_login(f.usuario(rol))
            for nombre in ("panel:inicio", "panel:usuarios", "panel:roles", "panel:parametros", "panel:moderacion"):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 403, (rol, nombre))

    def test_crea_usuario_con_rol(self):
        r = self.client.post(reverse("panel:usuario_nuevo"), {"first_name": "Cura", "email": "cura@test.cr", "telefono": "", "rol": "curador", "password": "Una-clave-789"})
        self.assertRedirects(r, reverse("panel:usuarios"))
        u = Usuario.objects.get(email="cura@test.cr")
        self.assertEqual(u.rol, "curador")
        self.assertTrue(u.check_password("Una-clave-789"))

    def test_edita_usuario_sin_cambiar_contrasena(self):
        u = f.usuario("comprador")
        self.client.post(reverse("panel:usuario_editar", args=[u.pk]), {"first_name": "Cambiado", "email": u.email, "telefono": "1", "rol": "comprador", "password": ""})
        u.refresh_from_db()
        self.assertEqual(u.first_name, "Cambiado")
        self.assertTrue(u.check_password(f.CLAVE))

    def test_suspende_y_reactiva(self):
        u = f.usuario("comprador")
        self.client.post(reverse("panel:usuario_suspender", args=[u.pk]))
        u.refresh_from_db(); self.assertFalse(u.is_active)
        self.client.post(reverse("panel:usuario_suspender", args=[u.pk]))
        u.refresh_from_db(); self.assertTrue(u.is_active)

    def test_suspender_con_actividad_pide_confirmacion_adicional(self):
        artista = f.usuario("artista")
        f.subasta_activa(artista=artista)
        r = self.client.post(reverse("panel:usuario_suspender", args=[artista.pk]))
        self.assertContains(r, "actividad en curso")
        artista.refresh_from_db(); self.assertTrue(artista.is_active)
        self.client.post(reverse("panel:usuario_suspender", args=[artista.pk]), {"confirmar": "1"})
        artista.refresh_from_db(); self.assertFalse(artista.is_active)

    def test_eliminar_con_actividad_exige_confirmar(self):
        artista = f.usuario("artista")
        f.subasta_activa(artista=artista)
        self.client.post(reverse("panel:usuario_eliminar", args=[artista.pk]))
        self.assertTrue(Usuario.objects.filter(pk=artista.pk).exists())
        self.client.post(reverse("panel:usuario_eliminar", args=[artista.pk]), {"confirmar": "1"})
        self.assertFalse(Usuario.objects.filter(pk=artista.pk).exists())

    def test_eliminar_sin_actividad_funciona_directo(self):
        u = f.usuario("comprador")
        self.client.post(reverse("panel:usuario_eliminar", args=[u.pk]))
        self.assertFalse(Usuario.objects.filter(pk=u.pk).exists())

    def test_admin_no_puede_suspenderse_ni_quitarse_el_rol(self):
        self.client.post(reverse("panel:usuario_suspender", args=[self.admin.pk]))
        self.client.post(reverse("panel:usuario_cambiar_rol", args=[self.admin.pk]), {"rol": "comprador"})
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
        self.assertEqual(self.admin.rol, "admin")

    def test_cambia_rol_y_lista_filtra(self):
        u = f.usuario("comprador", nombre="Zoe")
        self.client.post(reverse("panel:usuario_cambiar_rol", args=[u.pk]), {"rol": "curador"})
        u.refresh_from_db(); self.assertEqual(u.rol, "curador")
        r = self.client.get(reverse("panel:usuarios") + "?rol=curador&q=zoe")
        self.assertContains(r, "Zoe")

    def test_matriz_de_roles_carga(self):
        self.assertContains(self.client.get(reverse("panel:roles")), "Pujar en subastas")


class ParametrosTests(PanelBase):
    def datos(self, **extra):
        d = {d.clave: str(v) for d, v in parametros.todos() if d.tipo == "int"}
        d.update(extra)
        return d

    def test_valores_por_defecto(self):
        self.assertEqual(parametros.obtener("horas_extension"), 6)
        self.assertFalse(parametros.obtener("modo_mantenimiento"))

    def test_guarda_parametros_globales(self):
        r = self.client.post(reverse("panel:parametros"), self.datos(horas_extension="3", modo_mantenimiento=""))
        self.assertRedirects(r, reverse("panel:parametros"))
        self.assertEqual(parametros.obtener("horas_extension"), 3)

    def test_valida_rango_de_horas_de_visita(self):
        r = self.client.post(reverse("panel:parametros"), self.datos(visitas_hora_inicio="18", visitas_hora_fin="9"))
        self.assertContains(r, "Debe ser mayor")

    def test_modo_mantenimiento_bloquea_a_no_admins(self):
        parametros.guardar("modo_mantenimiento", True)
        self.assertEqual(self.client.get(reverse("panel:inicio")).status_code, 200)
        self.client.force_login(f.usuario("comprador"))
        self.assertEqual(self.client.get(reverse("subastas:explorar")).status_code, 503)


class ModeracionTests(PanelBase):
    def test_retirar_obra_la_oculta_del_catalogo(self):
        s = f.subasta_activa()
        self.client.post(reverse("panel:obra_restringir", args=[s.obra.pk]))
        s.obra.refresh_from_db(); self.assertTrue(s.obra.restringida)
        self.client.force_login(f.usuario("comprador"))
        self.assertNotContains(self.client.get(reverse("subastas:explorar")), "Costa quieta")
        self.client.force_login(self.admin)
        self.client.post(reverse("panel:obra_restringir", args=[s.obra.pk]))
        s.obra.refresh_from_db(); self.assertFalse(s.obra.restringida)

    def test_suspender_y_reanudar_pujas(self):
        s = f.subasta_activa()
        self.client.post(reverse("panel:subasta_suspender_pujas", args=[s.pk]))
        s.refresh_from_db(); self.assertTrue(s.pujas_suspendidas)
        self.assertContains(self.client.get(reverse("panel:moderacion") + "?f=Pujas+suspendidas"), "Costa quieta")
        self.client.post(reverse("panel:subasta_suspender_pujas", args=[s.pk]))
        s.refresh_from_db(); self.assertFalse(s.pujas_suspendidas)
