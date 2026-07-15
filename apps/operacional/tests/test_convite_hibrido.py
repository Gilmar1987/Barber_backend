from unittest.mock import patch

from django.test import TestCase

from apps.core.models import Usuario
from apps.operacional.dtos import ConviteProfissionalCreateDTO
from apps.operacional.models import ConviteProfissional, Profissional
from apps.operacional.services import ConviteProfissionalService
from apps.tenants.models import Barbearia


class ConviteHibridoTestCase(TestCase):
    """Teste end-to-end do fluxo de convite e aceite."""

    def setUp(self):
        self.dono = Usuario.objects.create_user(
            username="dono_teste", email="dono@test.com", password="senha", cpf="33333333333", tipo_usuario="DONO"
        )
        self.barbearia = Barbearia.objects.create(
            nome_comercial="Barbearia Teste", cnpj="33333333000133", cep="00000000",
            logradouro="Rua Teste", numero="1", bairro="Bairro", cidade="Cidade", estado="SP",
            email="teste@barbearia.com", created_by=self.dono
        )
        self.service = ConviteProfissionalService()

    @patch('common.email_service.BrevoEmailService.enviar_convite_profissional')
    def test_fluxo_completo_criacao_e_aceite(self, mock_email):
        """Simula DONO criando convite e Barbeiro aceitando."""
        mock_email.return_value = True

        # 1. DONO cria o convite
        dto = ConviteProfissionalCreateDTO(
            nome_completo="Carlos Novo",
            email="carlos.novo@email.com",
            cpf="44444444444",
            telefone="11999999999",
            comissao_percentual=60
        )
        result_criar = self.service.criar_convite(dto, self.barbearia.id, self.dono.id)

        self.assertTrue(result_criar.success)
        self.assertEqual(Usuario.objects.filter(email="carlos.novo@email.com", tipo_usuario="BARBEIRO").count(), 1)
        
        convite = ConviteProfissional.objects.get(email="carlos.novo@email.com")
        self.assertEqual(convite.status, ConviteProfissional.STATUS_PENDENTE)

        # 2. Barbeiro aceita o convite
        result_aceitar = self.service.aceitar_convite(convite.token)

        self.assertTrue(result_aceitar.success)
        
        convite.refresh_from_db()
        self.assertEqual(convite.status, ConviteProfissional.STATUS_ACEITO)

        # 3. Verifica se o vínculo Profissional foi criado
        usuario_carlos = Usuario.objects.get(email="carlos.novo@email.com")
        vinculo = Profissional.objects.filter(usuario=usuario_carlos, barbearia=self.barbearia).first()
        
        self.assertIsNotNone(vinculo)
        self.assertEqual(vinculo.comissao_percentual, 60)
        self.assertTrue(vinculo.ativo)