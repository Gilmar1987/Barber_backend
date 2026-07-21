# apps/agenda/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from apps.agenda.serializers import DisponibilidadeSearchSerializer, SlotDisponivelSerializer
from apps.agenda.services import DisponibilidadeService

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