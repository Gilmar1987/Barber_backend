# apps/agenda/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, OpenApiResponse
from apps.agenda.serializers import DisponibilidadeSearchSerializer, SlotDisponivelSerializer, AgendamentoCreateSerializer
from apps.agenda.services import DisponibilidadeService, AgendamentoService
from apps.agenda.dtos import AgendamentoCreateDTO

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
    def post(self, request):
        # 1. Extrai o contexto multi-tenant (usando o helper que já funcionou)
        try:
            from apps.operacional.views import _get_barbearia_id_from_jwt
            barbearia_id = _get_barbearia_id_from_jwt(request)
        except ValueError as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_403_FORBIDDEN)

        # 2. Valida o payload
        serializer = AgendamentoCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        dto: AgendamentoCreateDTO = serializer.to_dto()
        cliente_id = request.user.id if request.user.is_authenticated else None

        # 3. Delega ao Service
        result = self.service.criar_agendamento(dto=dto, barbearia_id=barbearia_id, cliente_id=cliente_id)

        if result['success']:
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            # Se for conflito de horário, retorna 409 Conflict, senão 400
            status_code = status.HTTP_409_CONFLICT if "Conflito de horário" in (result.get('error') or '') else status.HTTP_400_BAD_REQUEST
            return Response(result, status=status_code)