#https://pypi.python.org/pypi/python-graph/1.8.2

# Copyright (c) 2008-2009 Pedro Matiello <pmatiello@gmail.com>
#                         Salim Fadhley <sal@stodge.org>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.


from sys import getrecursionlimit, setrecursionlimit


def find_cycle(graph):
    """
    Find a cycle in the given graph.

    This function will return a list of nodes which form a cycle in the graph or an empty list if
    no cycle exists.

    @type graph: graph, digraph
    @param graph: Graph.

    @rtype: list
    @return: List of nodes.
    """
    directed = True

    def find_cycle_to_ancestor(node, ancestor):
        """
        Find a cycle containing both node and ancestor.
        """
        path = []
        while (node != ancestor):
            if (node is None):
                return []
            path.append(node)
            node = spanning_tree[node]
        path.append(node)
        path.reverse()
        return path

    def dfs(node):
        """
        Depth-first search subfunction.
        """
        visited[node] = 1
        # Explore recursively the connected component
        for each in graph[node]:
            if (cycle):
                return
            if (each not in visited):
                spanning_tree[each] = node
                dfs(each)
            else:
                if (directed or spanning_tree[node] != each):
                    cycle.extend(find_cycle_to_ancestor(node, each))

    recursionlimit = getrecursionlimit()
    setrecursionlimit(max(len(graph.nodes())*2,recursionlimit))

    visited = {}              # List for marking visited and non-visited nodes
    spanning_tree = {}        # Spanning tree
    cycle = []

    # Algorithm outer-loop
    for each in graph:
        # Select a non-visited node
        if (each not in visited):
            spanning_tree[each] = None
            # Explore node's connected component
            dfs(each)
            if (cycle):
                setrecursionlimit(recursionlimit)
                return cycle

    setrecursionlimit(recursionlimit)
    return []


class common( object ):
    """
    Standard methods common to all graph classes.

    @sort: __eq__, __getitem__, __iter__, __len__, __repr__, __str__, add_graph, add_nodes,
    add_spanning_tree, complete, inverse, order, reverse
    """

    def __str__(self):
        """
        Return a string representing the graph when requested by str() (or print).

        @rtype:  string
        @return: String representing the graph.
        """
        str_nodes = repr( self.nodes() )
        str_edges = repr( self.edges() )
        return "%s %s" % ( str_nodes, str_edges )

    def __repr__(self):
        """
        Return a string representing the graph when requested by repr()

        @rtype:  string
        @return: String representing the graph.
        """
        return "<%s.%s %s>" % ( self.__class__.__module__, self.__class__.__name__, str(self) )

    def __iter__(self):
        """
        Return a iterator passing through all nodes in the graph.

        @rtype:  iterator
        @return: Iterator passing through all nodes in the graph.
        """
        for n in self.nodes():
            yield n

    def __len__(self):
        """
        Return the order of self when requested by len().

        @rtype:  number
        @return: Size of the graph.
        """
        return self.order()

    def __getitem__(self, node):
        """
        Return a iterator passing through all neighbors of the given node.

        @rtype:  iterator
        @return: Iterator passing through all neighbors of the given node.
        """
        for n in self.neighbors( node ):
            yield n

    def order(self):
        """
        Return the order of self, this is defined as the number of nodes in the graph.

        @rtype:  number
        @return: Size of the graph.
        """
        return len(self.nodes())

    def add_nodes(self, nodelist):
        """
        Add given nodes to the graph.

        @attention: While nodes can be of any type, it's strongly recommended to use only
        numbers and single-line strings as node identifiers if you intend to use write().
        Objects used to identify nodes absolutely must be hashable. If you need attach a mutable
        or non-hashable node, consider using the labeling feature.

        @type  nodelist: list
        @param nodelist: List of nodes to be added to the graph.
        """
        for each in nodelist:
            self.add_node(each)

    def add_graph(self, other):
        """
        Add other graph to this graph.

        @attention: Attributes and labels are not preserved.

        @type  other: graph
        @param other: Graph
        """
        self.add_nodes( n for n in other.nodes() if not n in self.nodes() )

        for each_node in other.nodes():
            for each_edge in other.neighbors(each_node):
                if (not self.has_edge((each_node, each_edge))):
                    self.add_edge((each_node, each_edge))


    def add_spanning_tree(self, st):
        """
        Add a spanning tree to the graph.

        @type  st: dictionary
        @param st: Spanning tree.
        """
        self.add_nodes(list(st.keys()))
        for each in st:
            if (st[each] is not None):
                self.add_edge((st[each], each))


    def complete(self):
        """
        Make the graph a complete graph.

        @attention: This will modify the current graph.
        """
        for each in self.nodes():
            for other in self.nodes():
                if (each != other and not self.has_edge((each, other))):
                    self.add_edge((each, other))


    def inverse(self):
        """
        Return the inverse of the graph.

        @rtype:  graph
        @return: Complement graph for the graph.
        """
        inv = self.__class__()
        inv.add_nodes(self.nodes())
        inv.complete()
        for each in self.edges():
            if (inv.has_edge(each)):
                inv.del_edge(each)
        return inv

    def reverse(self):
        """
        Generate the reverse of a directed graph, returns an identical graph if not directed.
        Attributes & weights are preserved.

        @rtype: digraph
        @return: The directed graph that should be reversed.
        """
        assert self.DIRECTED, "Undirected graph types such as %s cannot be reversed" % self.__class__.__name__

        N = self.__class__()

        #- Add the nodes
        N.add_nodes( n for n in self.nodes() )

        #- Add the reversed edges
        for (u, v) in self.edges():
            wt = self.edge_weight((u, v))
            label = self.edge_label((u, v))
            attributes = self.edge_attributes((u, v))
            N.add_edge((v, u), wt, label, attributes)
        return N

    def __eq__(self, other):
        """
        Return whether this graph is equal to another one.

        @type other: graph, digraph
        @param other: Other graph or digraph

        @rtype: boolean
        @return: Whether this graph and the other are equal.
        """

        def nodes_eq():
            for each in self:
                if (not other.has_node(each)): return False
            for each in other:
                if (not self.has_node(each)): return False
            return True

        def edges_eq():
            for edge in self.edges():
                    if (not other.has_edge(edge)): return False
            for edge in other.edges():
                    if (not self.has_edge(edge)): return False
            return True

        try:
            return nodes_eq() and edges_eq()
        except AttributeError:
            return False


