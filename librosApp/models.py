from django.db import models

# Create your models here.
class Libro(models.Model):
    NIVEL_BASICA = 'BASICA'
    NIVEL_MEDIA = 'MEDIA'
    NIVELES = [
        (NIVEL_BASICA, 'Basica'),
        (NIVEL_MEDIA, 'Media'),
    ]

    titulo = models.CharField(max_length=100)
    autor = models.CharField(max_length=100)
    editorial = models.CharField(max_length=100)
    fecha_registro = models.DateField()
    codigo_libro = models.CharField(max_length=20, unique=True, blank=True)
    nivel_asignado = models.CharField(max_length=10, choices=NIVELES, null=True, blank=True)

    encargado_agrego = models.ForeignKey(
        'usuarioApp.EncargadoBiblioteca',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='libros_agregados',
    )

    def __str__(self):
        return self.titulo


class Ejemplar(models.Model):
    ESTADO_DISPONIBLE = 'disponible'
    ESTADO_PRESTADO = 'prestado'
    ESTADO_BAJA = 'baja'
    ESTADO_EXTRAVIADO = 'extraviado'
    ESTADO_DANIADO = 'danado'

    ESTADOS = [
        (ESTADO_DISPONIBLE, 'Disponible'),
        (ESTADO_PRESTADO, 'Prestado'),
        (ESTADO_BAJA, 'Baja'),
        (ESTADO_EXTRAVIADO, 'Extraviado'),
        (ESTADO_DANIADO, 'Dañado'),
    ]

    libro = models.ForeignKey(Libro, on_delete=models.PROTECT)
    codigo = models.CharField(max_length=50)
    fecha_llegada = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default=ESTADO_DISPONIBLE)

    def __str__(self):
        return f"{self.libro.titulo} - {self.codigo}"

