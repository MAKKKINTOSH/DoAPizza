from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema

from .models import Category, DishVariant
from .serializers import CategorySerializer, DishVariantSerializer, VariantCompactSerializer, DishListSerializer
from .filters import DishVariantFilter


class CategoryListView(ListAPIView):
    """
    GET /api/restaurant/categories/
    Список всех категорий блюд.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class CategoryDetailView(RetrieveAPIView):
    """
    GET /api/restaurant/categories/{id}/
    Получение категории по id.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class DishVariantListView(ListAPIView):
    """
    GET /api/restaurant/variants/
    Список блюд с вложенными вариантами. Фильтры применяются по вариантам.
    Фильтры: category, calories_min, calories_max, price_min, price_max
    """
    serializer_class = DishVariantSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = DishVariantFilter

    def get_queryset(self):
        return DishVariant.objects.filter(
            is_deleted=False,
            dish__is_deleted=False,
        ).select_related('dish', 'dish__category', 'size', 'measure_unit')

    @extend_schema(responses=DishListSerializer(many=True))
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        dishes = {}
        for variant in queryset:
            dish = variant.dish
            if dish.id not in dishes:
                image_url = request.build_absolute_uri(dish.image.url) if dish.image else None
                dishes[dish.id] = {
                    'id': dish.id,
                    'dish_name': dish.name,
                    'dish_image': image_url,
                    'dish_description': dish.description,
                    'category': CategorySerializer(dish.category).data,
                    'variants': [],
                }
            dishes[dish.id]['variants'].append(VariantCompactSerializer(variant).data)

        return Response(list(dishes.values()))


class DishVariantDetailView(RetrieveAPIView):
    """
    GET /api/restaurant/variants/{id}/
    Получение варианта блюда по id.
    """
    serializer_class = DishVariantSerializer

    def get_queryset(self):
        return DishVariant.objects.filter(
            is_deleted=False,
            dish__is_deleted=False,
        ).select_related('dish', 'dish__category', 'size', 'measure_unit')
