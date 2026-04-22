from django.contrib import admin

# Register your models here.
from .models import Ejemplar, Libro


@admin.register(Libro)
class LibroAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'autor', 'editorial', 'fecha_registro', 'codigo_libro', 'encargado_agrego')
    list_filter = ('editorial', 'fecha_registro')
    search_fields = ('titulo', 'autor', 'codigo_libro')
    ordering = ('-fecha_registro', 'titulo')


@admin.register(Ejemplar)
class EjemplarAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'libro', 'estado', 'fecha_llegada')
    list_filter = ('estado', 'fecha_llegada')
    search_fields = ('codigo', 'libro__titulo', 'libro__autor')
    ordering = ('-fecha_llegada',)