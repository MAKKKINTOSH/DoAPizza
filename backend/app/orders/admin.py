from django.contrib import admin
from .models import Courier, Order, OrderItem


@admin.register(Courier)
class CourierAdmin(admin.ModelAdmin):
    list_display = ['last_name', 'first_name', 'patronymic', 'phone_number', 'is_deleted']
    list_filter = ['is_deleted']
    search_fields = ['last_name', 'first_name', 'patronymic', 'phone_number']

    def has_delete_permission(self, request, obj=None):
        return False


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ['dish_variant', 'quantity']
    autocomplete_fields = ['dish_variant']
    show_change_link = True


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'status', 'is_pickup_display',
        'started_at', 'finished_at', 'courier',
    ]
    list_filter = ['status', 'started_at']
    search_fields = ['user__phone_number', 'address', 'comment']
    readonly_fields = ['started_at', 'is_pickup_display']
    inlines = [OrderItemInline]

    fieldsets = (
        ('Основное', {
            'fields': ('user', 'status', 'courier')
        }),
        ('Адрес', {
            'fields': ('address', 'is_pickup_display')
        }),
        ('Время', {
            'fields': ('started_at', 'finished_at')
        }),
        ('Дополнительно', {
            'fields': ('comment',)
        }),
    )

    def is_pickup_display(self, obj):
        return obj.is_pickup

    is_pickup_display.boolean = True
    is_pickup_display.short_description = 'Самовывоз'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'dish_variant', 'quantity']
    search_fields = ['order__id', 'dish_variant__dish__name']
    autocomplete_fields = ['order', 'dish_variant']
