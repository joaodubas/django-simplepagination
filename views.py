from django.core.paginator import Paginator, EmptyPage, InvalidPage

def paginate_queryset(queryset, per_page=15, page=1):
    """
    Receive a queryset and transform to a paginated queryset

    per_page -- number of objects per page
    page -- page being requested
    
    """
    paginator = Paginator(queryset, per_page)

    try:
        page = paginator.page(page)
    except (EmptyPage, InvalidPage):
        page = paginator.page(paginator.num_pages)
    
    return page

