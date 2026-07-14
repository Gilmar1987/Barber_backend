# [Domínio: tenants] [Skill: serializer]
"""
📖 MANIFESTO (Skill 04 - View):
"O Serializer do DRF executa a higienização de strings de entrada"

📖 MANIFESTO (Negative Constraints):
"PROIBIDO vazar dicionários primitivos (request.data) para o Service sem
validação prévia por um Serializer fortemente tipado"

📖 MANIFESTO (Higienização):
"Remove máscaras de CNPJ, CEP, telefone antes de chegar ao DTO Pydantic"

✅ Regras seguidas:
- Serializers validam dados de entrada (DRF)
- Serializers convertem para Pydantic DTOs (to_dto)
- Higienização de dados (remove máscaras)
- Campos obrigatórios vs opcionais claramente definidos
- Validações customizadas (CNPJ, CEP, coordenadas)
"""
from rest_framework import serializers


class BarbeariaCreateSerializer(serializers.Serializer):
    """
    Serializer para criação de barbearia.
    Higieniza CNPJ, CEP e telefone antes de converter para DTO.
    """
    nome_comercial = serializers.CharField(max_length=255, min_length=3)
    cnpj = serializers.CharField(max_length=18, min_length=14)  # Aceita máscara
    cep = serializers.CharField(max_length=9, min_length=8)  # Aceita máscara
    logradouro = serializers.CharField(max_length=255, min_length=3)
    numero = serializers.CharField(max_length=20, min_length=1)
    complemento = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    bairro = serializers.CharField(max_length=100, min_length=2)
    cidade = serializers.CharField(max_length=100, min_length=2)
    estado = serializers.CharField(max_length=2)
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    telefone = serializers.CharField(max_length=15, required=False, allow_blank=True, allow_null=True)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    
    def _clean_cnpj(self, value: str) -> str:
        """Remove máscara do CNPJ (12.345.678/0001-99 → 12345678000199)."""
        if not value:
            return value
        return ''.join(filter(str.isdigit, value))
    
    def _clean_cep(self, value: str) -> str:
        """Remove máscara do CEP (01001-000 → 01001000)."""
        if not value:
            return value
        return ''.join(filter(str.isdigit, value))
    
    def _clean_telefone(self, value: str) -> str:
        """Remove máscara do telefone ((11) 99999-9999 → 11999999999)."""
        if not value:
            return None
        cleaned = ''.join(filter(str.isdigit, value))
        return cleaned if cleaned else None
    
    def validate_cnpj(self, value: str) -> str:
        """Higieniza e valida CNPJ."""
        cleaned = self._clean_cnpj(value)
        if len(cleaned) != 14:
            raise serializers.ValidationError("CNPJ deve ter exatamente 14 dígitos.")
        return cleaned
    
    def validate_cep(self, value: str) -> str:
        """Higieniza e valida CEP."""
        cleaned = self._clean_cep(value)
        if len(cleaned) != 8:
            raise serializers.ValidationError("CEP deve ter exatamente 8 dígitos.")
        return cleaned
    
    def validate_telefone(self, value: str) -> str:
        """Higieniza telefone (retorna None se vazio)."""
        return self._clean_telefone(value)
    
    def validate_estado(self, value: str) -> str:
        """Valida se estado é UF válida (2 letras maiúsculas)."""
        v_upper = value.upper()
        if len(v_upper) != 2 or not v_upper.isalpha():
            raise serializers.ValidationError("Estado deve ser uma UF válida (ex: SP, RJ, MG).")
        return v_upper
    
    def to_dto(self):
        """Converte dados validados para Pydantic DTO."""
        from apps.tenants.dtos import BarbeariaCreateDTO
        
        return BarbeariaCreateDTO(
            nome_comercial=self.validated_data['nome_comercial'],
            cnpj=self.validated_data['cnpj'],
            cep=self.validated_data['cep'],
            logradouro=self.validated_data['logradouro'],
            numero=self.validated_data['numero'],
            complemento=self.validated_data.get('complemento'),
            bairro=self.validated_data['bairro'],
            cidade=self.validated_data['cidade'],
            estado=self.validated_data['estado'],
            latitude=self.validated_data['latitude'],
            longitude=self.validated_data['longitude'],
            telefone=self.validated_data.get('telefone'),
            email=self.validated_data.get('email'),
        )


