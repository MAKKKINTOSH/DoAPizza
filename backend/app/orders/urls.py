from django.urls import path
from .views import UserOrderListView, UserOrderDetailView, OrderCreateView

urlpatterns = [
    path('create', OrderCreateView.as_view(), name='order-create'),
    path('users/<int:user_id>/', UserOrderListView.as_view(), name='user-order-list'),
    path('users/<int:user_id>/<int:pk>/', UserOrderDetailView.as_view(), name='user-order-detail'),
]
