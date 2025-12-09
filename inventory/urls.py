from django.urls import path
from . import views

urlpatterns = [
    # List all items
    path('', views.inventory_list, name='inventory_list'),
    
    # Add new item
    path('add/', views.add_item, name='add_item'),
    
    # Delete item (CRITICAL ADDITION)
    # Uses uuid:pk because your model uses UUIDs for IDs
    path('delete/<uuid:pk>/', views.delete_item, name='delete_item'),
]