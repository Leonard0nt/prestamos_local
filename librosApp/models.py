from django.db import models
from django.utils import timezone

# Create your models here.
class Libro(models.Model):
    titulo = models.CharField(max_length=100)
    autor = models.CharField(max_length=100)
    editorial = models.CharField(max_length=100)
    fecha_registro = models.DateField()
    codigo_libro = models.CharField(max_length=20, unique=True, blank=True)

    def __str__(self):
        return self.titulo


class Ejemplar(models.Model):
    libro = models.ForeignKey(Libro, on_delete=models.CASCADE)
    codigo = models.CharField(max_length=50)
    fecha_llegada = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=20, default='disponible')

    def __str__(self):
        return f"{self.libro.titulo} - {self.codigo}"

