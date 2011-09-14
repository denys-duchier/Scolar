# essai pydot (bug ?)
# EV, sept 2011

import pydot

print 'pydot version:', pydot.__version__

g = pydot.Dot('graphname')
g.add_node(pydot.Node('a'))
g.add_node(pydot.Node('b'))


n = g.get_node('a')

print n
print 'nodes names = %s' % [ x.get_name() for x in g.get_node_list() ]

edges = [ ('a','b'), ('b','c'), ('c','d') ] 
g = pydot.graph_from_edges(edges)
print 'nodes names = %s' % [ x.get_name() for x in g.get_node_list() ]

if not len(g.get_node_list()):
    print 'bug: empty node list !' # incompatibility versions python / pydot 

# Les fleches ?
for (src_id, dst_id) in edges:
    e = g.get_edge(src_id, dst_id)
    e.set('arrowhead', 'normal')
    e.set( 'arrowsize', 2 )
    e.set_label( str( (src_id, dst_id) ) )
    e.set_fontname('Helvetica')
    e.set_fontsize(8.0)

g.write_jpeg('/tmp/graph_from_edges_dot.jpg', prog='dot') # ok sur ScoDoc / Debian 5, pas de fleches en Debian 6
# cf https://www-lipn.univ-paris13.fr/projects/scodoc/ticket/190


