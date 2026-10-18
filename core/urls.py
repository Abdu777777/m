from django.urls import path
from django.contrib.auth import views as auth_views
from . import views, money_views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('account/', views.account_dashboard, name='account_dashboard'),
    path('account/kyc/', views.kyc_submit, name='kyc_submit'),
    path('account/money-requests/', money_views.money_requests, name='money_requests'),
    path('request-subscription/', views.request_subscription, name='request_subscription'),
]
