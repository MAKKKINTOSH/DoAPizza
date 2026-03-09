from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiExample

from .models import Order
from .serializers import OrderSerializer, OrderCreateSerializer
from .filters import OrderFilter


class UserOrderListView(ListAPIView):
    """
    GET /api/orders/users/{user_id}/
    Список заказов конкретного пользователя с фильтрами по датам и статусу.
    Фильтры: started_at_from, started_at_to, status
    """
    serializer_class = OrderSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OrderFilter

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        return Order.objects.filter(
            user_id=user_id
        ).prefetch_related(
            'items__dish_variant__dish__category',
            'items__dish_variant__size',
            'items__dish_variant__measure_unit',
        ).select_related('user')


class UserOrderDetailView(RetrieveAPIView):
    """
    GET /api/orders/users/{user_id}/{pk}/
    Получение конкретного заказа пользователя по id.
    """
    serializer_class = OrderSerializer

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        return Order.objects.filter(
            user_id=user_id
        ).prefetch_related(
            'items__dish_variant__dish__category',
            'items__dish_variant__size',
            'items__dish_variant__measure_unit',
        ).select_related('user')


class OrderCreateView(APIView):
    """
    POST /api/orders/
    Создание заказа. Принимает номер телефона, имя и email для привязки/создания пользователя.
    """

    @extend_schema(
        request=OrderCreateSerializer,
        responses=OrderSerializer,
        examples=[
            OpenApiExample(
                'Пример запроса',
                value={
                    'phone_number': '+79991234567',
                    'name': 'Иван',
                    'email': 'ivan@example.com',
                    'address': 'ул. Пушкина, д. 1',
                    'comment': 'Позвонить за 10 минут',
                    'items': [
                        {'dish_variant_id': 1, 'quantity': 2},
                        {'dish_variant_id': 3, 'quantity': 1},
                    ],
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(
            OrderSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )
