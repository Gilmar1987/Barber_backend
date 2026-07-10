from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.tenants.models import Barbearia
from apps.tenants.services import BarbeariaService

Usuario = get_user_model()

class BarbeariaServiceTest(TestCase):
    def setUp(self):
        # We need a user to create a barbearia
        self.user = Usuario.objects.create_user(
            username="dono_test",
            email="dono@test.com",
            cpf="a"*64,  # valid hex hash format
            password="password123",
            tipo_usuario="CLIENTE_FINAL"
        )
        self.barbearia_data = {
            "nome_comercial": "Barbearia do Teste",
            "cnpj": "12345678000199",
            "slug": "barbearia-do-teste",
            "cep": "12345678",
            "numero": "100",
            "endereco_completo": "Rua dos Testes, 100"
        }

    def test_create_barbearia_success(self):
        barbearia = BarbeariaService.create_barbearia(self.barbearia_data, str(self.user.id))
        
        # Verify barbearia is created correctly
        self.assertIsNotNone(barbearia.id)
        self.assertEqual(barbearia.nome_comercial, "Barbearia do Teste")
        
        # Verify user is linked and updated to DONO
        self.user.refresh_from_db()
        self.assertEqual(self.user.barbearia_vinculo, barbearia)
        self.assertEqual(self.user.tipo_usuario, "DONO")

    def test_create_barbearia_duplicate_cnpj_fails(self):
        # First creation
        BarbeariaService.create_barbearia(self.barbearia_data, str(self.user.id))
        
        # Second creation with same data (same CNPJ) should raise ValueError
        user2 = Usuario.objects.create_user(
            username="dono_test2",
            email="dono2@test.com",
            cpf="b"*64,
            password="password123"
        )
        with self.assertRaises(ValueError):
            BarbeariaService.create_barbearia(self.barbearia_data, str(user2.id))

