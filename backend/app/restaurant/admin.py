from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from .models import Category, Dish, Size, MeasureUnit, DishVariant


class DishInline(admin.TabularInline):
    model = Dish
    extra = 0
    fields = ['name', 'is_deleted']
    show_change_link = True
    can_delete = False


class DishVariantInline(admin.TabularInline):
    model = DishVariant
    extra = 0
    fields = ['size', 'size_value', 'measure_unit', 'weight', 'calories', 'price', 'is_deleted']
    show_change_link = True
    can_delete = False


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'dish_links']
    search_fields = ['name']
    inlines = [DishInline]

    def dish_links(self, obj):
        dishes = obj.dishes.filter(is_deleted=False)
        if not dishes.exists():
            return '—'
        links = format_html_join(
            ', ',
            '<a href="{}">{}</a>',
            (
                (reverse('admin:restaurant_dish_change', args=[d.pk]), d.name)
                for d in dishes
            )
        )
        return links

    dish_links.short_description = 'Блюда категории'
    dish_links.allow_tags = True


@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_deleted']
    list_filter = ['category', 'is_deleted']
    search_fields = ['name', 'description']
    inlines = [DishVariantInline]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ['label']
    search_fields = ['label']


@admin.register(MeasureUnit)
class MeasureUnitAdmin(admin.ModelAdmin):
    list_display = ['label', 'short']
    search_fields = ['label', 'short']


@admin.register(DishVariant)
class DishVariantAdmin(admin.ModelAdmin):
    list_display = ['dish', 'size', 'size_value', 'measure_unit', 'weight', 'calories', 'price', 'is_deleted']
    list_filter = ['dish__category', 'size', 'is_deleted']
    search_fields = ['dish__name']
    autocomplete_fields = ['dish']

    def has_delete_permission(self, request, obj=None):
        return False
