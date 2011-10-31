# -*- encoding: utf-8 -*-
import urllib
import re

from django import template
from django.template import Context, loader, Node
from django.utils.translation import ugettext as _

register = template.Library()
# Regex for token keyword arguments
kwarg_re = re.compile(r"(?:(\w+)=)?(.+)")

def paginate(parse, token):
    bits = token.split_contents()

    if len(bits) < 2:
        raise template.TemplateSyntaxError(_(u'%s necessita de pelo menos um argumento (object_list).') % bits[0])
    
    paginator = bits[1]
    args = []
    kwargs = {}
    bits = bits[2:]

    if len(bits):
        for bit in bits:
            match = kwarg_re.match(bit)

            if not match:
                raise template.TemplateSyntaxError(_(u'Opção mal formada para %s') % bits[0])

            name, value = match.groups()

            if name:
                kwargs[str(name)] = value
            else:
                args.append(value)

    return PaginateNode(paginator, *args, **kwargs)


class TemplateTagMixin(object):
    def get_variable(self, variable):
        if isinstance(variable, str):
            var = getattr(self, variable)
        else:
            var = variable

        try:
            value = var.resolve(self.context)
        except template.VariableDoesNotExist:
            value = var
        
        return value
    
    def to_template(self, template, additional_context):
        t = loader.get_template(template)
        c = Context(additional_context, autoescape=self.context.autoescape)
        return t.render(c)


class PageLink(object):
    """Represent a link to a paginated resource"""
    def __init__(self, page, url_query=None):
        """Initialize the PageLink

        page -- a page number
        url_query -- additional parametes to be attached to the url query

        """
        self._page = page
        self._link = _('?pagina=%d') % page
        link_query = '&%s'

        if url_query:
            self._link += link_query % url_query

    def __str__(self):
        return self._page
    
    def __unicode__(self):
        return self._page
    
    def __repr__(self):
        return '%d <%s>' % (self._page, self._link)
    
    @property    
    def link(self):
        return self._link
    
    @property
    def number(self):
        return self._page


class PaginateNode(TemplateTagMixin, Node):
    def __init__(self, page, adjacent_pages='2', left_tail_num_pages='1', right_tail_num_pages='1', hide_limit='2', **kwargs):
        """Define the number of pages to be presented to the user, based on the
        number of adjancent pages and the number of pages on either tail.

        page -- an object django.core.paginator.Page
        adjacent_pages -- number of pages to be show next to the current page
        left_tail_num_pages -- number of pages at the beggining of the paginate
        right_tail_num_pages -- number of pages at the end of the paginate
        hide_limit -- the number of pages 'missing' to show an ellipsis

        """
        self.page = template.Variable(page)
        self.adjacent_pages = template.Variable(adjacent_pages)
        self.left_tail_num_pages = template.Variable(left_tail_num_pages)
        self.right_tail_num_pages = template.Variable(right_tail_num_pages)
        self.hide_limit = template.Variable(hide_limit)
        self.url_dict = kwargs

    def _get_url_query(self, kwargs):
        """Convert a dict to a url query

        kwargs -- a dictionary of params and values as key and values

        """
        if not kwargs:
            return None
        else:
            for k, v in kwargs.items():
                value = self.get_variable(template.Variable(v))
                kwargs[k] = value
        return urllib.urlencode(kwargs)

    def _calculate_paging_limits(self):
        """Define the left and right limit"""
        num_pages = self.page.paginator.num_pages

        left_limit = self.adjacent_pages + self.left_tail_num_pages + (self.hide_limit - 1)
        right_limit = num_pages - (self.hide_limit + self.right_tail_num_pages)

        return left_limit, right_limit
    
    def _get_range_of_pages(self, left_limit, right_limit):
        """Get the range of pages that will be show

        left_limit -- an integer representing the lower limit of pages
        right_limit -- an integer representing the upper limit of pages

        """
        num_pages = self.page.paginator.num_pages

        first_page = max(self.page.number - self.adjacent_pages, 1)
        if first_page <= left_limit:
            first_page = 1
        
        last_page = self.page.number + self.adjacent_pages + 1
        if last_page > right_limit:
            last_page = num_pages + 1

        return [n for n in range(first_page, last_page) if n > 0 and n <= num_pages]

    def _show_left_tail_pages(self, range_pages, max_left_tail):
        """Define if the left tail should be showed on the pagination

        range_pages -- a list of the pages that can be showed
        max_left_tail -- an integer representing the greatest value that should be
            showed on the lower limit
        
        """
        num_pages = self.page.paginator.num_pages
        return (max_left_tail not in range_pages) and (max_left_tail < num_pages)
    
    def _show_right_tail_pages(self, range_pages, min_right_tail, max_left_tail):
        """Define if the right tail shouw be showed on the pagination

        range_pages -- a list of the pages that can be showed
        min_right_tail -- an integer representing the lowest value that should be
            showed on the upper limit
        max_left_tail -- an integer representing the greatest value that should be
            showed on the lower limit
        
        """
        return (min_right_tail not in range_pages) and (min_right_tail > 0) and (min_right_tail > max_left_tail)

    def _set_page_as_page_link(self, page):
        """Convert a page to a PageLink class

        page -- an integer represeting the page

        """
        return PageLink(page, self.url_query)

    def _set_range_as_page_link(self, range):
        """Convert a range of pages to a PageLink class

        range -- a list of pages
        
        """
        return [self._set_page_as_page_link(n) for n in range]
    
    def render(self, context):
        self.context = context

        self.page = self.get_variable('page')
        self.adjacent_pages = int(self.get_variable('adjacent_pages'))
        self.left_tail_num_pages = int(self.get_variable('left_tail_num_pages'))
        self.right_tail_num_pages = int(self.get_variable('right_tail_num_pages'))
        self.hide_limit = int(self.get_variable('hide_limit'))
        self.url_query = self._get_url_query(self.url_dict)

        num_pages = self.page.paginator.num_pages

        left_limit, right_limit = self._calculate_paging_limits()

        range_left_tail = range(1, self.left_tail_num_pages + 2)
        range_right_tail = range(num_pages - self.right_tail_num_pages, num_pages + 1)

        range_pages = self._get_range_of_pages(left_limit, right_limit)

        max_left_tail = max(range_left_tail)
        min_right_tail = min(range_right_tail)

        ctx = {
            'page_': self.page,
            'prev_page': self._set_page_as_page_link(self.page.previous_page_number()) if self.page.has_previous() else None,
            'next_page': self._set_page_as_page_link(self.page.next_page_number()) if self.page.has_next() else None,
            'range_pages': self._set_range_as_page_link(range_pages),
            'range_left_tail': self._set_range_as_page_link(range_left_tail),
            'range_right_tail': self._set_range_as_page_link(range_right_tail),
            'show_left_tail': self._show_left_tail_pages(range_pages, max_left_tail),
            'show_right_tail': self._show_right_tail_pages(range_pages, min_right_tail, max_left_tail),
        }

        return self.to_template('paginate/list_page.html', ctx)

register.tag('paginate', paginate)
