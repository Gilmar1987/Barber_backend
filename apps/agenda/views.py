# apps/agenda/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, OpenApiResponse
from apps.agenda.serializers import DisponibilidadeSearchSerializer, SlotDisponivelSerializer, AgendamentoCreateSerializer
from apps.agenda.services import DisponibilidadeService, AgendamentoService, AgendamentoClienteService, AgendamentoClienteDeleteService
from apps.agenda.dtos import AgendamentoCreateDTO
from django.utils import timezone
from datetime import datetime

class DisponibilidadePagination(PageNumberPagination):
    """Paginação para slots de disponibilidade."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class DisponibilidadeView(APIView):
    """
    GET /api/v1/agenda/disponibilidade/
    Calcula slots de horário disponíveis para um profissional e serviço.
    """
    permission_classes = [AllowAny]  # Cliente final não autenticado pode consultar
    pagination_class = DisponibilidadePagination

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = DisponibilidadeService()

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='profissional_id', 
                type=OpenApiTypes.INT, 
                location=OpenApiParameter.QUERY, 
                required=True,
                description='ID do profissional'
            ),
            OpenApiParameter(
                name='servico_id', 
                type=OpenApiTypes.INT, 
                location=OpenApiParameter.QUERY, 
                required=True,
                description='ID do serviço'
            ),
            OpenApiParameter(
                name='data_inicio', 
                type=OpenApiTypes.DATE, 
                location=OpenApiParameter.QUERY, 
                required=True, 
                description="Data inicial (formato: YYYY-MM-DD)"
            ),
            OpenApiParameter(
                name='data_fim', 
                type=OpenApiTypes.DATE, 
                location=OpenApiParameter.QUERY, 
                required=False, 
                description="Data final (padrão: data_inicio + 5 dias)"
            ),
        ],
        responses={
            200: SlotDisponivelSerializer(many=True),
            400: "Erro de validação ou cálculo"
        },
        description='Calcula slots de horário disponíveis para um profissional e serviço em um intervalo de datas.',
        tags=['Agenda']
    )
    def get(self, request):
        """Calcula e retorna slots disponíveis com paginação."""
        serializer = DisponibilidadeSearchSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        dto = serializer.to_dto()
        result = self.service.calcular_disponibilidade(dto)

        if not result.success:
            return Response(result.model_dump(), status=status.HTTP_400_BAD_REQUEST)

        # ✅ Regra 10: Aplicar paginação nos slots gerados
        paginator = self.pagination_class()
        
        # Converte DTOs para dict para o paginator do DRF
        data_dicts = [slot.model_dump() for slot in result.data]
        page = paginator.paginate_queryset(data_dicts, request)

        if page is not None:
            return Response({
                'success': True,
                'data': page,
                'error': None,
                'details': {
                    'count': paginator.page.paginator.count,
                    'next': paginator.get_next_link(),
                    'previous': paginator.get_previous_link(),
                    'page': paginator.page.number,
                    'page_size': paginator.page_size,
                    'total_slots_gerados': result.details['total_slots']
                }
            }, status=status.HTTP_200_OK)

        return Response({
            'success': True,
            'data': data_dicts,
            'error': None,
            'details': result.details
        }, status=status.HTTP_200_OK)
    





#from apps.agenda.serializers import AgendamentoCreateSerializer # (Veja nota abaixo)
#from apps.agenda.services import AgendamentoService

class AgendamentoCreateView(APIView):
    """
    POST /api/v1/agenda/agendamentos/
    Cria um novo agendamento com proteção contra concorrência (double-booking).
    """
    permission_classes = [IsAuthenticated] # Ou AllowAny se permitir agendamento sem login (walk-in)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = AgendamentoService()

    @extend_schema(
        request=AgendamentoCreateSerializer,
        responses={
            201: OpenApiResponse(description='Agendamento criado com sucesso'),
            400: OpenApiResponse(description='Erro de validação ou conflito de horário'),
            403: OpenApiResponse(description='Acesso negado (Multi-tenant)'),
        },
        tags=['Agenda']
    )
    # apps/agenda/views.py (AgendamentoCreateView)


    def post(self, request):
        serializer = AgendamentoCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        dto: AgendamentoCreateDTO = serializer.to_dto()
        tipo_usuario = getattr(request.user, 'tipo_usuario', None)

        # Validar se a data não é menor que atual
        agendamento_dateTime = datetime.combine(dto.data, dto.hora_inicio)

        aware_datetime = timezone.make_aware(agendamento_dateTime)
        if aware_datetime < timezone.now():
            return Response({'success': False, 'error': 'Não é permitido agendar em uma data/hora passada.'}, status=400)

        # LÓGICA DE RESOLUÇÃO DO TENANT:
        if tipo_usuario in ('DONO', 'BARBEIRO'):
            # Se for dono/barbeiro, valida se a barbearia do payload bate com a do JWT (segurança extra)
            jwt_barbearia_id = getattr(request.user, 'tenant_id', None)
            if str(dto.barbearia_id) != str(jwt_barbearia_id):
                return Response({'success': False, 'error': 'Você só pode agendar na sua barbearia vinculada.'}, status=403)
            barbearia_id = dto.barbearia_id
            cliente_id = None # Agendamento feito pelo staff, não é "meu agendamento" de cliente
            
        elif tipo_usuario == 'CLIENTE_FINAL':
            # Cliente final informa em qual barbearia quer agendar
            barbearia_id = dto.barbearia_id
            cliente_id = request.user.id # Vincula o agendamento ao cliente logado
            
        else:
            return Response({'success': False, 'error': 'Perfil não autorizado.'}, status=403)

        # Delega ao Service (que já faz a validação se o profissional/serviço pertence a essa barbearia)
        result = self.service.criar_agendamento(
            dto=dto, 
            barbearia_id=barbearia_id, 
            cliente_id=cliente_id
            )

        if result.get('success'):
            response_data = result.get('data')
            if hasattr(response_data, 'model_dump'):
                return Response({
                    'success': True, 
                    'data': response_data.model_dump(),
                    'erro': result.get('erro'),
                    'message': result.get('message'),
                    'details': result.get('details'),

                    }, status=status.HTTP_201_CREATED)
        else:
            status_code = status.HTTP_409_CONFLICT if "Conflito de horário" in (result.get('error') or '') else status.HTTP_400_BAD_REQUEST
            return Response(
                result, 
                status=status_code)
       
        


class MeusAgendamentosView(APIView):
    """
    GET /api/v1/agenda/meus-agendamentos/
    Lista apenas os agendamentos do cliente autenticado.
    """
    permission_classes = [IsAuthenticated] # Garante que só usuários logados acessam
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = AgendamentoClienteService()

    @extend_schema(
        responses={
            200: OpenApiResponse(description='Lista de agendamentos do cliente'),
            401: OpenApiResponse(description='Não autenticado'),
            403: OpenApiResponse(description='Apenas CLIENTE_FINAL pode acessar este endpoint')
        },
        tags=['Agenda - Cliente']
    )
    def get(self, request):
        # 1. Validação de Perfil (Opcional, mas recomendado)
        tipo_usuario = getattr(request.user, 'tipo_usuario', None)
        if tipo_usuario != 'CLIENTE_FINAL':
            return Response(
                {'success': False, 'error': 'Acesso restrito a clientes finais.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 2. Extração segura do ID (Vem do JWT, impossível de forjar)
        cliente_id = request.user.id

        # 3. Delegação ao Service
        result = self.service.listar_meus_agendamentos(cliente_id=cliente_id)

        # 4. Resposta formatada
        if result.success:
            return Response({
                'success': True,
                'data': [item.model_dump() for item in result.data],
                'error': None,
                'details': {'total': len(result.data)}
            }, status=status.HTTP_200_OK)
        else:
            return Response(result.model_dump(), status=status.HTTP_400_BAD_REQUEST)
        
class AgendamentoClienteDeleteView(APIView):
    """
    DELETE /api/v1/agenda/meus-agendamentos/
    Exclui todos os agendamentos do cliente autenticado.
    """
    permission_classes = [IsAuthenticated] # Garante que só usuários logados acessam

    @extend_schema(
        responses={
            200: OpenApiResponse(description='Agendamentos excluídos com sucesso'),
            401: OpenApiResponse(description='Não autenticado'),
            403: OpenApiResponse(description='Apenas CLIENTE_FINAL pode acessar este endpoint')
        },
        tags=['Agenda - Cliente']
    )
    def delete(self, request):
        # 1. Validação de Perfil (Opcional, mas recomendado)
        tipo_usuario = getattr(request.user, 'tipo_usuario', None)
        if tipo_usuario != 'CLIENTE_FINAL':
            return Response(
                {'success': False, 'error': 'Acesso restrito a clientes finais.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 2. Extração segura do ID (Vem do JWT, impossível de forjar)
        cliente_id = request.user.id

        # 3. Delegação ao Service
        result = self.service.deletar_agus_agendamentos(cliente_id=cliente_id)

        # 4. Resposta formatada
        if result.success:
            return Response({
                'success': True,
                'message': result.message,
                'error': None,
                'details': None
            }, status=status.HTTP_200_OK)
        else:
            return Response(result.model_dump(), status=status.HTTP_400_BAD_REQUEST)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = AgendamentoClienteDeleteService()
        