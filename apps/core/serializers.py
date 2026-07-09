# [Domínio: core] [Skill: serializer]
"""
📖 MANIFESTO (Skill 04 - View):
"O Serializer do DRF executa a higienização de strings de entrada
(limpeza de máscaras de CEP/CNPJ/Telefone)"

📖 MANIFESTO (Negative Constraints):
"PROIBIDO vazar dicionários primitivos (request.data) para o Service sem
validação prévia por um Serializer fortemente tipado"

✅ Regras seguidas:
- Serializers validam dados de entrada
- Serializers convertem para Pydantic DTOs
- Higienização de dados (remove máscaras)
- Não expõe dados sensíveis na resposta
- telefone vazio/blank normalizado para None antes de chegar ao DTO
"""
from typing import Optional

from rest_framework import serializers

from apps.core.dtos import UsuarioCreateDTO, UsuarioUpdateDTO


def _clean_telefone(value: Optional[str]) -> Optional[str]:
    """Higieniza telefone: remove máscaras e normaliza vazio para None."""
    if not value:
        return None
    cleaned = ''.join(filter(str.isdigit, value))
    if len(cleaned) > 15:
        raise serializers.ValidationError("Telefone muito longo.")
    return cleaned or None


class UsuarioCreateSerializer(serializers.Serializer):
    """Serializer para criação de usuário."""
    username = serializers.CharField(max_length=150, min_length=3)
    first_name = serializers.CharField(max_length=150, min_length=2)
    last_name = serializers.CharField(max_length=150, min_length=2)
    email = serializers.EmailField()
    cpf = serializers.CharField(max_length=11, min_length=11)
    password = serializers.CharField(write_only=True, min_length=8)
    tipo_usuario = serializers.ChoiceField(
        choices=['CLIENTE_FINAL', 'BARBEIRO', 'DONO']
    )
    telefone = serializers.CharField(
        max_length=15,
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None
    )

    def validate_cpf(self, value: str) -> str:
        """Remove máscaras e valida CPF."""
        cleaned_cpf = ''.join(filter(str.isdigit, value))
        if len(cleaned_cpf) != 11:
            raise serializers.ValidationError("CPF deve ter exatamente 11 dígitos.")
        return cleaned_cpf

    def validate_telefone(self, value: Optional[str]) -> Optional[str]:
        return _clean_telefone(value)

    def to_dto(self) -> UsuarioCreateDTO:
        """Converte dados validados para Pydantic DTO."""
        return UsuarioCreateDTO(**self.validated_data)


class UsuarioUpdateSerializer(serializers.Serializer):
    """Serializer para atualização de usuário."""
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    email = serializers.EmailField(required=False)
    telefone = serializers.CharField(
        max_length=15,
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None
    )
    password = serializers.CharField(
        write_only=True,
        required=False,
        min_length=8
    )

    def validate_telefone(self, value: Optional[str]) -> Optional[str]:
        return _clean_telefone(value)

    def to_dto(self) -> UsuarioUpdateDTO:
        """Converte dados validados para Pydantic DTO."""
        return UsuarioUpdateDTO(**self.validated_data)


class UsuarioResponseSerializer(serializers.Serializer):
    """Serializer para resposta (não expõe dados sensíveis)."""
    id = serializers.UUIDField()
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    cpf_masked = serializers.CharField()
    tipo_usuario = serializers.CharField()
    telefone = serializers.CharField(allow_null=True)
    date_joined = serializers.DateTimeField()
