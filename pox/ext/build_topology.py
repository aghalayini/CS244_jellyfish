from graph import NXTopology
import os
import sys
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.node import OVSController
from mininet.node import Controller
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.clean import Cleanup
sys.path.append("../../")
from jelly_pox import JELLYPOX
from subprocess import Popen
from time import sleep, time
from mininet.util import dumpNodeConnections
import hashlib
import networkx as nx
from itertools import islice
from mininet.log import setLogLevel

# Topology port description:
# Every switch with switch_id=i is connected to host_id by port "number_of_racks + host_id"
#                               is connected to switch j by port "j"

src_dest_to_next_hop = {} # maps (src_switch_id, dest_switch_id, current_switch_id) to [next_switch_id1, next_switch_id2, ...]
host_ip_to_host_name = {} # e.g. maps '10.0.0.1' to 'h0'
nx_topology = None
iperf_time = 10 # seconds

# current_switch_id is string, e.g. '5'
# returns int
def get_next_hop(src_ip, dest_ip, src_port, dest_port, current_switch_id):
    
    src_host = host_ip_to_host_name[src_ip] # host object
    dest_host = host_ip_to_host_name[dest_ip] # host object
    src_switch_id = nx_topology.get_rack_index(int(str(src_host)[1:])) # int
    dest_switch_id = nx_topology.get_rack_index(int(str(dest_host)[1:])) # int
    if str(dest_switch_id) == current_switch_id: # destination host is directly connected to current_switch
        return nx_topology.number_of_racks + int(str(dest_host)[1:])
    
    
    next_switch_ids = src_dest_to_next_hop[(src_switch_id, dest_switch_id, current_switch_id)]
    next_hop_index = next_hop_selector_hash(src_ip, dest_ip, src_port, dest_port, upper_limit=len(next_switch_ids))
    next_hop = next_switch_ids[next_hop_index]
    return next_hop # because it is also the out_port we should send the packet to
    
    

# all inputs are string
# output is in [0, upper_limit)
def next_hop_selector_hash(src_ip, dest_ip, src_port, dest_port, upper_limit=1):
    hash_object = hashlib.md5(src_ip+dest_ip+src_port+dest_port)
    int(hash_object.hexdigest(), 16) % upper_limit


class JellyFishTop(Topo):
    ''' TODO, build your topology here'''

    def build(self):
        global nx_topology
        nx_topology = NXTopology(number_of_servers=25, switch_graph_degree=4, number_of_links=50)
        
        # create switches
        for n in nx_topology.G.nodes():
            self.addSwitch('s'+str(n))
        
        # connect switches to each other
        # for every link (i,j), switch with switch_id=i is connected to port number i of switch with switch_id=j
        for e in nx_topology.G.edges():
            self.addLink('s'+str(e[0]), 's'+str(e[1]), e[1], e[0])
        
        # create hosts and connect them to ToR switch
        for h in range(nx_topology.number_of_servers):
            self.addHost('h'+str(h))
            self.addLink('h'+str(h), 's'+str(nx_topology.get_rack_index(h)), 0, nx_topology.number_of_racks + h)
        
        
        for sender in range(len(nx_topology.sender_to_receiver)):
            receiver = nx_topology.sender_to_receiver[sender]
            node1 = nx_topology.get_rack_index(sender)
            node2 = nx_topology.get_rack_index(receiver)
            # print(node1, node2)
            shortest_paths = list(islice(nx.shortest_simple_paths(nx_topology.G, node1, node2), 64))
            
            k_shortest_paths = islice(shortest_paths, nx_topology.shortest_path_k)
            switch_to_next_hop = {}
            for path in k_shortest_paths:
                for i in range(len(path)-1):
                    s = switch_to_next_hop.get(path[i], set())
                    s.add(path[i+1])
                    switch_to_next_hop[path[i]] = s
            
            
            for k in switch_to_next_hop.keys():
                a = list(switch_to_next_hop[k])
                a.sort()
                src_dest_to_next_hop[(node1, node2, k)] = a
            #print src_dest_to_next_hop
            #sleep(1)
            
            ecmp8 = islice(shortest_paths, nx_topology.ECMP_last_index(shortest_paths, 8) + 1)
            ecmp64 = islice(shortest_paths, nx_topology.ECMP_last_index(shortest_paths, 64) + 1)
                        
    

if __name__ == "__main__":
    os.system('sudo mn -c 2>/dev/null')
    setLogLevel('info')
    topo = JellyFishTop()
    net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink, controller=JELLYPOX)
    
    net.start()
    sleep(3)
    print 'net started'
    
    for h in net.hosts:
        host_ip_to_host_name[h.IP()] = h
    
    # print(get_next_hop('10.0.0.1', '10.0.0.2', '1000', '5000', '1'))
    
    '''
    for h in net.hosts:
        h.cmd('iperf -s &')
    
    for sender in range(len(nx_topology.sender_to_receiver)):
        receiver = nx_topology.sender_to_receiver[sender] # int
        sender_host = net.get('h'+str(sender)) # host object
        receiver_host = net.get('h'+str(receiver)) # host object
        command ='iperf -c '+receiver_host.IP()+' -t '+str(iperf_time)+' -i '+str(iperf_time)+' &'
        print command
        sender_host.cmd(command)
        
    sleep(iperf_time)
    
    for h in net.hosts:
        print h.cmd('kill %iperf')
        
    '''
    
    CLI(net)
    net.stop()
    Cleanup.cleanup()
