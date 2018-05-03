import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx
from itertools import islice
import numpy as np

number_of_servers = 686
number_of_switch_ports = 50  # k
switch_graph_degree = 50 - 14  # r
number_of_racks = int(np.ceil(number_of_servers / (number_of_switch_ports - switch_graph_degree)))  # N
number_of_servers_in_rack = number_of_switch_ports - switch_graph_degree
shortest_path_k = 8

G = nx.random_regular_graph(switch_graph_degree, number_of_racks)

sender_to_receiver = np.random.permutation(number_of_racks)  # sender_to_receiver[i] = j <=> i sends message to j

for node1 in range(len(sender_to_receiver)):
    node2 = sender_to_receiver[node1]
    shortest_paths = list(nx.shortest_simple_paths(G, node1, node2))
    chosen_path = shortest_paths[np.random.randint(min(shortest_path_k, len(shortest_paths)))]
    for i in range(len(chosen_path) - 1):
        if 'count' not in G[chosen_path[i]][chosen_path[i + 1]]:
            G[chosen_path[i]][chosen_path[i + 1]]['count'] = 0
        G[chosen_path[i]][chosen_path[i + 1]]['count'] += 1

count = nx.get_edge_attributes(G, 'count')
edge_to_count = dict(count)
sorted_edges = sorted(edge_to_count, key=edge_to_count.get)

y_axis = []
for e in sorted_edges:
    y_axis.append(edge_to_count[e])
    
plt.plot(range(len(y_axis)), y_axis)
plt.savefig("1.svg")

plt.plot()
pos = nx.spring_layout(G)
nx.draw(G, pos=pos, with_labels=True)
nx.draw_networkx_edge_labels(G, pos=pos, labels=nx.get_edge_attributes(G, 'count'))
plt.savefig("2.svg")

