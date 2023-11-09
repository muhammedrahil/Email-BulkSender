from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'pageSize'

    def get_paginated_response(self, data):
        return Response({
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'per_page': self.page_size,
            'current_page': self.page.number,
            'total': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'data': data
        })
        
        
class CustomPagination():
    pagination_class = StandardResultSetPagination
    
    def get_pagination(this, self, request, queryset):
        page = this.pagination_class()
        queryset = page.paginate_queryset(queryset, request)
        serializer = self.serializer_class(queryset, many=True).data
        return page.get_paginated_response(serializer)