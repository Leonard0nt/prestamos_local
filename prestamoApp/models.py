
from datetime import date, timedelta
from django.db import models


# Create your models here.
def fecha_devolucion_default():
    return date.today() + timedelta(days=12)

class prestamo(models.Model):
    NIVEL_BASICA = 'BASICA'
    NIVEL_MEDIA = 'MEDIA'
    NIVELES = [
        (NIVEL_BASICA, 'Basica'),
        (NIVEL_MEDIA, 'Media'),
    ]

    ejemplar = models.ForeignKey('librosApp.Ejemplar', on_delete=models.PROTECT)
    usuario = models.ForeignKey('usuarioApp.usuario', on_delete=models.PROTECT)
    fecha_prestamo = models.DateField(default=date.today)
    fecha_devolucion = models.DateField(default=fecha_devolucion_default)
    dias_atraso = models.IntegerField(default=0)
    nivel_asignado = models.CharField(max_length=10, choices=NIVELES, null=True, blank=True)
    encargado_agrego = models.ForeignKey(
        'usuarioApp.EncargadoBiblioteca',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prestamos_agregados',
    )
    estado = models.CharField(
        max_length=1,
        choices=[
            ('P', 'Prestado'),
            ('D', 'Devuelto'),
            ('A', 'Atrasado'),
        ],
        default='P',
    )
    activo = models.BooleanField(default=True) 

    def __str__(self):
        return f"{self.ejemplar.codigo} - {self.fecha_prestamo}"