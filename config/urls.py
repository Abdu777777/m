from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def health(request):
    return JsonResponse({'status': 'ok', 'service': 'Arab Option'})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health, name='health'),
    path('', include('core.urls')),
]
