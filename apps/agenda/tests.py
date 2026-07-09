from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.tenants.models import Barbearia
from apps.agenda.models import Profissional, Servico, Agendamento
from apps.agenda.serializers import AgendamentoInputSerializer
from django.utils import timezone
import uuid

Usuario = get_user_model()

class AgendamentoInputSerializerTest(APITestCase):
    def test_serializer_validation_with_uuid_success(self):
        profissional_uuid = uuid.uuid4()
        servico_uuid = uuid.uuid4()
        data_hora = timezone.now() + timezone.timedelta(days=1)
        
        data = {
            "profissional_id": str(profissional_uuid),
            "servico_id": str(servico_uuid),
            "data_hora": data_hora.isoformat()
        }
        
        serializer = AgendamentoInputSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["profissional_id"], profissional_uuid)
        self.assertEqual(serializer.validated_data["servico_id"], servico_uuid)


class AgendamentoAPITestCase(APITestCase):
    def setUp(self):
        # Create Barbearia 1
        self.barbearia = Barbearia.objects.create(
            nome_comercial="Barbearia Central",
            cnpj="11111111000111",
            slug="barbearia-central",
            cep="01001000",
            numero="10",
            endereco_completo="Praça da Sé"
        )
        
        # Create Barbearia 2 (for conflict test)
        self.barbearia_outra = Barbearia.objects.create(
            nome_comercial="Outra Barbearia",
            cnpj="22222222000122",
            slug="outra-barbearia",
            cep="02002000",
            numero="20",
            endereco_completo="Av. Paulista"
        )

        # Create Barber User and Professional Profile in Barbearia 1
        self.barbeiro_user = Usuario.objects.create_user(
            username="barbeiro_joe",
            email="joe@barber.com",
            cpf="a"*64,
            password="password123",
            tipo_usuario="BARBEIRO",
            barbearia_vinculo=self.barbearia
        )
        self.profissional = Profissional.objects.create(
            barbearia=self.barbearia,
            usuario=self.barbeiro_user,
            comissao_percentual=50
        )

        # Create Service in Barbearia 1
        self.servico = Servico.objects.create(
            barbearia=self.barbearia,
            nome="Corte Clássico",
            preco=50.00,
            duracao_minutos=30
        )

        # Create Service in Barbearia 2 (conflict)
        self.servico_outro = Servico.objects.create(
            barbearia=self.barbearia_outra,
            nome="Barba Premium",
            preco=40.00,
            duracao_minutos=30
        )

        # Create Client User (no barbearia vinculo)
        self.cliente = Usuario.objects.create_user(
            username="cliente_pedro",
            email="pedro@client.com",
            cpf="b"*64,
            password="password123",
            tipo_usuario="CLIENTE_FINAL",
            barbearia_vinculo=None
        )

    def test_agendar_servico_como_cliente_final_sucesso(self):
        # Authenticate client
        self.client.force_authenticate(user=self.cliente)
        
        data_hora = timezone.now() + timezone.timedelta(days=1)
        # Ensure we round to minutes to avoid microsecond differences in comparison
        data_hora = data_hora.replace(microsecond=0)
        
        payload = {
            "profissional_id": str(self.profissional.id),
            "servico_id": str(self.servico.id),
            "data_hora": data_hora.isoformat()
        }
        
        response = self.client.post("/api/v1/agenda/agendamentos/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        
        # Verify appointment in database
        appointment = Agendamento.objects.get(id=response.data["data"]["id"])
        self.assertEqual(appointment.cliente, self.cliente)
        self.assertEqual(appointment.profissional, self.profissional)
        self.assertEqual(appointment.servico, self.servico)
        self.assertEqual(appointment.barbearia, self.barbearia)
        self.assertEqual(appointment.status, "AGENDADO")

    def test_agendar_servico_de_outra_barbearia_falha(self):
        # Authenticate client
        self.client.force_authenticate(user=self.cliente)
        
        data_hora = timezone.now() + timezone.timedelta(days=1)
        
        # Service from barbearia_outra but professional from barbearia
        payload = {
            "profissional_id": str(self.profissional.id),
            "servico_id": str(self.servico_outro.id),
            "data_hora": data_hora.isoformat()
        }
        
        response = self.client.post("/api/v1/agenda/agendamentos/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("O profissional e o serviço devem pertencer à mesma barbearia.", response.data["erro"])