class labeling( object ):
    """
    Generic labeling support for graphs

    @sort: __eq__, __init__, add_edge_attribute, add_edge_attributes, add_node_attribute,
    del_edge_labeling, del_node_labeling, edge_attributes, edge_label, edge_weight,
    get_edge_properties, node_attributes, set_edge_label, set_edge_properties, set_edge_weight
    """
    WEIGHT_ATTRIBUTE_NAME = "weight"
    DEFAULT_WEIGHT = 1

    LABEL_ATTRIBUTE_NAME = "label"
    DEFAULT_LABEL = ""

    def __init__(self):
        # Metadata bout edges
        self.edge_properties = {}    # Mapping: Edge -> Dict mapping, lablel-> str, wt->num
        self.edge_attr = {}          # Key value pairs: (Edge -> Attributes)

        # Metadata bout nodes
        self.node_attr = {}          # Pairing: Node -> Attributes

    def del_node_labeling( self, node ):
        if node in self.node_attr:
            # Since attributes and properties are lazy, they might not exist.
            del( self.node_attr[node] )

    def del_edge_labeling( self, edge ):

        keys = [edge]
        if not self.DIRECTED:
            keys.append(edge[::-1])

        for key in keys:
            for mapping in [self.edge_properties, self.edge_attr ]:
                try:
                    del ( mapping[key] )
                except KeyError:
                    pass

    def edge_weight(self, edge):
        """
        Get the weight of an edge.

        @type  edge: edge
        @param edge: One edge.

        @rtype:  number
        @return: Edge weight.
        """
        return self.get_edge_properties( edge ).setdefault( self.WEIGHT_ATTRIBUTE_NAME, self.DEFAULT_WEIGHT )


    def set_edge_weight(self, edge, wt):
        """
        Set the weight of an edge.

        @type  edge: edge
        @param edge: One edge.

        @type  wt: number
        @param wt: Edge weight.
        """
        self.set_edge_properties(edge, weight=wt )
        if not self.DIRECTED:
            self.set_edge_properties((edge[1], edge[0]) , weight=wt )


    def edge_label(self, edge):
        """
        Get the label of an edge.

        @type  edge: edge
        @param edge: One edge.

        @rtype:  string
        @return: Edge label
        """
        return self.get_edge_properties( edge ).setdefault( self.LABEL_ATTRIBUTE_NAME, self.DEFAULT_LABEL )

    def set_edge_label(self, edge, label):
        """
        Set the label of an edge.

        @type  edge: edge
        @param edge: One edge.

        @type  label: string
        @param label: Edge label.
        """
        self.set_edge_properties(edge, label=label )
        if not self.DIRECTED:
            self.set_edge_properties((edge[1], edge[0]) , label=label )

    def set_edge_properties(self, edge, **properties ):
        self.edge_properties.setdefault( edge, {} ).update( properties )
        if (not self.DIRECTED and edge[0] != edge[1]):
            self.edge_properties.setdefault((edge[1], edge[0]), {}).update( properties )

    def get_edge_properties(self, edge):
        return self.edge_properties.setdefault( edge, {} )

    def add_edge_attribute(self, edge, attr):
        """
        Add attribute to the given edge.

        @type  edge: edge
        @param edge: One edge.

        @type  attr: tuple
        @param attr: Node attribute specified as a tuple in the form (attribute, value).
        """
        self.edge_attr[edge] = self.edge_attributes(edge) + [attr]

        if (not self.DIRECTED and edge[0] != edge[1]):
            self.edge_attr[(edge[1],edge[0])] = self.edge_attributes((edge[1], edge[0])) + [attr]

    def add_edge_attributes(self, edge, attrs):
        """
        Append a sequence of attributes to the given edge

        @type  edge: edge
        @param edge: One edge.

        @type  attrs: tuple
        @param attrs: Node attributes specified as a sequence of tuples in the form (attribute, value).
        """
        for attr in attrs:
            self.add_edge_attribute(edge, attr)


    def add_node_attribute(self, node, attr):
        """
        Add attribute to the given node.

        @type  node: node
        @param node: Node identifier

        @type  attr: tuple
        @param attr: Node attribute specified as a tuple in the form (attribute, value).
        """
        self.node_attr[node] = self.node_attr[node] + [attr]


    def node_attributes(self, node):
        """
        Return the attributes of the given node.

        @type  node: node
        @param node: Node identifier

        @rtype:  list
        @return: List of attributes specified tuples in the form (attribute, value).
        """
        return self.node_attr[node]


    def edge_attributes(self, edge):
        """
        Return the attributes of the given edge.

        @type  edge: edge
        @param edge: One edge.

        @rtype:  list
        @return: List of attributes specified tuples in the form (attribute, value).
        """
        try:
            return self.edge_attr[edge]
        except KeyError:
            return []

    def __eq__(self, other):
        """
        Return whether this graph is equal to another one.

        @type other: graph, digraph
        @param other: Other graph or digraph

        @rtype: boolean
        @return: Whether this graph and the other are equal.
        """
        def attrs_eq(list1, list2):
            for each in list1:
                if (each not in list2): return False
            for each in list2:
                if (each not in list1): return False
            return True

        def edges_eq():
            for edge in self.edges():
                if (self.edge_weight(edge) != other.edge_weight(edge)): return False
                if (self.edge_label(edge) != other.edge_label(edge)): return False
                if (not attrs_eq(self.edge_attributes(edge), other.edge_attributes(edge))): return False
            return True

        def nodes_eq():
            for node in self:
                if (not attrs_eq(self.node_attributes(node), other.node_attributes(node))): return False
            return True


