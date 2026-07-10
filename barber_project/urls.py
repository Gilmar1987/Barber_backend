# config/urls.py
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Domínio core
    path('api/v1/core/', include('apps.core.urls')),
    
    # Domínio tenants
    path('api/v1/tenants/', include('apps.tenants.urls')),
    
    # Documentação da API (pública - permissão explícita AllowAny)
    path(
        'api/schema/',
        SpectacularAPIView.as_view(permission_classes=[AllowAny]),
        name='schema'
    ),
    path(
        'swagger/',
        SpectacularSwaggerView.as_view(
            url_name='schema',
            permission_classes=[AllowAny]
        ),
        name='swagger-ui'
    ),
    path(
        'redoc/',
        SpectacularRedocView.as_view(
            url_name='schema',
            permission_classes=[AllowAny]
        ),
        name='redoc'
    ),
]