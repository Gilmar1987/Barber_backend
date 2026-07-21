# apps/agenda/serializers.py
from rest_framework import serializers
from datetime import date, timedelta
from apps.agenda.dtos import DisponibilidadeSearchDTO

class DisponibilidadeSearchSerializer(serializers.Serializer):
    """Serializer para validar parâmetros de busca de disponibilidade."""
    profissional_id = serializers.IntegerField(min_value=1)
    servico_id = serializers.IntegerField(min_value=1)
    data_inicio = serializers.DateField()
    data_fim = serializers.DateField(required=False)

    def validate(self, data):
        """Valida e define data_fim padrão (D+5)."""
        data_inicio = data.get('data_inicio')
        data_fim = data.get('data_fim')
        
        if not data_fim:
            # Regra de Negócio: Escopo D+5 dias
            data['data_fim'] = data_inicio + timedelta(days=5)
        elif data_fim > data_inicio + timedelta(days=30):
            raise serializers.ValidationError(
                "O intervalo máximo de busca é de 30 dias."
            )
        
        if data_inicio < date.today():
            raise serializers.ValidationError(
                "A data de início não pode ser no passado."
            )
        
        return data

    def to_dto(self) -> DisponibilidadeSearchDTO:
        """Converte dados validados para DTO Pydantic."""
        return DisponibilidadeSearchDTO(**self.validated_data)
    
# apps/agenda/serializers.py (Adicione no final do arquivo)

class SlotDisponivelSerializer(serializers.Serializer):
    """Serializer apenas para documentação do Swagger."""
    data = serializers.DateField()
    horario_inicio = serializers.TimeField()
    horario_fim = serializers.TimeField()