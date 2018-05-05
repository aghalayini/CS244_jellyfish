import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx
from itertools import islice
import numpy as np
import random


class NXTopology:
    
    def __init__(self, number_of_servers=686, switch_graph_degree=14, number_of_links=2800, labels=['k_count', 'ecmp8_count', 'ecmp64_count']):
        self.number_of_servers = number_of_servers
        self.switch_graph_degree = switch_graph_degree  # k
        self.number_of_racks = (2 * number_of_links) // self.switch_graph_degree
        
        self.number_of_servers_in_rack = int(np.ceil(float(self.number_of_servers) / self.number_of_racks))
        self.number_of_switch_ports = self.number_of_servers_in_rack + self.switch_graph_degree  # r
        self.shortest_path_k = 8
        
        self.G = nx.random_regular_graph(self.switch_graph_degree, self.number_of_racks)
        self.sender_to_receiver = self.random_derangement(self.number_of_servers)  # sender_to_receiver[i] = j <=> i sends message to j
        
        for label in labels:
            for e in self.G.edges():
                self.G[e[0]][e[1]][label] = 0
        
        print("number_of_servers_in_rack = " + str(self.number_of_servers_in_rack))
        print("number_of_switch_ports = " + str(self.number_of_switch_ports))
        print("RRG has " + str(self.number_of_racks) + " nodes with degree " + str(self.switch_graph_degree) + " and " + str(self.G.number_of_edges()) + " edges")

    def random_derangement(self, n):
        while True:
            array = range(n)
            for i in range(n - 1, -1, -1):
                p = random.randint(0, i)
                if array[p] == i:
                    break
                else:
                    array[i], array[p] = array[p], array[i]
            else:
                if array[0] != 0:
                    return array

    def ECMP_last_index(self, shortest_paths, n):
        for i in range(min(n, len(shortest_paths)) - 1):
            if len(shortest_paths[i]) != len(shortest_paths[i + 1]):
                return i
        return n - 1
    
    def get_rack_index(self, server_index):
        return server_index % self.number_of_racks
    
    def add_to_edge_label(self, chosen_paths, label):
        s = set()
        for path in chosen_paths:
            for i in range(len(path) - 1):
                if (path[i],path[i + 1]) not in s:
                    #s.add((path[i],path[i + 1]))
                    self.G[path[i]][path[i + 1]][label] += 1
    
    def calculate_all_paths(self):
        for sender in range(len(self.sender_to_receiver)):
            receiver = self.sender_to_receiver[sender]
            node1 = self.get_rack_index(sender)
            node2 = self.get_rack_index(receiver)
            # print(node1, node2)
            shortest_paths = list(islice(nx.shortest_simple_paths(self.G, node1, node2), 64))
            k_shortest_paths = islice(shortest_paths, self.shortest_path_k)
            ecmp8 = islice(shortest_paths, self.ECMP_last_index(shortest_paths, 8) + 1)
            ecmp64 = islice(shortest_paths, self.ECMP_last_index(shortest_paths, 64) + 1)
                        
            self.add_to_edge_label(k_shortest_paths, 'k_count')
            self.add_to_edge_label(ecmp8, 'ecmp8_count')
            self.add_to_edge_label(ecmp64, 'ecmp64_count')
    
    def to_y_axis(self, label):
        ret = []
        count = nx.get_edge_attributes(self.G, label)
        edge_to_count = dict(count)
        sorted_edges = sorted(edge_to_count, key=edge_to_count.get)
        print("sorted_edges: " + str(len(sorted_edges)))
    
        for e in sorted_edges:
            ret.append(edge_to_count[e])
            
        return ret
    
    def draw_fig9(self, y_axes):
        keys = y_axes.keys()
        m = 0
        for k in keys:
            m = max(m, max(y_axes[k]))
        plt.figure()
        x_axis = range(len(y_axes[keys[0]]))
        plt.yticks(range(m + 1))
        plt.ylim(0, m + 1)
        plt.xlim(0, 3000)
        
        for k in keys:
            plt.plot(x_axis, y_axes[k], label=k)
        plt.legend()
        plt.savefig("1.svg")
        
        plt.figure()
        pos = nx.spring_layout(self.G)
        nx.draw(self.G, pos=pos, with_labels=False, node_size=1, width=0.1)
        # nx.draw_networkx_edge_labels(G, pos=pos, labels=nx.get_edge_attributes(G, 'count'))
        plt.savefig("2.svg")
        plt.show()


if __name__ == "__main__":
    t = NXTopology()
    
    t.calculate_all_paths()
    y_axes = {'k_count':t.to_y_axis('k_count'), 'ecmp8_count':t.to_y_axis('ecmp8_count'), 'ecmp64_count': t.to_y_axis('ecmp64_count')}
    # print(y_axes)
    t.draw_fig9(y_axes)
