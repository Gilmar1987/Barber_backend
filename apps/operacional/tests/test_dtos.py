from datetime import date, time
from decimal import Decimal

from django.test import TestCase
from pydantic import ValidationError

from apps.operacional.dtos import (
    ConviteProfissionalCreateDTO,
    GradeHorariaCreateDTO,
    ServicoCreateDTO,
)


class DTOTestCase(TestCase):
    """Testes unitários para validar regras de negócio nos DTOs (Pydantic)."""

    def test_grade_horaria_com_hora_fim_anterior_deve_falhar(self):
        """Hora de término não pode ser anterior à hora de início."""
        with self.assertRaises(ValidationError) as context:
            GradeHorariaCreateDTO(
                dia_semana=1,
                hora_inicio=time(18, 0),
                hora_fim=time(9, 0),  # Inválido!
            )
        self.assertIn("hora_fim deve ser posterior", str(context.exception))

    def test_convite_com_cpf_invalido_deve_falhar(self):
        """CPF deve ter exatamente 11 dígitos após higienização."""
        with self.assertRaises(ValidationError) as context:
            ConviteProfissionalCreateDTO(
                nome_completo="Carlos Silva",
                email="carlos@email.com",
                cpf="123456",  # Inválido!
                comissao_percentual=50,
            )
        self.assertIn("at least 11 characters", str(context.exception))

    def test_servico_com_preco_zero_ou_negativo_deve_falhar(self):
        """Preço do serviço deve ser maior que zero."""
        with self.assertRaises(ValidationError):
            ServicoCreateDTO(
                nome="Corte",
                preco=Decimal("0.00"),  # Inválido!
                duracao_minutos=30,
            )