from django.template.loader_tags import (IncludeNode,
                                         ExtendsNode, BlockNode)
from sekizai.templatetags.sekizai_tags import RenderBlock
from sekizai.helpers import (
    is_variable_extend_node, _extend_blocks, FAKE_CONTEXT)
from django.template.base import VariableNode, NodeList, Variable
from menus.templatetags.menu_tags import ShowMenu, ShowSubMenu, ShowBreadcrumb
from django.template.loader import get_template


def _get_nodelist(tpl):
    if hasattr(tpl, 'template'):
        return tpl.template.nodelist
    else:
        return tpl.nodelist


# modified _extend_nodelist from sekizai.helpers
def _extend_nodelist(extend_node):

    if is_variable_extend_node(extend_node):
        return []

    blocks = extend_node.blocks
    _extend_blocks(extend_node, blocks)

    found = []
    for block in blocks.values():
        found += get_all_templates_used(block.nodelist, block)

    parent_template = extend_node.get_parent(FAKE_CONTEXT)
    if not _get_nodelist(parent_template).get_nodes_by_type(ExtendsNode):
        found += get_all_templates_used(
            _get_nodelist(parent_template), None)
    else:
        found += get_all_templates_used(
            _get_nodelist(parent_template), extend_node)

    return found


def _scan_nodelist(subnodelist, node, block):
    if isinstance(subnodelist, NodeList):
        if isinstance(node, BlockNode):
            block = node
        return get_all_templates_used(subnodelist, block), block
    return [], block


# modified _scan_placeholders from cms.utils.plugins
def get_all_templates_used(nodelist, current_block=None, ignore_blocks=None):
    if ignore_blocks is None:
        ignore_blocks = []

    found = []
    for node in nodelist:
        if isinstance(node, IncludeNode) and node.template:

            # This is required for Django 1.7 but works on older version too
            # Check if it quacks like a template object, if not
            # presume is a template path and get the object out of it
            if not callable(getattr(node.template, 'render', None)):
                # If it's a variable there is no way to expand it at this stage so we
                # need to skip it
                if isinstance(node.template.var, Variable):
                    continue
                else:
                    template = get_template(node.template.var)
            else:
                template = node.template
            if not hasattr(template, 'name'):
                template = template.template
            found.append(template.name)
            found += get_all_templates_used(_get_nodelist(template))
        elif isinstance(node, ExtendsNode):
            template = node.get_parent(FAKE_CONTEXT)
            if not hasattr(template, 'name'):
                template = template.template
            found.append(template.name)
            found += _extend_nodelist(node)
            if hasattr(node, 'child_nodelists'):
                for child_lst in node.child_nodelists:
                    _found_to_add, current_block = _scan_nodelist(
                        getattr(node, child_lst, ''), node, current_block)
                    found += _found_to_add
        elif isinstance(node, RenderBlock):
            node.kwargs['name'].resolve({})
            found += get_all_templates_used(node.blocks['nodelist'], node)
        elif (isinstance(node, VariableNode) and current_block and
              node.filter_expression.token == 'block.super' and
              hasattr(current_block.super, 'nodelist')):
            found += get_all_templates_used(
                _get_nodelist(current_block.super), current_block.super)
        elif isinstance(node, BlockNode) and node.name in ignore_blocks:
            continue
        elif (isinstance(node, ShowMenu) or isinstance(node, ShowSubMenu) or
              isinstance(node, ShowBreadcrumb)):
            menu_template_node = node.kwargs.get('template', None)
            if menu_template_node and hasattr(menu_template_node, 'var'):
                menu_template_name = menu_template_node.var.resolve({})
                if menu_template_name:
                    found.append(menu_template_name)
                    compiled_template = get_template(menu_template_name)
                    found += get_all_templates_used(_get_nodelist(compiled_template))
        elif hasattr(node, 'child_nodelists'):
            for child_lst in node.child_nodelists:
                _found_to_add, current_block = _scan_nodelist(
                    getattr(node, child_lst, ''), node, current_block)
                found += _found_to_add
        else:
            for attr in dir(node):
                _found_to_add, current_block = _scan_nodelist(
                    getattr(node, attr), node, current_block)
                found += _found_to_add
    return found
