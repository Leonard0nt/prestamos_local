from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Ejemplar, Libro


class AgregarEjemplaresTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser("pruebas"))
        self.book = Libro.objects.create(
            titulo="El libro de prueba", autor="Autor", editorial="Editorial",
            fecha_registro=date.today(), codigo_libro="DEMO-LIBRO", nivel_asignado="BASICA",
        )
        self.url = f"/libros/{self.book.pk}/agregar_ejemplar/"

    def test_agrega_ejemplares_con_codigos_antiguos_sin_numero(self):
        Ejemplar.objects.create(libro=self.book, codigo="DEMO-EJEMPLAR")

        response = self.client.post(self.url, {"cantidad": 2}, content_type="application/json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            [item["codigo"] for item in response.json()], ["DEMO-LIBRO-1", "DEMO-LIBRO-2"],
        )
        self.assertTrue(Ejemplar.objects.filter(libro=self.book, codigo="DEMO-EJEMPLAR").exists())

    def test_continua_desde_el_mayor_sufijo_numerico(self):
        for code in ("DEMO-LIBRO-9", "DEMO-LIBRO-2", "CODIGO-LEGADO"):
            Ejemplar.objects.create(libro=self.book, codigo=code)

        response = self.client.post(self.url, {"cantidad": 1}, content_type="application/json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()[0]["codigo"], "DEMO-LIBRO-10")

    def test_rechaza_cantidad_invalida(self):
        for quantity in ("abc", 0, 1.5):
            with self.subTest(quantity=quantity):
                response = self.client.post(
                    self.url, {"cantidad": quantity}, content_type="application/json",
                )
                self.assertEqual(response.status_code, 400)
        self.assertFalse(Ejemplar.objects.exists())
