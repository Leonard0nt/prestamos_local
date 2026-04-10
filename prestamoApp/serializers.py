from rest_framework import serializers
from .models import prestamo


class PrestamoSerializer(serializers.ModelSerializer):
    libro_detalle = serializers.CharField(source='ejemplar.libro.titulo', read_only=True)
    ejemplar_detalle = serializers.StringRelatedField(source='ejemplar', read_only=True)
    usuario_detalle = serializers.StringRelatedField(source='usuario', read_only=True)

    class Meta:
        model = prestamo
        fields = '__all__'
        read_only_fields = ['estado', 'dias_atraso', 'activo']

    def validate(self, data):
        # Validar que el libro no esté prestado
        ejemplar = data.get('ejemplar', getattr(self.instance, 'ejemplar', None))

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
        ejemplar.estado = 'prestado'
        ejemplar.save()

        return prestamo_obj

