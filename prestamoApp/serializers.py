from rest_framework import serializers
from .models import prestamo
from datetime import date

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
        libro = data['libro']
        ejemplar = data['ejemplar']

        if prestamo.objects.filter(ejemplar=ejemplar, estado__in=['P','A']).exists():
            raise serializers.ValidationError("Este ejemplar no se puede prestar porque ya está prestado o atrasado")

        # Validar que la fecha de devolución sea mayor
        if data['fecha_devolucion'] < data['fecha_prestamo']:
            raise serializers.ValidationError("La fecha de devolución no puede ser menor a la de préstamo")
        return data
    
    def create(self, validated_data):
        prestamo_obj = super().create(validated_data)

        ejemplar = prestamo_obj.ejemplar
        ejemplar.estado = 'prestado'
        ejemplar.save()

        return prestamo_obj

