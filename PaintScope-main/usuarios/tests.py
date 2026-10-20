from django.test import TestCase
from django.urls import reverse

from config import testutils as f
from .models import MetodoPago, Usuario


class RegistroTests(TestCase):  # PAIN-14 · RF-01 · CU-01
    def datos(self, **extra):
        d = {"first_name": "Ana", "email": "ana@test.cr", "rol": "artista",
             "password1": f.CLAVE, "password2": f.CLAVE}
        d.update(extra)
        return d

    def test_registro_crea_cuenta_y_deja_autenticado(self):
        r = self.client.post(reverse("registro"), self.datos())
        self.assertRedirects(r, reverse("obras:portafolio"))
        self.assertEqual(Usuario.objects.get(email="ana@test.cr").rol, "artista")
        self.assertIn("_auth_user_id", self.client.session)

    def test_correo_duplicado_muestra_error(self):
        f.usuario("comprador", email="ana@test.cr")
        r = self.client.post(reverse("registro"), self.datos())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "ya está registrado")
        self.assertEqual(Usuario.objects.filter(email__iexact="ana@test.cr").count(), 1)

    def test_no_se_puede_auto_registrar_como_admin_ni_curador(self):
        for rol in ("admin", "curador"):
            r = self.client.post(reverse("registro"), self.datos(email=f"{rol}@test.cr", rol=rol))
            self.assertEqual(r.status_code, 200)
            self.assertFalse(Usuario.objects.filter(email=f"{rol}@test.cr").exists())


class LoginTests(TestCase):  # PAIN-15 · RF-02 · CU-02
    def test_redirige_al_panel_segun_rol(self):
        destinos = {"artista": "obras:portafolio", "curador": "obras:postulaciones",
                    "comprador": "subastas:explorar", "admin": "panel:inicio"}
        for rol, destino in destinos.items():
            u = f.usuario(rol, email=f"{rol}@test.cr")
            r = self.client.post(reverse("login"), {"username": u.email, "password": f.CLAVE})
            self.assertRedirects(r, reverse(destino), fetch_redirect_response=False)
            self.client.post(reverse("logout"))

    def test_credenciales_incorrectas_muestran_error(self):
        u = f.usuario("comprador")
        r = self.client.post(reverse("login"), {"username": u.email, "password": "mala"})
        self.assertContains(r, "incorrectos")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_cuenta_suspendida_no_entra_y_se_le_explica(self):
        u = f.usuario("comprador")
        u.is_active = False
        u.save()
        r = self.client.post(reverse("login"), {"username": u.email, "password": f.CLAVE})
        self.assertContains(r, "suspendida")

    def test_rutas_exigen_sesion_y_rol(self):
        self.assertEqual(self.client.get(reverse("perfil")).status_code, 302)
        self.client.force_login(f.usuario("comprador"))
        self.assertEqual(self.client.get(reverse("panel:inicio")).status_code, 403)
        self.assertEqual(self.client.get(reverse("obras:postulaciones")).status_code, 403)
        self.assertEqual(self.client.get(reverse("obras:portafolio")).status_code, 403)


class PerfilTests(TestCase):  # PAIN-16 · RF-03
    def setUp(self):
        self.u = f.usuario("artista", telefono="8888-0000")
        self.client.force_login(self.u)

    def test_muestra_telefono_actual(self):
        self.assertContains(self.client.get(reverse("perfil")), "8888-0000")

    def test_edita_y_guarda(self):
        r = self.client.post(reverse("perfil"), {"perfil-first_name": "Nueva", "perfil-email": "nueva@test.cr",
                                                 "perfil-telefono": "7000-1111"})
        self.assertRedirects(r, reverse("perfil"))
        self.u.refresh_from_db()
        self.assertEqual((self.u.first_name, self.u.email, self.u.telefono), ("Nueva", "nueva@test.cr", "7000-1111"))

    def test_no_permite_usar_correo_de_otra_cuenta(self):
        otro = f.usuario("comprador", email="otro@test.cr")
        r = self.client.post(reverse("perfil"), {"perfil-first_name": "X", "perfil-email": otro.email, "perfil-telefono": ""})
        self.assertContains(r, "otra cuenta")

    def test_cambia_contrasena_sin_cerrar_sesion(self):
        nueva = "Otra-clave-456"
        r = self.client.post(reverse("cambiar_password"), {"old_password": f.CLAVE, "new_password1": nueva, "new_password2": nueva})
        self.assertRedirects(r, reverse("perfil"))
        self.u.refresh_from_db()
        self.assertTrue(self.u.check_password(nueva))
        self.assertEqual(self.client.get(reverse("perfil")).status_code, 200)

    def test_rechaza_contrasena_actual_incorrecta(self):
        r = self.client.post(reverse("cambiar_password"), {"old_password": "no", "new_password1": "Otra-clave-456", "new_password2": "Otra-clave-456"})
        self.assertEqual(r.status_code, 200)
        self.u.refresh_from_db()
        self.assertTrue(self.u.check_password(f.CLAVE))


class MetodoPagoTests(TestCase):  # PAIN-24 · RF-16
    def setUp(self):
        self.u = f.usuario("comprador")
        self.client.force_login(self.u)

    def test_guarda_solo_ultimos_4_digitos(self):
        r = self.client.post(reverse("agregar_metodo_pago"), {"tipo": "credito", "titular": "Ana", "numero": "4242 4242 4242 4242", "vencimiento": "12/39"})
        self.assertRedirects(r, reverse("perfil"))
        m = MetodoPago.objects.get(usuario=self.u)
        self.assertEqual(m.ultimos4, "4242")
        self.assertNotIn("4242424242424242", str(m.__dict__))
        self.assertTrue(self.u.tiene_metodo_pago)

    def test_rechaza_numero_invalido_y_tarjeta_vencida(self):
        r = self.client.post(reverse("agregar_metodo_pago"), {"tipo": "credito", "titular": "A", "numero": "1234 5678 9012 3456", "vencimiento": "12/39"})
        self.assertContains(r, "no es válido")
        r = self.client.post(reverse("agregar_metodo_pago"), {"tipo": "credito", "titular": "A", "numero": "4242424242424242", "vencimiento": "01/20"})
        self.assertContains(r, "vencida")
        self.assertFalse(MetodoPago.objects.exists())


class AdminDjangoTests(TestCase):
    def test_pantallas_del_admin_de_django_cargan_sin_username(self):
        root = Usuario.objects.create_superuser(email="root@test.cr", password=f.CLAVE, first_name="Root")
        self.client.force_login(root)
        self.assertEqual(self.client.get("/admin/usuarios/usuario/").status_code, 200)
        self.assertEqual(self.client.get("/admin/usuarios/usuario/add/").status_code, 200)
        self.assertEqual(self.client.get(f"/admin/usuarios/usuario/{root.pk}/change/").status_code, 200)
        self.assertEqual(root.rol, "admin")
