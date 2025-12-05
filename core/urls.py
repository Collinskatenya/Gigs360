from django.urls import path
from . import views

urlpatterns = [
    # The Homepage
    path('', views.home, name='home'),
]