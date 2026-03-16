from django.urls import path
from . import views

app_name = 'community'

urlpatterns = [
    # The Main Hub (Global Activity Feed)
    path('', views.community_hub, name='hub'),
    
    # Specific Channel/Space Feed
    path('space/<slug:slug>/', views.space_detail, name='space_detail'),
    
    # Create a new post in a space
    path('space/<slug:slug>/new/', views.create_post, name='create_post'),
]