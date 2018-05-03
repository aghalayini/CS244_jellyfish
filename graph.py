import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx
from itertools import islice
import numpy as np


def ECMP_last_index(shortest_paths, n):
    for i in range(min(n, len(shortest_paths)) - 1):
        if len(shortest_paths[i]) != len(shortest_paths[i + 1]):
            return i
    return n - 1


number_of_servers = 686
switch_graph_degree = 14  # k
number_of_racks = 5600 // switch_graph_degree

number_of_servers_in_rack = int(np.ceil(number_of_servers / number_of_racks))
number_of_switch_ports = number_of_servers_in_rack + switch_graph_degree  # r
shortest_path_k = 8

G = nx.random_regular_graph(switch_graph_degree, number_of_racks)

print("number_of_servers_in_rack = " + str(number_of_servers_in_rack))
print("number_of_switch_ports = " + str(number_of_switch_ports))
print("RRG has " + str(number_of_racks) + " nodes with degree " + str(switch_graph_degree) + " and " + str(G.number_of_edges()) + " edges")

sender_to_receiver = np.random.permutation(number_of_servers)  # sender_to_receiver[i] = j <=> i sends message to j

for e in G.edges():
    G.edges[e]['k_count'] = 0
    G.edges[e]['ecmp8_count'] = 0
    G.edges[e]['ecmp64_count'] = 0

for sender in range(len(sender_to_receiver)):
    receiver = sender_to_receiver[sender]
    node1 = sender // number_of_servers_in_rack
    node2 = receiver // number_of_servers_in_rack
    # print(node1, node2)
    shortest_paths = list(islice(nx.shortest_simple_paths(G, node1, node2), 64))
    k_shortest_paths = islice(shortest_paths, shortest_path_k)
    ecmp8 = islice(shortest_paths, ECMP_last_index(shortest_paths, 8) + 1)
    ecmp64 = islice(shortest_paths, ECMP_last_index(shortest_paths, 64) + 1)
    for path in k_shortest_paths:
        for i in range(len(path) - 1):
            G[path[i]][path[i + 1]]['k_count'] += 1
            
    for path in ecmp8:
        for i in range(len(path) - 1):
            G[path[i]][path[i + 1]]['ecmp8_count'] += 1
            
    for path in ecmp64:
        for i in range(len(path) - 1):
            G[path[i]][path[i + 1]]['ecmp64_count'] += 1

y_axis = {"k":[], "ecmp8":[], "ecmp64": []}

count = nx.get_edge_attributes(G, 'k_count')
edge_to_count = dict(count)
sorted_edges = sorted(edge_to_count, key=edge_to_count.get)
print("sorted_edges: " + str(len(sorted_edges)))

for e in sorted_edges:
    y_axis['k'].append(edge_to_count[e])
    
count = nx.get_edge_attributes(G, 'ecmp8_count')
edge_to_count = dict(count)
sorted_edges = sorted(edge_to_count, key=edge_to_count.get)
print("sorted_edges: " + str(len(sorted_edges)))

for e in sorted_edges:
    y_axis['ecmp8'].append(edge_to_count[e])
    
count = nx.get_edge_attributes(G, 'ecmp64_count')
edge_to_count = dict(count)
sorted_edges = sorted(edge_to_count, key=edge_to_count.get)
print("sorted_edges: " + str(len(sorted_edges)))

for e in sorted_edges:
    y_axis['ecmp64'].append(edge_to_count[e])

plt.figure()
x_axis = range(len(y_axis['k']))
plt.yticks(range(int(min(y_axis['k'])), 1 + int(np.ceil(max(y_axis['k'])))))
plt.ylim(int(min(y_axis['k'])), 1 + int(np.ceil(max(y_axis['k']))))
plt.plot(x_axis, y_axis['k'])
plt.plot(x_axis, y_axis['ecmp8'])
plt.plot(x_axis, y_axis['ecmp64'])
plt.savefig("1.svg")

plt.figure()
pos = nx.spring_layout(G)
nx.draw(G, pos=pos, with_labels=False, node_size=1, width=0.1)
# nx.draw_networkx_edge_labels(G, pos=pos, labels=nx.get_edge_attributes(G, 'count'))
plt.savefig("2.svg")
plt.show()
