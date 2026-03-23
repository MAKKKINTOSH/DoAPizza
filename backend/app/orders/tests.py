from django.test import TestCase
from rest_framework.test import APIClient

from administration.models import User, DeliveryAddress
from restaurant.models import Category, Dish, DishVariant, MeasureUnit, Size
from .models import Order


def create_variant(price='399.00', calories='650.00'):
    category, _ = Category.objects.get_or_create(name='Пицца')
    dish, _ = Dish.objects.get_or_create(name='Маргарита', defaults={'category': category})
    size, _ = Size.objects.get_or_create(label='Маленький')
    unit, _ = MeasureUnit.objects.get_or_create(label='Сантиметры', short='см')
    return DishVariant.objects.create(
        dish=dish, size=size, size_value='25', measure_unit=unit,
        weight='380', calories=calories, price=price,
    )


class OrderCreateTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/orders/create'
        self.variant = create_variant()

    def _payload(self, **overrides):
        data = {
            'phone_number': '+79001234567',
            'address': 'ул. Пушкина, д. 1',
            'items': [{'dish_variant_id': self.variant.pk, 'quantity': 2}],
        }
        data.update(overrides)
        return data

    def test_create_order_returns_201(self):
        response = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(response.status_code, 201)

    def test_response_contains_order_fields(self):
        response = self.client.post(self.url, self._payload(), format='json')
        for field in ('id', 'user', 'address', 'status', 'status_display', 'is_pickup', 'items'):
            self.assertIn(field, response.data)

    def test_initial_status_is_processing(self):
        response = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(response.data['status'], 'processing')

    def test_auto_creates_user(self):
        self.assertFalse(User.objects.filter(phone_number='+79001234567').exists())
        self.client.post(self.url, self._payload(), format='json')
        self.assertTrue(User.objects.filter(phone_number='+79001234567').exists())

    def test_reuses_existing_user(self):
        User.objects.create(phone_number='+79001234567')
        self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(User.objects.filter(phone_number='+79001234567').count(), 1)

    def test_fills_empty_name_on_existing_user(self):
        user = User.objects.create(phone_number='+79001234567', name='')
        self.client.post(self.url, self._payload(name='Иван'), format='json')
        user.refresh_from_db()
        self.assertEqual(user.name, 'Иван')

    def test_does_not_overwrite_existing_name(self):
        user = User.objects.create(phone_number='+79001234567', name='Старое имя')
        self.client.post(self.url, self._payload(name='Новое имя'), format='json')
        user.refresh_from_db()
        self.assertEqual(user.name, 'Старое имя')

    def test_address_saved_to_user_history(self):
        self.client.post(self.url, self._payload(), format='json')
        user = User.objects.get(phone_number='+79001234567')
        self.assertTrue(DeliveryAddress.objects.filter(user=user, address='ул. Пушкина, д. 1').exists())

    def test_address_not_duplicated(self):
        self.client.post(self.url, self._payload(), format='json')
        self.client.post(self.url, self._payload(), format='json')
        user = User.objects.get(phone_number='+79001234567')
        self.assertEqual(DeliveryAddress.objects.filter(user=user, address='ул. Пушкина, д. 1').count(), 1)

    def test_pickup_order_no_address(self):
        response = self.client.post(self.url, self._payload(address=''), format='json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['is_pickup'])
        self.assertEqual(response.data['address'], '')

    def test_delivery_order_is_not_pickup(self):
        response = self.client.post(self.url, self._payload(), format='json')
        self.assertFalse(response.data['is_pickup'])

    def test_missing_phone_returns_400(self):
        payload = self._payload()
        del payload['phone_number']
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, 400)

    def test_empty_items_returns_400(self):
        response = self.client.post(self.url, self._payload(items=[]), format='json')
        self.assertEqual(response.status_code, 400)

    def test_nonexistent_variant_returns_400(self):
        response = self.client.post(
            self.url,
            self._payload(items=[{'dish_variant_id': 99999, 'quantity': 1}]),
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_quantity_less_than_1_returns_400(self):
        response = self.client.post(
            self.url,
            self._payload(items=[{'dish_variant_id': self.variant.pk, 'quantity': 0}]),
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_order_items_in_response(self):
        response = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(len(response.data['items']), 1)
        self.assertEqual(response.data['items'][0]['quantity'], 2)


class UserOrderListTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(phone_number='+79001234567')
        self.variant = create_variant()
        # Create two orders
        order1 = Order.objects.create(user=self.user, address='ул. 1')
        order2 = Order.objects.create(user=self.user, address='ул. 2', status=Order.Status.DELIVERED)
        from .models import OrderItem
        OrderItem.objects.create(order=order1, dish_variant=self.variant, quantity=1)
        OrderItem.objects.create(order=order2, dish_variant=self.variant, quantity=1)

    def test_returns_all_user_orders(self):
        response = self.client.get(f'/api/orders/users/{self.user.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_filter_by_status(self):
        response = self.client.get(f'/api/orders/users/{self.user.pk}/?status=delivered')
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['status'], 'delivered')

    def test_other_user_orders_not_visible(self):
        other = User.objects.create(phone_number='+79009999999')
        response = self.client.get(f'/api/orders/users/{other.pk}/')
        self.assertEqual(len(response.data), 0)


class UserOrderDetailTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(phone_number='+79001234567')
        self.variant = create_variant()
        self.order = Order.objects.create(user=self.user, address='ул. Пушкина, д. 1')
        from .models import OrderItem
        OrderItem.objects.create(order=self.order, dish_variant=self.variant, quantity=3)

    def test_returns_order_detail(self):
        response = self.client.get(f'/api/orders/users/{self.user.pk}/{self.order.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], self.order.pk)

    def test_wrong_user_returns_404(self):
        other = User.objects.create(phone_number='+79009999999')
        response = self.client.get(f'/api/orders/users/{other.pk}/{self.order.pk}/')
        self.assertEqual(response.status_code, 404)

    def test_nonexistent_order_returns_404(self):
        response = self.client.get(f'/api/orders/users/{self.user.pk}/99999/')
        self.assertEqual(response.status_code, 404)
