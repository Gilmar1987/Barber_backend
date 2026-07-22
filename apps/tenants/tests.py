from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.tenants.models import Barbearia
from apps.tenants.services import BarbeariaService
from apps.tenants.dtos import BarbeariaCreateDTO

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
        self.barbearia_data = BarbeariaCreateDTO(
            nome_comercial="Barbearia do Teste",
            cnpj="12345678000199",
            cep="12345678",
            logradouro="Rua dos Testes",
            numero="100",
            bairro="Centro",
            cidade="Recife",
            estado="PE",
            email="dono@test.com",
            latitude=-8.05784,
            longitude=-34.88291
        )

    def test_create_barbearia_success(self):
        result = BarbeariaService().criar_barbearia(self.barbearia_data, self.user.id)
        self.assertTrue(result.success)
        
        barbearia_id = result.data.id
        barbearia = Barbearia.objects.get(id=barbearia_id)
        
        # Verify barbearia is created correctly
        self.assertIsNotNone(barbearia.id)
        self.assertEqual(barbearia.nome_comercial, "Barbearia do Teste")
        
        # Verify user is linked and updated to DONO
        self.user.refresh_from_db()
        self.assertEqual(self.user.barbearia_vinculo, barbearia)
        self.assertEqual(self.user.tipo_usuario, "DONO")

    def test_create_barbearia_duplicate_cnpj_fails(self):
        # First creation
        result1 = BarbeariaService().criar_barbearia(self.barbearia_data, self.user.id)
        self.assertTrue(result1.success)
        
        # Second creation with same data (same CNPJ) should return success=False
        user2 = Usuario.objects.create_user(
            username="dono_test2",
            email="dono2@test.com",
            cpf="b"*64,
            password="password123"
        )
        result2 = BarbeariaService().criar_barbearia(self.barbearia_data, user2.id)
        self.assertFalse(result2.success)

    def test_listar_contextos_usuario_dono_multiple_barbearias(self):
        # Create first barbearia for user
        result1 = BarbeariaService().criar_barbearia(self.barbearia_data, self.user.id)
        self.assertTrue(result1.success)
        barbearia1_id = result1.data.id
        
        # Create second barbearia data
        barbearia_data_2 = BarbeariaCreateDTO(
            nome_comercial="Segunda Barbearia",
            cnpj="98765432000188",
            cep="12345678",
            logradouro="Avenida Principal",
            numero="200",
            bairro="Centro",
            cidade="Recife",
            estado="PE",
            email="dono@test.com",
            latitude=-8.05784,
            longitude=-34.88291
        )
        
        # Create second barbearia for same user
        result2 = BarbeariaService().criar_barbearia(barbearia_data_2, self.user.id)
        self.assertTrue(result2.success)
        barbearia2_id = result2.data.id
        
        # In the context of multiple barbearias, let's list the contexts
        result_contexts = BarbeariaService().listar_contextos_usuario(self.user.id)
        self.assertTrue(result_contexts.success)
        self.assertEqual(len(result_contexts.data), 2)
        
        # Check that we have the contexts correctly mapped
        ids = [item.barbearia_id for item in result_contexts.data]
        self.assertIn(barbearia1_id, ids)
        self.assertIn(barbearia2_id, ids)
        
        # Check papel is DONO
        for item in result_contexts.data:
            self.assertEqual(item.papel, "DONO")


