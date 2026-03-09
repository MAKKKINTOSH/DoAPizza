from rest_framework import serializers
from .models import Category, Dish, Size, MeasureUnit, DishVariant


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class MeasureUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeasureUnit
        fields = ['id', 'label', 'short']


class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = ['id', 'label']


class DishVariantSerializer(serializers.ModelSerializer):
    category = CategorySerializer(source='dish.category', read_only=True)
    dish_name = serializers.CharField(source='dish.name', read_only=True)
    dish_image = serializers.ImageField(source='dish.image', read_only=True)
    dish_description = serializers.CharField(source='dish.description', read_only=True)
    size = SizeSerializer(read_only=True)
    measure_unit = MeasureUnitSerializer(read_only=True)

    class Meta:
        model = DishVariant
        fields = [
            'id',
            'dish',
            'dish_name',
            'dish_image',
            'dish_description',
            'category',
            'size',
            'size_value',
            'measure_unit',
            'weight',
            'calories',
            'price',
        ]


class VariantCompactSerializer(serializers.ModelSerializer):
    size = serializers.CharField(source='size.label')
    size_value = serializers.SerializerMethodField()

    def get_size_value(self, obj):
        short = obj.measure_unit.short if obj.measure_unit else ''
        return f'{obj.size_value} {short}'.strip()

    class Meta:
        model = DishVariant
        fields = ['id', 'size', 'size_value', 'weight', 'calories', 'price']


class DishListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    dish_name = serializers.CharField()
    dish_image = serializers.ImageField(allow_null=True)
    dish_description = serializers.CharField()
    category = CategorySerializer()
    variants = VariantCompactSerializer(many=True)
