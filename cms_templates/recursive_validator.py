from django.template.debug import DebugLexer, DebugParser
from django.utils.encoding import smart_unicode
from django.template import TemplateEncodingError, \
    TemplateSyntaxError, StringOrigin
from django.template.loader import find_template
from digraph import digraph, find_cycle, AdditionError
from dbtemplates.models import Template
from django.core.exceptions import ValidationError


def handle_recursive_calls(tpl_name, content):
    call_graph = digraph()
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

        #raises ValidationError in case of a cycle
        cycle_test(call_graph, called_tpls)

        visited_templates.extend(called_tpls)
        i += 1


def cycle_test(call_graph, called_tpls):
    for item in called_tpls:
        try:
            call_graph.add_node(item[0])
        except:
            pass

        try:
            #add edge (caller tpl ---> callee tpl), label = extends or include
            call_graph.add_edge((item[2], item[0]), label=item[1])
        except AdditionError:
            pass

    # the list of nodes in case of a cycle
    cycle_items = find_cycle(call_graph)
    if cycle_items:
        msg = format_error_msg(call_graph, cycle_items)
        raise ValidationError(msg)

def format_error_msg(graph, cycle_nodes):
    msg = 'Infinite recursion: ' + str(cycle_nodes)
    # for i in range(len(cycle_nodes)-1):
    #     n1 = cycle_nodes[i]
    #     n2 = cycle_nodes[i + 1]
    #     label = graph.edge_label((n1, n2))
    #     msg += '%s %s %s,' % (n1, label, n2)
    return msg

def get_called_templates(tpl_string, caller):
    try:
        template_string = smart_unicode(tpl_string)
    except UnicodeDecodeError:
        raise TemplateEncodingError("Templates can only be constructed "
                                    "from unicode or UTF-8 strings.")
    origin = StringOrigin(template_string)

    lexer_class, parser_class = DebugLexer, CalledTemplatesParser
    lexer = lexer_class(template_string, origin)
    parser = parser_class(lexer.tokenize())
    return parser.parse(caller)


class CalledTemplatesParser(DebugParser):

    def parse(self, caller):
        called_templates = []
        while self.tokens:
            token = self.next_token()
            if token.token_type == 2: # TOKEN_BLOCK
                try:
                    command = token.contents.split()[0]
                    if command in ['extends', 'include', 'ssi']:
                        callee = self.get_clean_callee(token)
                        called_templates.append((callee, command, caller))
                except IndexError:
                    pass
        return called_templates

    def get_clean_callee(self, token):
        callee = token.contents.split()[1]
        return callee.replace("'", "\"")[1:-1]