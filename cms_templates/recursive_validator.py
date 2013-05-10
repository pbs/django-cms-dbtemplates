from django.template.debug import DebugLexer, DebugParser
from django.utils.encoding import smart_unicode
from django.template import TemplateEncodingError, \
    TemplateSyntaxError, StringOrigin
from django.template.loader import find_template
from digraph import digraph, find_cycle, AdditionError
from dbtemplates.models import Template


class InfiniteRecursivityError(Exception):

    def __init__(self, cycle_items, graph):
        self.cycle_items = cycle_items
        self.graph = graph


def handle_recursive_calls(tpl_name, content):
    # create the call graph as a directed graph
    call_graph = digraph()

    # visited_templates items will look like this:
    # [("tpl1", "extends", "tpl2"), ...]
    visited_templates = [(tpl_name, '', '')]

    call_graph.add_node(tpl_name)
    i = 0
    while i < len(visited_templates):
        name = visited_templates[i][0]
        try:
            tpl_content = content if i == 0 else Template.objects.get(name=name).content
        except:
            i += 1
            continue

        called_tpls = get_called_templates(tpl_content, name)
        update_call_graph(call_graph, called_tpls)

        #raises InfiniteRecursivityError in case of a cycle
        cycle_test(call_graph, called_tpls)

        visited_templates.extend(called_tpls)
        i += 1


def update_call_graph(call_graph, called_tpls):
    for item in called_tpls:
        try:
            #add callee node to graph
            call_graph.add_node(item[0])
        except:
            pass

        try:
            #add edge (caller tpl ---> callee tpl), label=extends, include, etc
            call_graph.add_edge((item[2], item[0]), label=item[1])
        except AdditionError:
            pass


def cycle_test(call_graph, called_tpls):
    # the list of nodes in case of a cycle
    cycle_items = find_cycle(call_graph)
    if cycle_items:
        raise InfiniteRecursivityError(cycle_items, call_graph)


def format_recursive_msg(tpl_name, e):
    tpl_name_index = e.cycle_items.index(tpl_name) \
                     if tpl_name in e.cycle_items else 0
    msg = ''
    for i in range(len(e.cycle_items)):
        n1 = e.cycle_items[(tpl_name_index + i) % len(e.cycle_items)]
        n2 = e.cycle_items[(tpl_name_index + i + 1) % len(e.cycle_items)]
        label = e.graph.edge_label((n1, n2))
        msg += '<%s> uses (%s) <%s>, ' % (n1, label, n2)
    return msg


def get_called_templates(tpl_string, caller):
    template_string = smart_unicode(tpl_string)
    origin = StringOrigin(template_string)
    lexer = DebugLexer(template_string, origin)
    parser = CalledTemplatesParser(lexer.tokenize())
    return parser.parse(caller)


class CalledTemplatesParser(DebugParser):

    def parse(self, caller):
        called_templates = []
        while self.tokens:
            token = self.next_token()
            if token.token_type == 2: # TOKEN_BLOCK
                command = token.split_contents()[0]
                callee = ''
                if command == 'load':
                    #load tag needs to be compiled so that the extra tags
                    # (like the ones for menu) can be recognized later as tokens
                    compile_func = self.tags[command]
                    compile_func(self, token)
                elif command in ['extends', 'include', 'ssi']:
                    callee = self.clean_callee(token.contents.split()[1])
                elif command in ['show_menu', 'show_menu_below_id',
                                 'show_sub_menu', 'show_breadcrumb']:
                    compile_func = self.tags[command]
                    compiled_result = compile_func(self, token)
                    callee = compiled_result.kwargs['template'].literal
                    callee = self.clean_callee(callee)
                if callee:
                    called_templates.append((callee, command, caller))

        return called_templates

    def clean_callee(self, callee):
        return callee.replace("'", "\"")[1:-1]
