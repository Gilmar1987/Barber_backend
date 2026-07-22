import hashlib
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.core.dtos import UsuarioCreateDTO
from apps.core.service import UsuarioService

_TEST_PASSWORD = os.environ.get("TEST_USER_PASSWORD", "Test@12345!")

Usuario = get_user_model()

class UsuarioModelTest(TestCase):
    def test_criar_usuario_com_dados_completos_passa_no_fluxo(self):
        service = UsuarioService()
        dto = UsuarioCreateDTO(
            username="novousuario",
            first_name="João",
            last_name="Silva",
            email="novo@example.com",
            cpf="12345678909",
            password=_TEST_PASSWORD,
            tipo_usuario="CLIENTE_FINAL",
            telefone="11999999999",
        )

        result = service.criar_usuario(dto)

        self.assertTrue(result.success, result.model_dump())
        self.assertEqual(result.data.username, "novousuario")
        self.assertEqual(result.data.first_name, "João")
        self.assertEqual(result.data.last_name, "Silva")

        user = Usuario.objects.get(username="novousuario")
        self.assertEqual(user.first_name, "João")
        self.assertTrue(user.check_password(_TEST_PASSWORD))

    def test_criar_usuario_com_cpf_hash_passa_na_validacao(self):
        cpf_hash = hashlib.blake2b(b"12345678909", digest_size=32).hexdigest()
        
        user = Usuario(
            username="testuser",
            first_name="Test",
            last_name="User",
            email="testuser@example.com",
            cpf=cpf_hash,
            tipo_usuario="CLIENTE_FINAL"
        )
        user.set_password(_TEST_PASSWORD)
        validate_password(_TEST_PASSWORD, user)
        
        try:
            user.full_clean()
        except ValidationError as e:
            self.fail(f"full_clean() raised ValidationError unexpectedly: {e}")

    def test_validar_cpf_invalido_falha(self):
        user = Usuario(
            username="testuser2",
            first_name="Test",
            last_name="User",
            email="testuser2@example.com",
            cpf="12345678900",
            tipo_usuario="CLIENTE_FINAL"
        )
        user.set_password(_TEST_PASSWORD)
        validate_password(_TEST_PASSWORD, user)
        
        with self.assertRaises(ValidationError):
            user.full_clean()

