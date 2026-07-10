# config/urls.py
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Autenticação JWT (login e refresh token) - URLs explícitas
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Domínio core
    path('api/v1/core/', include('apps.core.urls')),
    
    # Domínio tenants
    path('api/v1/tenants/', include('apps.tenants.urls')),

    # Domínio operacional
    path('api/v1/operacional/', include('apps.operacional.urls')),
    
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