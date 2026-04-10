from django.db import models

# Create your models here.
class usuario(models.Model):
    rut = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=False)
    telefono = models.CharField(max_length=20)

    def __str__(self):
        return self.nombre