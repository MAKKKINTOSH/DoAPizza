from django.test import TestCase
from rest_framework.test import APIClient

from .models import Category, Dish, DishVariant, MeasureUnit, Size


def make_variant(dish, size_label='Маленький', size_value='25', price='399.00',
                 weight='380.00', calories='650.00', is_deleted=False):
    size, _ = Size.objects.get_or_create(label=size_label)
    unit, _ = MeasureUnit.objects.get_or_create(label='Сантиметры', short='см')
    return DishVariant.objects.create(
        dish=dish,
        size=size,
        size_value=size_value,
        measure_unit=unit,
        weight=weight,
        calories=calories,
        price=price,
        is_deleted=is_deleted,
    )


class CategoryListTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        Category.objects.create(name='Пицца')
        Category.objects.create(name='Напитки')

    def test_returns_all_categories(self):
        response = self.client.get('/api/restaurant/categories/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_category_has_id_and_name(self):
        response = self.client.get('/api/restaurant/categories/')
        names = [c['name'] for c in response.data]
        self.assertIn('Пицца', names)


class DishVariantListTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name='Пицца')
        self.dish = Dish.objects.create(name='Маргарита', category=self.category)
        make_variant(self.dish, price='399.00', calories='650.00')

    def test_returns_dishes_grouped(self):
        response = self.client.get('/api/restaurant/variants/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['dish_name'], 'Маргарита')
        self.assertIn('variants', response.data[0])

    def test_filter_by_category(self):
        cat2 = Category.objects.create(name='Напитки')
        dish2 = Dish.objects.create(name='Кола', category=cat2)
        make_variant(dish2, price='100.00', calories='150.00')

        response = self.client.get(f'/api/restaurant/variants/?category={self.category.pk}')
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['dish_name'], 'Маргарита')

    def test_filter_by_price_min(self):
        dish2 = Dish.objects.create(name='Дёшевое блюдо', category=self.category)
        make_variant(dish2, price='50.00', calories='100.00')

        response = self.client.get('/api/restaurant/variants/?price_min=200')
        names = [d['dish_name'] for d in response.data]
        self.assertIn('Маргарита', names)
        self.assertNotIn('Дёшевое блюдо', names)

    def test_filter_by_price_max(self):
        dish2 = Dish.objects.create(name='Дорогое блюдо', category=self.category)
        make_variant(dish2, price='1000.00', calories='900.00')

        response = self.client.get('/api/restaurant/variants/?price_max=500')
        names = [d['dish_name'] for d in response.data]
        self.assertIn('Маргарита', names)
        self.assertNotIn('Дорогое блюдо', names)

    def test_filter_by_calories_max(self):
        dish2 = Dish.objects.create(name='Калорийное блюдо', category=self.category)
        make_variant(dish2, price='400.00', calories='1500.00')

        response = self.client.get('/api/restaurant/variants/?calories_max=1000')
        names = [d['dish_name'] for d in response.data]
        self.assertIn('Маргарита', names)
        self.assertNotIn('Калорийное блюдо', names)

    def test_soft_deleted_dish_excluded(self):
        deleted_dish = Dish.objects.create(name='Удалённое', category=self.category, is_deleted=True)
        make_variant(deleted_dish)

        response = self.client.get('/api/restaurant/variants/')
        names = [d['dish_name'] for d in response.data]
        self.assertNotIn('Удалённое', names)

    def test_soft_deleted_variant_excluded(self):
        dish2 = Dish.objects.create(name='Блюдо с удалённым вариантом', category=self.category)
        make_variant(dish2, is_deleted=True)

        response = self.client.get('/api/restaurant/variants/')
        names = [d['dish_name'] for d in response.data]
        self.assertNotIn('Блюдо с удалённым вариантом', names)


class DishVariantDetailTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name='Пицца')
        self.dish = Dish.objects.create(name='Маргарита', category=self.category)
        self.variant = make_variant(self.dish)

    def test_returns_variant_detail(self):
        response = self.client.get(f'/api/restaurant/variants/{self.variant.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['dish_name'], 'Маргарита')
        self.assertIn('price', response.data)

    def test_nonexistent_variant_returns_404(self):
        response = self.client.get('/api/restaurant/variants/99999/')
        self.assertEqual(response.status_code, 404)

    def test_deleted_variant_returns_404(self):
        deleted_variant = make_variant(self.dish, size_label='Большой', is_deleted=True)
        response = self.client.get(f'/api/restaurant/variants/{deleted_variant.pk}/')
        self.assertEqual(response.status_code, 404)
