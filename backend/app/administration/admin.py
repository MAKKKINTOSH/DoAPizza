from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, DeliveryAddress, AuthCode


class DeliveryAddressInline(admin.TabularInline):
    model = DeliveryAddress
    extra = 0
    readonly_fields = ['created_at']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['phone_number', 'name', 'email', 'is_active', 'is_staff', 'date_joined']
    list_filter = ['is_active', 'is_staff']
    search_fields = ['phone_number', 'name', 'email']
    ordering = ['-date_joined']
    inlines = [DeliveryAddressInline]

    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Личные данные', {'fields': ('name', 'email')}),
        ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'name', 'email', 'password1', 'password2'),
        }),
    )
    readonly_fields = ['date_joined', 'last_login']


@admin.register(DeliveryAddress)
class DeliveryAddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'address', 'created_at']
    search_fields = ['user__phone_number', 'address']
    list_filter = ['created_at']
    readonly_fields = ['created_at']


@admin.register(AuthCode)
class AuthCodeAdmin(admin.ModelAdmin):
    list_display = ['phone_number', 'code', 'created_at', 'is_used']
    list_filter = ['is_used']
    search_fields = ['phone_number']
    readonly_fields = ['created_at']
