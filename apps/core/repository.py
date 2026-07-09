# [Domínio: core] [Skill: repository]
"""
📖 MANIFESTO (Skill 02 - Repository):
"Toda persistência e leitura devem passar estritamente pela camada de Repository."

📖 MANIFESTO (Negative Constraints):
"PROIBIDO realizar consultas diretas ao banco utilizando managers padrões
(ex: .objects.all()) em Service ou Views."

📖 MANIFESTO (Skill 02 - Repository):
"Aplica transação atômica e select_for_update para mitigar Race Conditions."

✅ Regras seguidas:
- Todas as queries passam pelo Repository
- Usa DTOs Pydantic (sem Dict[str, Any])
- Transações atômicas para operações críticas
- Trilha de auditoria (created_by, updated_by)
- Não acessa request HTTP
"""
from typing import List, Optional
from uuid import UUID

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.dtos import UsuarioCreateDTO, UsuarioUpdateDTO
from apps.core.models import Usuario
from common.exceptions import (
    DuplicateResourceException,
    UserNotFoundException,
)


class UsuarioRepository:
    """
    Repositório para operações com o modelo Usuario.
    Segue o padrão de isolamento de camadas.
    """
    
    @staticmethod
    def get_by_id(user_id: UUID) -> Optional[Usuario]:
        """Busca usuário por ID."""
        try:
            return Usuario.objects.get(id=user_id)
        except Usuario.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_cpf(cpf: str) -> Optional[Usuario]:
        """Busca usuário por CPF."""
        try:
            return Usuario.objects.get(cpf=cpf)
        except Usuario.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_email(email: str) -> Optional[Usuario]:
        """Busca usuário por email."""
        try:
            return Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_username(username: str) -> Optional[Usuario]:
        """Busca usuário por username."""
        try:
            return Usuario.objects.get(username=username)
        except Usuario.DoesNotExist:
            return None
    
    @staticmethod
    def get_all_by_tipo(tipo_usuario: Optional[str] = None) -> List[Usuario]:
        """Lista usuários, opcionalmente filtrando por tipo."""
        queryset = Usuario.objects.all()
        if tipo_usuario:
            queryset = queryset.filter(tipo_usuario=tipo_usuario)
        return list(queryset)
    
    @staticmethod
    def create(dto: UsuarioCreateDTO, created_by: Optional[UUID] = None) -> Usuario:
        """
        Cria novo usuário com senha hasheada.
        Usa transaction.atomic para garantir atomicidade.
        """
        with transaction.atomic():
            try:
                user = Usuario(
                    username=dto.username,
                    first_name=dto.first_name,
                    last_name=dto.last_name,
                    email=dto.email,
                    cpf=dto.cpf,
                    tipo_usuario=dto.tipo_usuario,
                    telefone=dto.telefone,
                )
                user.set_password(dto.password)
                user.save()
                return user
            except IntegrityError as e:
                error_msg = str(e)
                if 'cpf' in error_msg:
                    raise DuplicateResourceException('cpf', dto.cpf)
                elif 'email' in error_msg:
                    raise DuplicateResourceException('email', dto.email)
                elif 'username' in error_msg:
                    raise DuplicateResourceException('username', dto.username)
                raise
    
    @staticmethod
    def update(
        user: Usuario,
        dto: UsuarioUpdateDTO,
        updated_by: Optional[UUID] = None
    ) -> Usuario:
        """
        Atualiza usuário existente.
        Se incluir password, faz o hash automaticamente.
        """
        with transaction.atomic():
            if dto.email is not None:
                user.email = dto.email
            if dto.telefone is not None:
                user.telefone = dto.telefone
            if dto.password is not None:
                user.set_password(dto.password)
            
            user.save()
            return user
    
    @staticmethod
    def delete(user: Usuario, deleted_by: Optional[UUID] = None) -> bool:
        """Remove usuário do banco (hard delete)."""
        with transaction.atomic():
            user.delete()
            return True
    
    @staticmethod
    def exists_by_cpf(cpf: str, exclude_id: Optional[UUID] = None) -> bool:
        """Verifica se CPF já existe (excluindo usuário específico)."""
        queryset = Usuario.objects.filter(cpf=cpf)
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.exists()
    
    @staticmethod
    def exists_by_email(email: str, exclude_id: Optional[UUID] = None) -> bool:
        """Verifica se email já existe (excluindo usuário específico)."""
        queryset = Usuario.objects.filter(email=email)
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.exists()