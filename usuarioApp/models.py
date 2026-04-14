from django.db import models
from django.contrib.auth.models import User


# Create your models here.
class usuario(models.Model):
    rut = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=False)
    telefono = models.CharField(max_length=20)
    activo = models.BooleanField(default=True)
    
    def __str__(self):
        return self.nombre


class EncargadoBiblioteca(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='encargado', null=True, blank=True)
    nombre = models.CharField(max_length=100)
    rut = models.CharField(max_length=20, unique=True)
    correo = models.EmailField(unique=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en']

    def __str__(self):
        return f"{self.nombre} ({self.rut})"