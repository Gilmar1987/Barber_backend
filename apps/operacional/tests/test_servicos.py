from decimal import Decimal

from django.test import TestCase

from apps.core.models import Usuario
from apps.operacional.dtos import ServicoCreateDTO
from apps.operacional.models import Profissional, Servico, ServicoProfissional
from apps.operacional.services import ServicoService
from apps.tenants.models import Barbearia


class ServicoHabilitacaoTestCase(TestCase):
    """Testes para criação atômica de serviços com habilitação de profissionais."""

    def setUp(self):
        self.dono = Usuario.objects.create_user(
            username="dono_serv", email="dono@serv.com", password="senha", cpf="55555555555", tipo_usuario="DONO"
        )
        self.barbearia = Barbearia.objects.create(
            nome_comercial="Barbearia Serv", cnpj="55555555000155", cep="00000000",
            logradouro="Rua Serv", numero="1", bairro="Bairro", cidade="Cidade", estado="SP",
            email="serv@barbearia.com", created_by=self.dono
        )
        
        # Cria um profissional válido
        self.barbeiro = Usuario.objects.create_user(
            username="barbeiro_serv", email="barbeiro@serv.com", password="senha", cpf="66666666666", tipo_usuario="BARBEIRO"
        )
        self.profissional = Profissional.objects.create(
            barbearia=self.barbearia,
            usuario=self.barbeiro,
            comissao_percentual=50
        )
        self.service = ServicoService()

    def test_criar_servico_com_profissionais_especificos_com_sucesso(self):
        """Deve criar o serviço e os vínculos de habilitação."""
        dto = ServicoCreateDTO(
            nome="Barba Terapia",
            preco=Decimal("80.00"),
            duracao_minutos=60,
            todos_profissionais_habilitados=False,
            profissional_ids=[self.profissional.id]
        )
        
        result = self.service.criar_servico(dto, self.barbearia.id, self.dono.id)

        self.assertTrue(result.success)
        self.assertEqual(Servico.objects.filter(nome="Barba Terapia").count(), 1)
        self.assertEqual(ServicoProfissional.objects.filter(habilitado=True).count(), 1)

    def test_criar_servico_com_profissional_inexistente_deve_fazer_rollback(self):
        """Se um profissional_id for inválido, o serviço NÃO deve ser criado (Rollback)."""
        dto = ServicoCreateDTO(
            nome="Serviço Órfão",
            preco=Decimal("50.00"),
            duracao_minutos=30,
            todos_profissionais_habilitados=False,
            profissional_ids=[9999]  # ID que não existe
        )
        
        result = self.service.criar_servico(dto, self.barbearia.id, self.dono.id)

        self.assertFalse(result.success)
        self.assertIn("não encontrado", result.error.lower())
        
        # VERIFICAÇÃO CRÍTICA DE ROLLBACK: O serviço não deve existir no banco
        self.assertEqual(Servico.objects.filter(nome="Serviço Órfão").count(), 0)