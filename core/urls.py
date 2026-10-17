from django.urls import path
from . import views
urlpatterns = [path('', views.home, name='home'), path('request-subscription/', views.request_subscription, name='request_subscription')]
