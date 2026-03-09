import django_filters
from .models import Order


class OrderFilter(django_filters.FilterSet):
    started_at_from = django_filters.DateTimeFilter(field_name='started_at', lookup_expr='gte')
    started_at_to = django_filters.DateTimeFilter(field_name='started_at', lookup_expr='lte')
    status = django_filters.ChoiceFilter(choices=Order.Status.choices)

    class Meta:
        model = Order
        fields = ['started_at_from', 'started_at_to', 'status']
