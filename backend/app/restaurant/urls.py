from django.urls import path
from .views import (
    CategoryListView,
    CategoryDetailView,
    DishVariantListView,
    DishVariantDetailView,
)

urlpatterns = [
    path('categories/', CategoryListView.as_view(), name='category-list'),
    # path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category-detail'),
    path('variants/', DishVariantListView.as_view(), name='variant-list'),
    path('variants/<int:pk>/', DishVariantDetailView.as_view(), name='variant-detail'),
]
