from decimal import Decimal

from django.test import TestCase

from apps.core.models import Usuario
from apps.operacional.dtos import ServicoCreateDTO, ServicoUpdateDTO
from apps.operacional.services import ServicoService
from apps.tenants.models import Barbearia


class MultiTenantTestCase(TestCase):
    """Testes para garantir que um DONO não acessa dados de outra barbearia."""

    def setUp(self):
        # Barbearia A
        self.dono_a = Usuario.objects.create_user(
            username="dono_a", email="a@test.com", password="senha", cpf="11111111111", tipo_usuario="DONO"
        )
        self.barbearia_a = Barbearia.objects.create(
            nome_comercial="Barbearia A", cnpj="11111111000111", cep="00000000",
            logradouro="Rua A", numero="1", bairro="Bairro A", cidade="Cidade A", estado="SP",
            email="a@barbearia.com", created_by=self.dono_a
        )

        # Barbearia B
        self.dono_b = Usuario.objects.create_user(
            username="dono_b", email="b@test.com", password="senha", cpf="22222222222", tipo_usuario="DONO"
        )
        self.barbearia_b = Barbearia.objects.create(
            nome_comercial="Barbearia B", cnpj="22222222000122", cep="00000000",
            logradouro="Rua B", numero="1", bairro="Bairro B", cidade="Cidade B", estado="SP",
            email="b@barbearia.com", created_by=self.dono_b
        )

        # Serviço criado na Barbearia A
        result_criacao = ServicoService().criar_servico(
            ServicoCreateDTO(nome="Corte A", preco=Decimal("50.00"), duracao_minutos=30),
            self.barbearia_a.id
        )
        self.servico_a = result_criacao.data
        self.service = ServicoService()

    def test_nao_pode_atualizar_servico_de_outra_barbearia(self):
        """Tentar atualizar um serviço usando o ID de outra barbearia deve falhar."""
        
        # CORREÇÃO: Removido o argumento 'user_id' que causava o TypeError
        result = self.service.atualizar_servico(
            servico_id=self.servico_a.id,
            dto=ServicoUpdateDTO(nome="Corte A Modificado"),
            barbearia_id=self.barbearia_b.id,  # Tentando usar o ID da Barbearia B (deve falhar)
        )

        # O teste verifica se a aplicação bloqueou a tentativa
        self.assertFalse(result.success)
        self.assertIn("não encontrado", result.error.lower())