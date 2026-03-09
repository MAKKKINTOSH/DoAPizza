import django_filters
from .models import DishVariant


class DishVariantFilter(django_filters.FilterSet):
    category = django_filters.NumberFilter(field_name='dish__category__id')
    calories_min = django_filters.NumberFilter(field_name='calories', lookup_expr='gte')
    calories_max = django_filters.NumberFilter(field_name='calories', lookup_expr='lte')
    price_min = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = django_filters.NumberFilter(field_name='price', lookup_expr='lte')

    class Meta:
        model = DishVariant
        fields = ['category', 'calories_min', 'calories_max', 'price_min', 'price_max']
