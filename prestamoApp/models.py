from django.db import models
from datetime import date, timedelta

# Create your models here.
def fecha_devolucion_default():
    return date.today() + timedelta(days=7)

class prestamo(models.Model):
    ejemplar = models.ForeignKey('librosApp.Ejemplar', on_delete=models.PROTECT)
    usuario = models.ForeignKey('usuarioApp.usuario', on_delete=models.PROTECT)
    fecha_prestamo = models.DateField(default=date.today)
    fecha_devolucion = models.DateField(default=fecha_devolucion_default)
    dias_atraso = models.IntegerField(default=0)
    estado = models.CharField(max_length=1, choices=[
        ('P', 'Prestado'),
        ('D', 'Disponible'),
        ('A', 'Atrasado')
    ],    default='P')
    activo = models.BooleanField(default=True) 

def __str__(self):
    return f"{self.ejemplar.codigo} - {self.fecha_prestamo}"