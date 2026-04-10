from django.contrib import admin
from django.urls import path

from rest_framework.routers import DefaultRouter
from usuarioApp.views import UsuarioViewSet
from librosApp.views import EjemplarViewSet, LibroViewSet
from prestamoApp.views import PrestamoViewSet

router = DefaultRouter()

router.register(r'usuarios', UsuarioViewSet)
router.register(r'libros', LibroViewSet)
router.register(r'prestamos', PrestamoViewSet)
router.register(r'ejemplares', EjemplarViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/', PrestamoViewSet.dashboard),

    # UI
    path('usuarios-ui/', UsuarioViewSet.usuarios_view, name='usuarios_ui'),
    path('libros-ui/', LibroViewSet.libros_view, name='libros_ui'),
    path('libros/<int:libro_id>/ejemplares/', LibroViewSet.ejemplares_view, name='libro_ejemplares'),
]

urlpatterns += router.urls