"""
Exceptions.
"""

# Graph errors

class GraphError(RuntimeError):
    """
    A base-class for the various kinds of errors that occur in the the python-graph class.
    """
    pass

class AdditionError(GraphError):
    """
    This error is raised when trying to add a node or edge already added to the graph or digraph.
    """
    pass

class NodeUnreachable(GraphError):
    """
    Goal could not be reached from start.
    """
    def __init__(self, start, goal):
        msg = "Node %s could not be reached from node %s" % ( repr(goal), repr(start) )
        InvalidGraphType.__init__(self, msg)
        self.start = start
        self.goal = goal

class InvalidGraphType(GraphError):
    """
    Invalid graph type.
    """
    pass

# Algorithm errors

class AlgorithmError(RuntimeError):
    """
    A base-class for the various kinds of errors that occur in the the
    algorithms package.
    """
    pass

class NegativeWeightCycleError(AlgorithmError):
    """
    Algorithms like the Bellman-Ford algorithm can detect and raise an exception
    when they encounter a negative weight cycle.

    @see: pygraph.algorithms.shortest_path_bellman_ford
    """
    pass


# Copyright (c) 2007-2009 Pedro Matiello <pmatiello@gmail.com>
#                         Christian Muise <christian.muise@gmail.com>
#                         Johannes Reinhardt <jreinhardt@ist-dein-freund.de>
#                         Nathan Davis <davisn90210@gmail.com>
#                         Zsolt Haraszti <zsolt@drawwell.net>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.


class basegraph( object ):
    """
    An abstract class intended as a common ancestor to all graph classes. This allows the user
    to test isinstance(X, basegraph) to determine if the object is one of any of the python-graph
    main classes.
    """


