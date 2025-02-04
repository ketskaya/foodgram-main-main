from rest_framework.pagination import LimitOffsetPagination

from .constants import PAGE_SIZE, MAX_PAGE_SIZE, LIMIT_QUERY_PARAM


class PageToOffsetPagination(LimitOffsetPagination):
    page_size = PAGE_SIZE
    page_size_query_param = LIMIT_QUERY_PARAM
    max_page_size = MAX_PAGE_SIZE
