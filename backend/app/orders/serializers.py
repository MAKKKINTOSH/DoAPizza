from decimal import Decimal
from rest_framework import serializers
from django.db.models import Sum
from restaurant.serializers import DishVariantSerializer
from administration.models import User, DeliveryAddress
from .models import Order, OrderItem, BonusTransaction


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
            'bonus_discount',
            'items',
        ]


class BonusTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BonusTransaction
        fields = ['id', 'order', 'amount', 'transaction_type', 'created_at']


class UserBonusSerializer(serializers.Serializer):
    balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    transactions = BonusTransactionSerializer(many=True)


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
    bonus_points = serializers.IntegerField(required=False, min_value=0, default=0)
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
        bonus_points = validated_data.get('bonus_points', 0)
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

        # Проверяем и списываем бонусы
        bonus_discount = Decimal('0.00')
        if bonus_points > 0:
            balance = (
                BonusTransaction.objects.filter(user=user)
                .aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            )
            bonus_discount = min(Decimal(str(bonus_points)), balance)
            if bonus_discount < 0:
                bonus_discount = Decimal('0.00')

        # Создаём заказ
        order = Order.objects.create(
            user=user,
            address=address,
            comment=comment,
            bonus_discount=bonus_discount,
        )

        # Создаём элементы заказа
        for item_data in items_data:
            try:
                variant = DishVariant.objects.get(pk=item_data['dish_variant_id'], is_deleted=False)
            except DishVariant.DoesNotExist:
                order.delete()
                raise serializers.ValidationError(
                    {'items': [f"Вариант блюда с id={item_data['dish_variant_id']} не найден."]}
                )
            OrderItem.objects.create(
                order=order,
                dish_variant=variant,
                quantity=item_data['quantity'],
            )

        # Фиксируем списание бонусов
        if bonus_discount > 0:
            BonusTransaction.objects.create(
                user=user,
                order=order,
                amount=-bonus_discount,
                transaction_type=BonusTransaction.Type.REDEEMED,
            )

        return order
