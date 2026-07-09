

# [Domínio: core] [Skill: admin]
"""
✅ Regras seguidas:
- Admin customizado para Custom User Model
- List display com campos relevantes
- Filtros e busca configurados
- Fieldsets organizados
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.core.models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """Admin customizado para o modelo Usuario."""
    
    list_display = (
        'username',
        'email',
        'cpf',
        'tipo_usuario',
        'is_staff',
        'date_joined'
    )
    list_filter = ('tipo_usuario', 'is_staff', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'cpf')
    ordering = ('-date_joined',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Informações Adicionais', {
            'fields': ('cpf', 'tipo_usuario', 'telefone'),
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informações Adicionais', {
            'fields': ('cpf', 'tipo_usuario', 'telefone', 'email'),
        }),
    )