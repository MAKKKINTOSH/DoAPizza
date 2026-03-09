from rest_framework import serializers
from .models import User, DeliveryAddress, AuthCode


class DeliveryAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAddress
        fields = ['id', 'address', 'created_at']


class UserSerializer(serializers.ModelSerializer):
    addresses = DeliveryAddressSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ['id', 'phone_number', 'name', 'email', 'date_joined', 'addresses']


class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['phone_number', 'name', 'email']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class RequestAuthCodeSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)


class VerifyAuthCodeSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=6)