class BarbeariaUpdateSerializer(serializers.Serializer):
    """
    Serializer para atualização de barbearia (partial update).
    Todos os campos são opcionais.
    """
    nome_comercial = serializers.CharField(max_length=255, min_length=3, required=False)
    cep = serializers.CharField(max_length=9, min_length=8, required=False)
    logradouro = serializers.CharField(max_length=255, min_length=3, required=False)
    numero = serializers.CharField(max_length=20, min_length=1, required=False)
    complemento = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    bairro = serializers.CharField(max_length=100, min_length=2, required=False)
    cidade = serializers.CharField(max_length=100, min_length=2, required=False)
    estado = serializers.CharField(max_length=2, required=False)
    latitude = serializers.FloatField(min_value=-90, max_value=90, required=False)
    longitude = serializers.FloatField(min_value=-180, max_value=180, required=False)
    telefone = serializers.CharField(max_length=15, required=False, allow_blank=True, allow_null=True)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    ativo = serializers.BooleanField(required=False)
    
    def _clean_cep(self, value: str) -> str:
        """Remove máscara do CEP."""
        if not value:
            return value
        return ''.join(filter(str.isdigit, value))
    
    def _clean_telefone(self, value: str) -> str:
        """Remove máscara do telefone."""
        if not value:
            return None
        cleaned = ''.join(filter(str.isdigit, value))
        return cleaned if cleaned else None
    
    def validate_cep(self, value: str) -> str:
        """Higieniza e valida CEP."""
        cleaned = self._clean_cep(value)
        if len(cleaned) != 8:
            raise serializers.ValidationError("CEP deve ter exatamente 8 dígitos.")
        return cleaned
    
    def validate_telefone(self, value: str) -> str:
        """Higieniza telefone."""
        return self._clean_telefone(value)
    
    def validate_estado(self, value: str) -> str:
        """Valida UF."""
        v_upper = value.upper()
        if len(v_upper) != 2 or not v_upper.isalpha():
            raise serializers.ValidationError("Estado deve ser uma UF válida.")
        return v_upper
    
    def to_dto(self):
        """Converte dados validados para Pydantic DTO."""
        from apps.tenants.dtos import BarbeariaUpdateDTO
        
        return BarbeariaUpdateDTO(
            nome_comercial=self.validated_data.get('nome_comercial'),
            cep=self.validated_data.get('cep'),
            logradouro=self.validated_data.get('logradouro'),
            numero=self.validated_data.get('numero'),
            complemento=self.validated_data.get('complemento'),
            bairro=self.validated_data.get('bairro'),
            cidade=self.validated_data.get('cidade'),
            estado=self.validated_data.get('estado'),
            latitude=self.validated_data.get('latitude'),
            longitude=self.validated_data.get('longitude'),
            telefone=self.validated_data.get('telefone'),
            email=self.validated_data.get('email'),
            ativo=self.validated_data.get('ativo'),
        )


class ProximidadeSearchSerializer(serializers.Serializer):
    """
    Serializer para busca por proximidade geográfica.
    """
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    raio_km = serializers.FloatField(min_value=0.1, max_value=100, default=10.0)
    
    def to_dto(self):
        """Converte dados validados para Pydantic DTO."""
        from apps.tenants.dtos import ProximidadeSearchDTO
        
        return ProximidadeSearchDTO(
            latitude=self.validated_data['latitude'],
            longitude=self.validated_data['longitude'],
            raio_km=self.validated_data.get('raio_km', 10.0),
        )


class BarbeariaResponseSerializer(serializers.Serializer):
    """
    Serializer para resposta de barbearia (não expõe dados sensíveis).
    Usado apenas para documentação no Swagger (drf-spectacular).
    """
    id = serializers.UUIDField()
    nome_comercial = serializers.CharField()
    cnpj_masked = serializers.CharField()
    logradouro = serializers.CharField()
    numero = serializers.CharField()
    complemento = serializers.CharField(allow_null=True)
    bairro = serializers.CharField()
    cidade = serializers.CharField()
    estado = serializers.CharField()
    cep = serializers.CharField()
    latitude = serializers.FloatField(allow_null=True)
    longitude = serializers.FloatField(allow_null=True)
    telefone = serializers.CharField(allow_null=True)
    email = serializers.EmailField(allow_null=True)
    ativo = serializers.BooleanField()
    is_deleted = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)


class BarbeariaListSerializer(serializers.Serializer):
    """
    Serializer para listagem de barbearias (versão resumida).
    """
    id = serializers.UUIDField()
    nome_comercial = serializers.CharField()
    cnpj_masked = serializers.CharField()
    cidade = serializers.CharField()
    estado = serializers.CharField()
    telefone = serializers.CharField(allow_null=True)
    ativo = serializers.BooleanField()
    is_deleted = serializers.BooleanField()


class BarbeariaListWithDistanceSerializer(serializers.Serializer):
    """
    Serializer para listagem com distância (busca por proximidade).
    """
    id = serializers.UUIDField()
    nome_comercial = serializers.CharField()
    cnpj_masked = serializers.CharField()
    cidade = serializers.CharField()
    estado = serializers.CharField()
    telefone = serializers.CharField(allow_null=True)
    ativo = serializers.BooleanField()
    is_deleted = serializers.BooleanField()
    distancia_metros = serializers.FloatField(allow_null=True)

