from rest_framework import serializers
from librosApp.models import Ejemplar
from .models import prestamo


class PrestamoSerializer(serializers.ModelSerializer):
    libro_detalle = serializers.CharField(source='ejemplar.libro.titulo', read_only=True)
    ejemplar_detalle = serializers.StringRelatedField(source='ejemplar', read_only=True)
    usuario_detalle = serializers.StringRelatedField(source='usuario', read_only=True)
    nivel_pertenencia = serializers.SerializerMethodField()

    class Meta:
        model = prestamo
        fields = '__all__'
        read_only_fields = ['estado', 'dias_atraso', 'activo']

    def get_nivel_pertenencia(self, obj):
        if obj.nivel_asignado == prestamo.NIVEL_MEDIA:
            return 'Media'
        if obj.nivel_asignado == prestamo.NIVEL_BASICA:
            return 'Basica'

        encargado = getattr(obj, 'encargado_agrego', None)
        if encargado:
            return encargado.get_nivel_display()

        usuario_encargado = getattr(obj.usuario, 'encargado_agrego', None)
        if usuario_encargado:
            return usuario_encargado.get_nivel_display()

        libro_encargado = getattr(obj.ejemplar.libro, 'encargado_agrego', None)
        return libro_encargado.get_nivel_display() if libro_encargado else ''

    def validate(self, data):
        request = self.context.get('request')
        if (
            request
            and request.user.is_superuser
            and self.instance is None
            and not data.get('nivel_asignado')
        ):
            raise serializers.ValidationError(
                {'nivel_asignado': 'Debes seleccionar un nivel (Basica o Media).'}
            )

        # Validar que el libro no esté prestado
        ejemplar = data.get('ejemplar', getattr(self.instance, 'ejemplar', None))

        usuario_obj = data.get('usuario', getattr(self.instance, 'usuario', None))

        if usuario_obj and not usuario_obj.activo:
            raise serializers.ValidationError(
                'No se pueden registrar préstamos a usuarios desactivados.'
            )

        if ejemplar and ejemplar.estado != Ejemplar.ESTADO_DISPONIBLE:
            raise serializers.ValidationError(
                'Este ejemplar no está disponible para préstamo.'
            )
        if ejemplar:
            prestamos_activos = prestamo.objects.filter(ejemplar=ejemplar, estado__in=['P', 'A'])
            if self.instance:
                prestamos_activos = prestamos_activos.exclude(pk=self.instance.pk)

            if prestamos_activos.exists():
                raise serializers.ValidationError(
                    "Este ejemplar no se puede prestar porque ya está prestado o atrasado"
                )

        fecha_prestamo = data.get('fecha_prestamo', getattr(self.instance, 'fecha_prestamo', None))
        fecha_devolucion = data.get('fecha_devolucion', getattr(self.instance, 'fecha_devolucion', None))

        if fecha_prestamo and fecha_devolucion and fecha_devolucion < fecha_prestamo:
            raise serializers.ValidationError(
                "La fecha de devolución no puede ser menor a la de préstamo"
            )
        return data
    
    def create(self, validated_data):
        prestamo_obj = super().create(validated_data)

        ejemplar = prestamo_obj.ejemplar
        ejemplar.estado = Ejemplar.ESTADO_PRESTADO
        ejemplar.save(update_fields=['estado'])

        return prestamo_obj

