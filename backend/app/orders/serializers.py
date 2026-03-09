from rest_framework import serializers
from restaurant.serializers import DishVariantSerializer
from administration.models import User, DeliveryAddress
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    dish_variant = DishVariantSerializer(read_only=True)
    dish_variant_id = serializers.PrimaryKeyRelatedField(
        source='dish_variant',
        queryset=__import__('restaurant.models', fromlist=['DishVariant']).DishVariant.objects.filter(is_deleted=False),
        write_only=True
    )

    class Meta:
        model = OrderItem
        fields = ['id', 'dish_variant', 'dish_variant_id', 'quantity']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_pickup = serializers.BooleanField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'user',
            'address',
            'started_at',
            'finished_at',
            'comment',
            'status',
            'status_display',
            'is_pickup',
            'items',
        ]


class OrderItemCreateSerializer(serializers.Serializer):
    dish_variant_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):
    # Данные пользователя
    phone_number = serializers.CharField(max_length=20)
    name = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    email = serializers.EmailField(required=False, allow_blank=True, default='')

    # Данные заказа
    address = serializers.CharField(required=False, allow_blank=True, default='')
    comment = serializers.CharField(required=False, allow_blank=True, default='')
    items = OrderItemCreateSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('Заказ должен содержать хотя бы один элемент.')
        return value

    def create(self, validated_data):
        from restaurant.models import DishVariant

        phone_number = validated_data['phone_number']
        name = validated_data.get('name', '')
        email = validated_data.get('email', '')
        address = validated_data.get('address', '')
        comment = validated_data.get('comment', '')
        items_data = validated_data['items']

        # Получаем или создаём пользователя
        user, created = User.objects.get_or_create(
            phone_number=phone_number,
            defaults={'name': name, 'email': email},
        )
        if not created:
            # Обновляем имя/email если они пустые
            updated = False
            if name and not user.name:
                user.name = name
                updated = True
            if email and not user.email:
                user.email = email
                updated = True
            if updated:
                user.save(update_fields=['name', 'email'])

        # Сохраняем адрес если он новый
        if address:
            DeliveryAddress.objects.get_or_create(user=user, address=address)

        # Создаём заказ
        order = Order.objects.create(
            user=user,
            address=address,
            comment=comment,
        )

        # Создаём элементы заказа
        for item_data in items_data:
            variant = DishVariant.objects.get(pk=item_data['dish_variant_id'])
            OrderItem.objects.create(
                order=order,
                dish_variant=variant,
                quantity=item_data['quantity'],
            )

        return order
