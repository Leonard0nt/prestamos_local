from datetime import date, timedelta
import json
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.core.wsgi import get_wsgi_application
from django.test import TestCase, override_settings

from librosApp.models import Ejemplar, Libro
from prestamoApp.models import prestamo
from usuarioApp.models import EncargadoBiblioteca, usuario

from .bridge import HOST, DjangoBridge


@override_settings(ALLOWED_HOSTS=[HOST])
class DesktopWorkflowsTests(TestCase):
    password = "PruebasQt-2026"

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_superuser("admin-qt", password=cls.password)
        cls.librarian = User.objects.create_user("encargado-qt", password=cls.password)
        EncargadoBiblioteca.objects.create(
            user=cls.librarian, nombre="Encargado de prueba", rut="101",
            correo="encargado@example.test", nivel="BASICA",
        )
        cls.book = Libro.objects.create(
            titulo="L'école de prueba", autor="Autor", editorial="Editorial",
            fecha_registro=date.today(), codigo_libro="BAS", nivel_asignado="BASICA",
        )
        cls.other_book = Libro.objects.create(
            titulo="Libro Media", autor="Autor", editorial="Editorial",
            fecha_registro=date.today(), codigo_libro="MED", nivel_asignado="MEDIA",
        )
        cls.copy = Ejemplar.objects.create(libro=cls.book, codigo="BAS-1")
        cls.other_copy = Ejemplar.objects.create(libro=cls.other_book, codigo="MED-1")
        cls.reader = usuario.objects.create(
            nombre="Estudiante", rut="102", email="estudiante@example.test",
            curso="1°A", telefono="12", nivel_asignado="BASICA",
        )

    def setUp(self):
        self.bridge = DjangoBridge(get_wsgi_application())

    def request(self, path, method="GET", data=None, *, form=False, csrf=True, query=""):
        headers = {}
        if csrf and "csrftoken" in self.bridge.cookies:
            headers["X-CSRFToken"] = self.bridge.cookies["csrftoken"].value
        body = b""
        if data is not None:
            headers["Content-Type"] = (
                "application/x-www-form-urlencoded" if form else "application/json"
            )
            body = (urlencode(data) if form else json.dumps(data)).encode()
        return self.bridge.dispatch(path, query=query, method=method, body=body, headers=headers)

    def login(self, user=None):
        response = self.request("/login/")
        self.assertEqual(response.status, 200)
        return self.request(
            "/login/", "POST", {"username": (user or self.admin).username, "password": self.password},
            form=True,
        )

    def test_login_plantillas_y_logout(self):
        self.assertEqual(self.request("/").status, 302)
        self.request("/login/")
        failed = self.request(
            "/login/", "POST", {"username": self.admin.username, "password": "incorrecta"}, form=True,
        )
        self.assertEqual(failed.status, 200)
        self.assertNotIn("sessionid", self.bridge.cookies)
        self.assertEqual(self.login().headers["location"], "/encargados-ui/")
        self.assertIn("sessionid", self.bridge.cookies)
        self.assertNotIn("sessionid", self.bridge.visible_cookies())
        for path in ("/", "/libros-ui/", "/usuarios-ui/", "/encargados-ui/"):
            with self.subTest(path=path):
                response = self.request(path)
                self.assertEqual(response.status, 200)
                self.assertIn(b"/_desktop/assets/bootstrap.min.css", response.body)
        self.assertEqual(self.request("/logout/").headers["location"], "/login/")
        self.assertNotIn("sessionid", self.bridge.cookies)

    def test_csrf_y_acceso_anonimo(self):
        self.request("/login/")
        self.assertEqual(self.request("/libros/").status, 403)
        self.assertEqual(self.request("/libros/", "POST", {}).status, 403)
        self.login()
        self.assertEqual(self.request("/libros/", "POST", {}, csrf=False).status, 403)

    def test_configuracion_exige_password_actual(self):
        self.login()
        fields = {"username": "admin-renombrado", "email": "admin@example.test"}
        rejected = self.request(
            "/mi-cuenta/actualizar/", "POST", dict(fields, current_password="incorrecta"), form=True,
        )
        self.assertEqual(rejected.status, 400)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.username, "admin-qt")
        accepted = self.request(
            "/mi-cuenta/actualizar/", "POST",
            dict(fields, current_password=self.password, password="NuevaClaveQt-2026"), form=True,
        )
        self.assertEqual(accepted.status, 200)
        self.assertEqual(self.request("/").status, 200)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("NuevaClaveQt-2026"))

    def test_encargado_edita_ejemplares_del_nivel_asignado(self):
        self.assertEqual(self.login(self.librarian).headers["location"], "/")
        result = self.request("/libros/")
        self.assertEqual([row["id"] for row in json.loads(result.body)], [self.book.pk])
        self.assertEqual(self.request("/encargados/").status, 403)
        self.assertEqual(
            self.request(f"/ejemplares/{self.other_copy.pk}/", "PATCH", {"estado": "danado"}).status,
            404,
        )
        self.assertEqual(
            self.request(f"/ejemplares/{self.copy.pk}/", "PATCH", {"estado": "danado"}).status,
            200,
        )

    def test_enlace_directo_de_ejemplares_usa_catalogo_y_respeta_nivel(self):
        self.login(self.librarian)
        response = self.request(f"/libros/{self.book.pk}/ejemplares/")
        self.assertEqual(response.status, 200)
        self.assertIn(f"libroInicial = Number('{self.book.pk}')".encode(), response.body)
        self.assertEqual(self.request(f"/libros/{self.other_book.pk}/ejemplares/").status, 404)

    def test_libros_y_ejemplares_crud(self):
        self.login()
        payload = {
            "titulo": "Otro libro", "autor": "Autor", "editorial": "Editorial",
            "fecha_registro": str(date.today()), "codigo_libro": "OTRO",
            "nivel_asignado": "BASICA", "cantidad": 1,
        }
        created = self.request("/libros/", "POST", payload)
        self.assertEqual(created.status, 201)
        book = json.loads(created.body)
        book_url = f"/libros/{book['id']}/"
        self.assertEqual(self.request(book_url, "PATCH", {"editorial": "Nueva"}).status, 200)
        copies = json.loads(self.request(book_url + "ejemplares_json/").body)
        copy_url = f"/ejemplares/{copies[0]['id']}/"
        self.assertEqual(self.request(book_url, "DELETE").status, 400)
        self.assertEqual(
            self.request(book_url + "actualizar_estado_ejemplares/", "POST", {"estado": "extraviado"}).status,
            200,
        )
        self.assertEqual(self.request(copy_url, "DELETE").status, 200)
        self.assertEqual(self.request(copy_url + "eliminar_definitivo/", "DELETE").status, 200)
        self.assertEqual(self.request(book_url, "DELETE").status, 204)

    def test_alumnos_edicion_baja_reactivacion_y_eliminacion(self):
        self.login()
        created = self.request("/usuarios/", "POST", {
            "rut": "103", "nombre": "Estudiante nuevo", "curso": "1°A",
            "email": "otro@example.test", "telefono": "123",
        })
        self.assertEqual(created.status, 201)
        pk = json.loads(created.body)["id"]
        path = f"/usuarios/{pk}/"
        self.assertEqual(self.request(path, "PATCH", {"nombre": "Otro nombre"}).status, 200)
        self.assertEqual(self.request(path, "DELETE").status, 200)
        inactive = json.loads(self.request("/usuarios/", query="vista=baja").body)
        self.assertIn(pk, [row["id"] for row in inactive])
        self.assertEqual(self.request(path + "reactivar/", "POST").status, 200)
        self.assertEqual(self.request(path, "DELETE").status, 200)
        self.assertEqual(self.request(path, "DELETE").status, 200)
        self.assertFalse(usuario.objects.filter(pk=pk).exists())

    def test_encargados_creacion_edicion_restablecimiento_y_eliminacion(self):
        self.login()
        data = {"rut": "12345678-5", "nombre": "Nuevo", "correo": "nuevo@example.test", "nivel": "MEDIA"}
        response = self.request("/encargados/", "POST", data)
        self.assertEqual(response.status, 201)
        pk = json.loads(response.body)["id"]
        path = f"/encargados/{pk}/"
        self.assertEqual(
            self.request(path, "PATCH", dict(data, nombre="Editado")).status, 200,
        )
        response = self.request(path + "restablecer_password/", "POST")
        self.assertEqual(response.status, 200)
        self.assertTrue(json.loads(response.body)["password_temporal"])
        self.assertEqual(self.request(path, "DELETE").status, 204)
        self.assertFalse(EncargadoBiblioteca.objects.filter(pk=pk).exists())

    def test_prestamo_tardio_se_devuelve_archiva_y_puede_prestarse_de_nuevo(self):
        self.login()
        initial = date.today() - timedelta(days=5)
        due = date.today() - timedelta(days=2)
        data = {
            "ejemplar": self.copy.pk, "usuario": self.reader.pk, "nivel_asignado": "BASICA",
            "fecha_prestamo": str(initial), "fecha_devolucion": str(due),
        }
        response = self.request("/prestamos/", "POST", data)
        self.assertEqual(response.status, 201)
        pk = json.loads(response.body)["id"]
        self.assertEqual(self.request("/prestamos/", "POST", data).status, 400)
        loan = next(p for p in json.loads(self.request("/prestamos/").body) if p["id"] == pk)
        self.assertEqual(loan["estado"], "A")
        self.assertEqual(self.request(f"/ejemplares/{self.copy.pk}/", "DELETE").status, 400)
        returned = self.request(f"/prestamos/{pk}/devolver/", "POST")
        self.assertEqual(returned.status, 200)
        self.assertEqual(json.loads(returned.body)["estado"], "D")
        self.assertEqual(json.loads(returned.body)["dias_atraso"], 2)
        self.assertEqual(self.request(f"/prestamos/{pk}/devolver/", "POST").status, 400)
        self.assertEqual(self.request(f"/prestamos/{pk}/", "DELETE").status, 200)
        archived = json.loads(self.request("/prestamos/historial/").body)
        self.assertIn(pk, [row["id"] for row in archived])
        self.assertEqual(self.request("/prestamos/", "POST", data).status, 201)

    def test_encargado_no_puede_prestar_ejemplar_de_otro_nivel(self):
        self.login(self.librarian)
        response = self.request("/prestamos/", "POST", {
            "ejemplar": self.other_copy.pk, "usuario": self.reader.pk,
            "fecha_prestamo": str(date.today()), "fecha_devolucion": str(date.today()),
        })
        self.assertEqual(response.status, 400)
        self.assertFalse(prestamo.objects.exists())


    def test_prestamo_rechaza_fecha_invertida_y_alumno_de_baja(self):
        self.login()
        today = date.today()
        data = {
            "ejemplar": self.copy.pk, "usuario": self.reader.pk, "nivel_asignado": "BASICA",
            "fecha_prestamo": str(today), "fecha_devolucion": str(today - timedelta(days=1)),
        }
        self.assertEqual(self.request("/prestamos/", "POST", data).status, 400)
        usuario.objects.filter(pk=self.reader.pk).update(activo=False)
        self.assertEqual(
            self.request("/prestamos/", "POST", dict(data, fecha_devolucion=str(today))).status,
            400,
        )
        self.copy.refresh_from_db()
        self.assertEqual(self.copy.estado, Ejemplar.ESTADO_DISPONIBLE)
        self.assertFalse(prestamo.objects.exists())
