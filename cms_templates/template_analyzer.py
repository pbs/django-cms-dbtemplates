from django.template.loader_tags import (ConstantIncludeNode,
                                         ExtendsNode, BlockNode)
from sekizai.templatetags.sekizai_tags import RenderBlock
from sekizai.helpers import is_variable_extend_node
from django.template import VariableNode, NodeList


def _extend_blocks(extend_node, blocks):
    """
    Extends the dictionary `blocks` with *new* blocks in the parent node (recursive)
    """
    # we don't support variable extensions
    if is_variable_extend_node(extend_node):
        return
    parent = extend_node.get_parent(None)
    # Search for new blocks
    for node in parent.nodelist.get_nodes_by_type(BlockNode):
        if not node.name in blocks:
            blocks[node.name] = node
        else:
            # set this node as the super node (for {{ block.super }})
            block = blocks[node.name]
            seen_supers = []
            while hasattr(block.super, 'nodelist') and block.super not in seen_supers:
                seen_supers.append(block.super)
                block = block.super
            block.super = node
    # search for further ExtendsNodes
    for node in parent.nodelist.get_nodes_by_type(ExtendsNode):
        _extend_blocks(node, blocks)
        break


# modified _extend_nodelist from sekizai.helpers
def _extend_nodelist(extend_node):

    if is_variable_extend_node(extend_node):
        return []

    blocks = extend_node.blocks
    _extend_blocks(extend_node, blocks)

    found = []
    for block in blocks.values():
        found += get_all_templates_used(block.nodelist, block, blocks.keys())

    parent_template = extend_node.get_parent({})
    if not parent_template.nodelist.get_nodes_by_type(ExtendsNode):
        found += get_all_templates_used(
            parent_template.nodelist, None, blocks.keys())
    else:
        found += get_all_templates_used(
            parent_template.nodelist, extend_node, blocks.keys())

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
        if isinstance(node, ConstantIncludeNode) and node.template:
            found.append(node.template.name)
            found += get_all_templates_used(node.template.nodelist)
        elif isinstance(node, ExtendsNode):
            found.append(node.get_parent(None).name)
            found += _extend_nodelist(node)
        elif isinstance(node, RenderBlock):
            node.kwargs['name'].resolve({})
            found += get_all_templates_used(node.blocks['nodelist'], node)
        elif (isinstance(node, VariableNode) and current_block and
              node.filter_expression.token == 'block.super' and
              hasattr(current_block.super, 'nodelist')):
            found += get_all_templates_used(
                current_block.super.nodelist, current_block.super)
        elif isinstance(node, BlockNode) and node.name in ignore_blocks:
            continue
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
