from django.db import models
from django.conf import settings
from restaurant.models import DishVariant


class Courier(models.Model):
    first_name = models.CharField(max_length=100, verbose_name='Имя')
    last_name = models.CharField(max_length=100, verbose_name='Фамилия')
    patronymic = models.CharField(max_length=100, blank=True, verbose_name='Отчество')
    phone_number = models.CharField(max_length=20, verbose_name='Номер телефона')
    is_deleted = models.BooleanField(default=False, verbose_name='Удалено (мягкое)')

    class Meta:
        verbose_name = 'Курьер'
        verbose_name_plural = 'Курьеры'

    def __str__(self):
        parts = [self.last_name, self.first_name]
        if self.patronymic:
            parts.append(self.patronymic)
        return ' '.join(parts)


class Order(models.Model):
    class Status(models.TextChoices):
        PROCESSING = 'processing', 'В обработке'
        PREPARING = 'preparing', 'Готовится'
        COURIER_ON_WAY = 'courier_on_way', 'Курьер в пути'
        DELIVERED = 'delivered', 'Доставлен'
        CANCELLED = 'cancelled', 'Отменён'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name='Пользователь'
    )
    address = models.TextField(blank=True, verbose_name='Адрес доставки')
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='Начало')
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name='Завершение')
    comment = models.TextField(blank=True, verbose_name='Комментарий')
    courier = models.ForeignKey(
        Courier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Курьер'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROCESSING,
        verbose_name='Статус'
    )

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-started_at']

    def __str__(self):
        return f'Заказ #{self.pk} — {self.user.phone_number} ({self.get_status_display()})'

    @property
    def is_pickup(self):
        """Самовывоз"""
        return not bool(self.address)


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Заказ'
    )
    dish_variant = models.ForeignKey(
        DishVariant,
        on_delete=models.PROTECT,
        related_name='order_items',
        verbose_name='Вариант блюда'
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name='Количество')

    class Meta:
        verbose_name = 'Элемент заказа'
        verbose_name_plural = 'Элементы заказа'

    def __str__(self):
        return f'{self.dish_variant} × {self.quantity}'