class digraph (basegraph, common, labeling):
    """
    Digraph class.

    Digraphs are built of nodes and directed edges.

    @sort: __eq__, __init__, __ne__, add_edge, add_node, del_edge, del_node, edges, has_edge, has_node,
    incidents, neighbors, node_order, nodes
    """

    DIRECTED = True

    def __init__(self):
        """
        Initialize a digraph.
        """
        common.__init__(self)
        labeling.__init__(self)
        self.node_neighbors = {}     # Pairing: Node -> Neighbors
        self.node_incidence = {}     # Pairing: Node -> Incident nodes


    def nodes(self):
        """
        Return node list.

        @rtype:  list
        @return: Node list.
        """
        return list(self.node_neighbors.keys())


    def neighbors(self, node):
        """
        Return all nodes that are directly accessible from given node.

        @type  node: node
        @param node: Node identifier

        @rtype:  list
        @return: List of nodes directly accessible from given node.
        """
        return self.node_neighbors[node]


    def incidents(self, node):
        """
        Return all nodes that are incident to the given node.

        @type  node: node
        @param node: Node identifier

        @rtype:  list
        @return: List of nodes directly accessible from given node.
        """
        return self.node_incidence[node]

    def edges(self):
        """
        Return all edges in the graph.

        @rtype:  list
        @return: List of all edges in the graph.
        """
        return [ a for a in self._edges() ]

    def _edges(self):
        for n, neighbors in self.node_neighbors.items():
            for neighbor in neighbors:
                yield (n, neighbor)

    def has_node(self, node):
        """
        Return whether the requested node exists.

        @type  node: node
        @param node: Node identifier

        @rtype:  boolean
        @return: Truth-value for node existence.
        """
        return node in self.node_neighbors

    def add_node(self, node, attrs = None):
        """
        Add given node to the graph.

        @attention: While nodes can be of any type, it's strongly recommended to use only
        numbers and single-line strings as node identifiers if you intend to use write().

        @type  node: node
        @param node: Node identifier.

        @type  attrs: list
        @param attrs: List of node attributes specified as (attribute, value) tuples.
        """
        if attrs is None:
            attrs = []
        if (node not in self.node_neighbors):
            self.node_neighbors[node] = []
            self.node_incidence[node] = []
            self.node_attr[node] = attrs
        else:
            raise AdditionError("Node %s already in digraph" % node)


    def add_edge(self, edge, wt = 1, label="", attrs = []):
        """
        Add an directed edge to the graph connecting two nodes.

        An edge, here, is a pair of nodes like C{(n, m)}.

        @type  edge: tuple
        @param edge: Edge.

        @type  wt: number
        @param wt: Edge weight.

        @type  label: string
        @param label: Edge label.

        @type  attrs: list
        @param attrs: List of node attributes specified as (attribute, value) tuples.
        """
        u, v = edge
        for n in [u,v]:
            if not n in self.node_neighbors:
                raise AdditionError( "%s is missing from the node_neighbors table" % n )
            if not n in self.node_incidence:
                raise AdditionError( "%s is missing from the node_incidence table" % n )

        if v in self.node_neighbors[u] and u in self.node_incidence[v]:
            raise AdditionError("Edge (%s, %s) already in digraph" % (u, v))
        else:
            self.node_neighbors[u].append(v)
            self.node_incidence[v].append(u)
            self.set_edge_weight((u, v), wt)
            self.add_edge_attributes( (u, v), attrs )
            self.set_edge_properties( (u, v), label=label, weight=wt )


    def del_node(self, node):
        """
        Remove a node from the graph.

        @type  node: node
        @param node: Node identifier.
        """
        for each in list(self.incidents(node)):
            # Delete all the edges incident on this node
            self.del_edge((each, node))

        for each in list(self.neighbors(node)):
            # Delete all the edges pointing to this node.
            self.del_edge((node, each))

        # Remove this node from the neighbors and incidents tables
        del(self.node_neighbors[node])
        del(self.node_incidence[node])

        # Remove any labeling which may exist.
        self.del_node_labeling( node )


    def del_edge(self, edge):
        """
        Remove an directed edge from the graph.

        @type  edge: tuple
        @param edge: Edge.
        """
        u, v = edge
        self.node_neighbors[u].remove(v)
        self.node_incidence[v].remove(u)
        self.del_edge_labeling( (u,v) )


    def has_edge(self, edge):
        """
        Return whether an edge exists.

        @type  edge: tuple
        @param edge: Edge.

        @rtype:  boolean
        @return: Truth-value for edge existence.
        """
        u, v = edge
        return (u, v) in self.edge_properties


    def node_order(self, node):
        """
        Return the order of the given node.

        @rtype:  number
        @return: Order of the given node.
        """
        return len(self.neighbors(node))

    def __eq__(self, other):
        """
        Return whether this graph is equal to another one.

        @type other: graph, digraph
        @param other: Other graph or digraph

        @rtype: boolean
        @return: Whether this graph and the other are equal.
        """
        return common.__eq__(self, other) and labeling.__eq__(self, other)

    def __ne__(self, other):
        """
        Return whether this graph is not equal to another one.

        @type other: graph, digraph
        @param other: Other graph or digraph

        @rtype: boolean
        @return: Whether this graph and the other are different.
        """
        return not (self == other)
