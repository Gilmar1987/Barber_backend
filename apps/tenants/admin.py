# [Domínio: tenants] [Skill: admin]
"""
📖 MANIFESTO (LGPD Compliance):
"dados sensíveis mascarados em logs"
"dados sensíveis mascarados em respostas"

📖 MANIFESTO (Auditoria Obrigatória):
"Auditoria completa (created_at, updated_at, created_by)"
"Soft Delete em entidades críticas"

📖 MANIFESTO (Geolocalização):
"Usar GEOGRAPHY(Point, 4326) para cálculos em metros reais"

✅ Regras seguidas:
- CNPJ mascarado na listagem (LGPD)
- Widget OSM para edição de coordenadas geográficas
- Fieldsets organizados por contexto
- Filtros úteis (ativo, cidade, estado)
- Busca por nome, CNPJ, cidade
- Campos de auditoria readonly
- Soft delete visível no admin
"""
from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.utils.html import format_html

from apps.tenants.models import Barbearia


@admin.register(Barbearia)
class BarbeariaAdmin(GISModelAdmin):
    """
    Admin customizado para o modelo Barbearia.
    Herda de GISModelAdmin para suportar widgets de geolocalização.
    """
    
    # ═══════════════════════════════════════════════════════════
    # LISTAGEM
    # ═══════════════════════════════════════════════════════════
    list_display = (
        'nome_comercial_display',
        'cnpj_masked',
        'cidade_estado',
        'telefone',
        'ativo_display',
        'created_at',
    )
    
    list_filter = (
        'ativo',
        'is_deleted',
        'estado',
        'cidade',
        'created_at',
    )
    
    search_fields = (
        'nome_comercial',
        'cnpj',
        'cidade',
        'bairro',
        'cep',
    )
    
    ordering = ('-created_at',)
    
    readonly_fields = (
        'id',
        'created_at',
        'updated_at',
        'created_by',
        'updated_by',
        'deleted_at',
        'deleted_by',
        'is_deleted',
        'endereco_completo_display',
    )
    
    # ═══════════════════════════════════════════════════════════
    # FIELDSETS (Organização por contexto)
    # ═══════════════════════════════════════════════════════════
    fieldsets = (
        ('Identificação', {
            'fields': (
                'id',
                'nome_comercial',
                'cnpj',
            ),
            'description': 'Dados cadastrais da barbearia (tenant)',
        }),
        ('Endereço', {
            'fields': (
                'cep',
                'logradouro',
                'numero',
                'complemento',
                'bairro',
                'cidade',
                'estado',
                'endereco_completo_display',
            ),
            'description': 'Endereço completo do estabelecimento',
        }),
        ('Geolocalização (PostGIS GEOGRAPHY)', {
            'fields': ('localizacao',),
            'description': 'Coordenadas geográficas em GEOGRAPHY (cálculos em metros reais)',
        }),
        ('Contato', {
            'fields': (
                'telefone',
                'email',
            ),
            'classes': ('collapse',),
        }),
        ('Status', {
            'fields': ('ativo',),
        }),
        ('Auditoria (LGPD)', {
            'fields': (
                'created_at',
                'updated_at',
                'created_by',
                'updated_by',
            ),
            'classes': ('collapse',),
            'description': 'Trilha de auditoria automática',
        }),
        ('Soft Delete', {
            'fields': (
                'is_deleted',
                'deleted_at',
                'deleted_by',
            ),
            'classes': ('collapse',),
            'description': 'Exclusão lógica (dados preservados)',
        }),
    )
    
    # ═══════════════════════════════════════════════════════════
    # MÉTODOS CUSTOMIZADOS (LGPD + UX)
    # ═══════════════════════════════════════════════════════════
    
    @admin.display(description='Nome Comercial')
    def nome_comercial_display(self, obj: Barbearia) -> str:
        return obj.nome_comercial
    
    @admin.display(description='CNPJ')
    def cnpj_masked(self, obj: Barbearia) -> str:
        """
        Exibe CNPJ mascarado para LGPD.
        Formato: **.XXX.XXX/****-XX
        """
        if obj.cnpj and len(obj.cnpj) == 14:
            # Mostra apenas os 4 dígitos do meio
            return f"**.{obj.cnpj[2:5]}.{obj.cnpj[5:8]}/****-XX"
        return "***"
    
    @admin.display(description='Cidade/UF')
    def cidade_estado(self, obj: Barbearia) -> str:
        """Exibe cidade e estado formatados."""
        return f"{obj.cidade}/{obj.estado}"
    
    @admin.display(description='Status', boolean=True)
    def ativo_display(self, obj: Barbearia) -> bool:
        """Exibe status ativo com ícone visual."""
        return obj.ativo and not obj.is_deleted
    
    @admin.display(description='Endereço Completo')
    def endereco_completo_display(self, obj: Barbearia) -> str:
        """Exibe endereço completo formatado."""
        endereco = obj.get_endereco_completo()
        return format_html('<strong>{}</strong>', endereco)
    
    # ═══════════════════════════════════════════════════════════
    # CONFIGURAÇÃO DO GIS
    # ═══════════════════════════════════════════════════════════
    
    # Widget OpenStreetMap para edição de coordenadas
    gis_widget_kwargs = {
        'attrs': {
            'default_lon': -46.633309,  # São Paulo longitude
            'default_lat': -23.550520,  # São Paulo latitude
            'default_zoom': 12,
        },
    }
    
    # ═══════════════════════════════════════════════════════════
    # ACTIONS CUSTOMIZADAS
    # ═══════════════════════════════════════════════════════════
    
    @admin.action(description='Desativar barbearias selecionadas')
    def desativar_barbearias(self, request, queryset):
        count = 0
        for barbearia in queryset.filter(is_deleted=False):
            barbearia.ativo = False
            barbearia.updated_by = request.user
            barbearia.save(update_fields=['ativo', 'updated_by', 'updated_at'])
            count += 1
        self.message_user(request, f'{count} barbearia(s) desativada(s).')
    
    @admin.action(description='Ativar barbearias selecionadas')
    def ativar_barbearias(self, request, queryset):
        count = 0
        for barbearia in queryset.filter(is_deleted=False):
            barbearia.ativo = True
            barbearia.updated_by = request.user
            barbearia.save(update_fields=['ativo', 'updated_by', 'updated_at'])
            count += 1
        self.message_user(request, f'{count} barbearia(s) ativada(s).')
    
    @admin.action(description='Soft delete das barbearias selecionadas')
    def soft_delete_barbearias(self, request, queryset):
        """Realiza soft delete em múltiplas barbearias."""
        from django.utils import timezone
        count = 0
        for barbearia in queryset:
            barbearia.soft_delete(user_id=request.user.id)
            count += 1
        self.message_user(request, f'{count} barbearia(s) excluída(s) logicamente.')
    
    actions = [
        'desativar_barbearias',
        'ativar_barbearias',
        'soft_delete_barbearias',
    ]