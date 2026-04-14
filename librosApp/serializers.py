from rest_framework import serializers
from .models import Libro, Ejemplar

class LibroSerializer(serializers.ModelSerializer):

    cantidad_ejemplares = serializers.SerializerMethodField()
    cantidad = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Libro
        fields = '__all__'

    def get_cantidad_ejemplares(self, obj):
        return obj.ejemplar_set.count()

    def create(self, validated_data):
        cantidad = validated_data.pop('cantidad', 0)

        libro = Libro.objects.create(**validated_data)

        for i in range(cantidad):
            Ejemplar.objects.create(
                libro=libro,
                codigo=f"{libro.codigo_libro}-{i + 1}"
            )

        return libro

class EjemplarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ejemplar
        fields = '__all__'