from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')

    class Meta:
        verbose_name = 'Категория блюд'
        verbose_name_plural = 'Категории блюд'

    def __str__(self):
        return self.name


class Dish(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='dishes',
        verbose_name='Категория'
    )
    image = models.ImageField(
        upload_to='dishes/',
        blank=True,
        null=True,
        verbose_name='Изображение'
    )
    is_deleted = models.BooleanField(default=False, verbose_name='Удалено (мягкое)')

    class Meta:
        verbose_name = 'Блюдо'
        verbose_name_plural = 'Блюда'

    def __str__(self):
        return self.name


class Size(models.Model):
    label = models.CharField(max_length=100, verbose_name='Лейбл')

    class Meta:
        verbose_name = 'Размер'
        verbose_name_plural = 'Размеры'

    def __str__(self):
        return self.label


class MeasureUnit(models.Model):
    label = models.CharField(max_length=100, verbose_name='Лейбл')
    short = models.CharField(max_length=20, verbose_name='Короткий вариант')

    class Meta:
        verbose_name = 'Мера измерения'
        verbose_name_plural = 'Меры измерения'

    def __str__(self):
        return f'{self.label} ({self.short})'


class DishVariant(models.Model):
    dish = models.ForeignKey(
        Dish,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name='Блюдо'
    )
    size = models.ForeignKey(
        Size,
        on_delete=models.PROTECT,
        related_name='variants',
        verbose_name='Размер'
    )
    size_value = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name='Значение размера'
    )
    measure_unit = models.ForeignKey(
        MeasureUnit,
        on_delete=models.PROTECT,
        related_name='variants',
        verbose_name='Мера измерения'
    )
    weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name='Вес (г)'
    )
    calories = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name='Калорийность (ккал)'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Цена (руб.)'
    )
    is_deleted = models.BooleanField(default=False, verbose_name='Удалено (мягкое)')

    class Meta:
        verbose_name = 'Вариант блюда'
        verbose_name_plural = 'Варианты блюд'

    def __str__(self):
        return f'{self.dish.name} — {self.size.label} ({self.size_value} {self.measure_unit.short})'
