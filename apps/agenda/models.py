
# apps/agenda/models.py
from django.db import models
from django.conf import settings

class Agendamento(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('CONFIRMADO', 'Confirmado'),
        ('CANCELADO', 'Cancelado'),
        ('CONCLUIDO', 'Concluído'),
    ]

    barbearia = models.ForeignKey('tenants.Barbearia', on_delete=models.CASCADE, related_name='agendamentos')
    profissional = models.ForeignKey('operacional.Profissional', on_delete=models.PROTECT, related_name='agendamentos')
    servico = models.ForeignKey('operacional.Servico', on_delete=models.PROTECT, related_name='agendamentos')
    
    # Cliente pode ser um usuário registrado ou um walk-in (nome/telefone)
    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='meus_agendamentos')
    nome_cliente = models.CharField(max_length=255)
    telefone_cliente = models.CharField(max_length=20)
    
    data = models.DateField()
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    observacoes = models.TextField(blank=True, null=True)
    
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data', '-hora_inicio']
        # 🛡️ Segunda linha de defesa: Restrição no banco de dados
        constraints = [
            models.UniqueConstraint(
                fields=['profissional', 'data', 'hora_inicio'],
                name='unique_profissional_data_hora',
                condition=models.Q(status__in=['PENDENTE', 'CONFIRMADO'])
            )
        ]

    def __str__(self):
        return f"{self.servico.nome} com {self.profissional.usuario.username} em {self.data} às {self.hora_inicio}"
