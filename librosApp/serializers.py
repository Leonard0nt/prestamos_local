from rest_framework import serializers
from .models import Libro, Ejemplar

class LibroSerializer(serializers.ModelSerializer):

    cantidad_ejemplares = serializers.SerializerMethodField()
    cantidad_disponibles = serializers.SerializerMethodField()
    nivel_pertenencia = serializers.SerializerMethodField()
    cantidad = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Libro
        fields = '__all__'

    def get_cantidad_ejemplares(self, obj):
        return obj.ejemplar_set.count()

    def get_cantidad_disponibles(self, obj):
        return obj.ejemplar_set.filter(estado='disponible').count()

    def get_nivel_pertenencia(self, obj):
        if obj.nivel_asignado == Libro.NIVEL_MEDIA:
            return 'Media'
        if obj.nivel_asignado == Libro.NIVEL_BASICA:
            return 'Basica'

        encargado = getattr(obj, 'encargado_agrego', None)
        return encargado.get_nivel_display() if encargado else ''

    def validate(self, attrs):
        request = self.context.get('request')
        if (
            request
            and request.user.is_superuser
            and self.instance is None
            and not attrs.get('nivel_asignado')
        ):
            raise serializers.ValidationError(
                {'nivel_asignado': 'Debes seleccionar un nivel (Basica o Media).'}
            )
        return attrs


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