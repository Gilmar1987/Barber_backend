# [Domínio: core] [Skill: pagination]
"""
📖 MANIFESTO (Tech Stack):
"django-filter + drf-spectacular (OpenAPI 3 / Swagger)"

✅ Regras seguidas:
- Paginação padrão consistente
- Metadata útil para frontend
- Compatível com drf-spectacular
"""
from typing import Any, Dict

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """Paginação padrão do sistema."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data: Any) -> Response:
        return Response({
            'success': True,
            'pagination': {
                'total_items': self.page.paginator.count,
                'total_pages': self.page.paginator.num_pages,
                'current_page': self.page.number,
                'page_size': self.get_page_size(self.request),
                'has_next': self.page.has_next(),
                'has_previous': self.page.has_previous(),
            },
            'data': data
        })