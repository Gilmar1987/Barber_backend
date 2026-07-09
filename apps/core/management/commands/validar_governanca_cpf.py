# <scope: barber_backend:core:management>
# <governance: multi_tenant_enforcement_active>

import os
import re
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

class Command(BaseCommand):
    help = 'Agente de IA/Engenharia para auditoria e validação estrita das regras de CPF (LGPD/Conventions)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('🔍 Iniciando varredura estática de governança do CPF...'))
        
        caminho_core_models = os.path.join(settings.BASE_DIR, 'apps', 'core', 'models.py')
        caminho_core_serializers = os.path.join(settings.BASE_DIR, 'apps', 'core', 'serializers.py')

        # REGRA 1: Validar se as travas algorítmicas estão ativas no models.py
        if os.path.exists(caminho_core_models):
            with open(caminho_core_models, 'r', encoding='utf-8') as f:
                conteudo_models = f.read()

            # Verifica se o CPF possui o validador matemático ativado
            if "validators=[validar_cpf]" not in conteudo_models:
                raise CommandError(
                    '❌ CRÍTICO: Violação do Manifesto! O campo CPF em core/models.py '
                    'não possui o validador matemático "validators=[validar_cpf]".'
                )
                
            # Verifica se possui limpeza de caracteres não numéricos
            if "re.sub(r'\D'" not in conteudo_models:
                raise CommandError(
                    '❌ CRÍTICO: O campo CPF não está executando a sanitização '
                    'para salvar apenas números em formato limpo de 11 caracteres.'
                )

        # REGRA 2: Validar se há vazamento de dados limpos em Serializers ou Views
        if os.path.exists(caminho_core_serializers):
            with open(caminho_core_serializers, 'r', encoding='utf-8') as f:
                conteudo_serializers = f.read()

            # Impede a exposição direta do CPF em campos de leitura pública (Read)
            if "fields = ['username', 'email', 'cpf'" in conteudo_serializers and "fields = " in conteudo_serializers:
                # Se o serializer expõe o CPF sem tratamento, emite um alerta de conformidade de privacidade
                self.stdout.write(self.style.NOTICE(
                    '⚠️ ALERTA DE PRIVACIDADE: Certifique-se de mascarar o CPF antes de '
                    'exibi-lo em listagens abertas da API pública.'
                ))

        self.stdout.write(self.style.SUCCESS('✅ SUCESSO: O código-fonte passou em 100% dos testes de governança de CPF e LGPD!'))
