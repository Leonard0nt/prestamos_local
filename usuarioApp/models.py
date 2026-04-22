from django.db import models
from django.contrib.auth.models import User


# Create your models here.
class usuario(models.Model):
    NIVEL_BASICA = 'BASICA'
    NIVEL_MEDIA = 'MEDIA'
    NIVELES = [
        (NIVEL_BASICA, 'Basica'),
        (NIVEL_MEDIA, 'Media'),
    ]

    rut = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    curso = models.CharField(max_length=100, blank=True, default='')
    email = models.EmailField(unique=False)
    telefono = models.CharField(max_length=20)
    activo = models.BooleanField(default=True)
    nivel_asignado = models.CharField(max_length=10, choices=NIVELES, null=True, blank=True)
    encargado_agrego = models.ForeignKey(
        'EncargadoBiblioteca',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios_agregados',
    )

    def __str__(self):
        return self.nombre


class EncargadoBiblioteca(models.Model):
    NIVEL_BASICA = 'BASICA'
    NIVEL_MEDIA = 'MEDIA'
    NIVELES = [
        (NIVEL_BASICA, 'Basica'),
        (NIVEL_MEDIA, 'Media'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='encargado', null=True, blank=True)
    nombre = models.CharField(max_length=100)
    rut = models.CharField(max_length=20, unique=True)
    correo = models.EmailField(unique=True)
    nivel = models.CharField(max_length=10, choices=NIVELES, default=NIVEL_BASICA)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en']

    def __str__(self):
        return f"{self.nombre} ({self.rut})"