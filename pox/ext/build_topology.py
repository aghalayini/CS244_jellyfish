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
from mininet.util import dumpNodeConnections,pmonitor
import hashlib
import networkx as nx
from itertools import islice
from mininet.log import setLogLevel
import pickle
import random


# Topology port description:
# Every switch with switch_id=i is connected to host_id by port "number_of_racks + host_id"
#                               is connected to switch j by port "j"

src_dest_to_next_hop = {} # d1 maps (src_switch_id, dest_switch_id, current_switch_id) to [next_switch_id1, next_switch_id2, ...]
host_ip_to_host_name = {} # d2 e.g. maps '10.0.0.1' to 'h0'

######################################### Parameters #########################################
iperf_time = 100 # seconds
switch_switch_link_bw = 400 # Mbps
switch_host_link_bw = 100 # Mbps
r_method = '8_shortest' # 'ecmp8', 'ecmp64' or '8_shortest'
number_of_tcp_flows = 1 # should be 1 or 8
nx_topology = NXTopology(number_of_servers=100, switch_graph_degree=3, number_of_links=15)
##############################################################################################

# current_switch_id is string, e.g. '5'
# returns int
def get_next_hop(src_ip, dest_ip, src_port, dest_port, current_switch_id,current_port,src_dest_to_next_hop_u,host_ip_to_host_name_u):
    print("host_ip_to_host_name dict: {}".format(host_ip_to_host_name))
    src_host = host_ip_to_host_name_u[src_ip] # host object
    dest_host = host_ip_to_host_name_u[dest_ip] # host object
    src_switch_id = nx_topology.get_rack_index(int(str(src_host)[1:]))+1 # int
    dest_switch_id = nx_topology.get_rack_index(int(str(dest_host)[1:]))+1 # int
    if str(dest_switch_id) == current_switch_id: # destination host is directly connected to current_switch
        return nx_topology.number_of_racks + int(str(dest_host)[1:])+1
    print("src_dest_to_next_hop dict: ",src_dest_to_next_hop_u) 
    next_switch_ids = src_dest_to_next_hop_u[(src_switch_id, dest_switch_id, int(current_switch_id))]
    print("next_switch_ids: ",next_switch_ids)
    next_hop_index = next_hop_selector_hash(src_ip, dest_ip, src_port, dest_port, upper_limit=len(next_switch_ids)) 
    next_hop = next_switch_ids[next_hop_index]
    while next_hop==int(current_port):
        next_hop_index=random.randint(0,len(next_switch_ids)-1)
        next_hop=next_switch_ids[next_hop_index]
    return next_hop # because it is also the out_port we should send the packet to

    

# all inputs are string
# output is in [0, upper_limit)
def next_hop_selector_hash(src_ip, dest_ip, src_port, dest_port, upper_limit=1):
    hash_object = hashlib.md5(src_ip+dest_ip+src_port+dest_port)
    #print(hash_object)
    return int(hash_object.hexdigest(), 16) % upper_limit


class JellyFishTop(Topo):
    ''' TODO, build your topology here'''

    def build(self):
        #global nx_topology
        #nx_topology = NXTopology(number_of_servers=16, switch_graph_degree=2, number_of_links=3)
        
        # create switches
        for n in nx_topology.G.nodes():
            self.addSwitch('s'+str(n+1))
        
        # connect switches to each other
        # for every link (i,j), switch with switch_id=i is connected to port number i of switch with switch_id=j
        for e in nx_topology.G.edges():
            self.addLink('s'+str(e[0]+1), 's'+str(e[1]+1), e[1]+1, e[0]+1, bw=switch_switch_link_bw)
        
        # create hosts and connect them to ToR switch
        for h in range(nx_topology.number_of_servers):
            self.addHost('h'+str(h))
            self.addLink('h'+str(h), 's'+str(nx_topology.get_rack_index(h)+1), 0, nx_topology.number_of_racks + h+1, bw=switch_host_link_bw)
        
        def modify_dict(sender,receiver):
            node1 = nx_topology.get_rack_index(sender)
            node2 = nx_topology.get_rack_index(receiver)
            # print(node1, node2)
            shortest_paths = list(islice(nx.shortest_simple_paths(nx_topology.G, node1, node2), 64))
            
            if r_method == '8_shortest':
                selected_paths = islice(shortest_paths, nx_topology.shortest_path_k) # 8 shortest paths
            elif r_method == 'ecmp8':
                selected_paths = islice(shortest_paths, nx_topology.ECMP_last_index(shortest_paths, 8) + 1) #ECMP8
            else:
                selected_paths = islice(shortest_paths, nx_topology.ECMP_last_index(shortest_paths, 64) + 1) # ECMP64

            switch_to_next_hop = {}
            for path in selected_paths:
                for i in range(len(path)-1):
                    s = switch_to_next_hop.get(path[i], set())
                    s.add(path[i+1]+1)
                    switch_to_next_hop[path[i]] = s
            
            
            for k in switch_to_next_hop.keys():
                a = list(switch_to_next_hop[k])
                a.sort()
                src_dest_to_next_hop[(node1+1, node2+1, k+1)] = a
            #print src_dest_to_next_hop
            #sleep(1)
            
            
                        
        for sender in range(len(nx_topology.sender_to_receiver)): 
            receiver = nx_topology.sender_to_receiver[sender]
            modify_dict(receiver,sender)
            modify_dict(sender,receiver)


if __name__ == "__main__":
    os.system('sudo mn -c 2>/dev/null')
    #setLogLevel('info')
    topo = JellyFishTop()
    net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink, controller=JELLYPOX, autoSetMacs=True) 
    net.start()
    sleep(2)
    print 'net started'
    
    for h in net.hosts:
        host_ip_to_host_name[h.IP()] = str(h)
        print(h.IP(),h)
    #print(get_next_hop('10.0.0.1', '10.0.0.2', '1000', '5000', '6',src_dest_to_next_hop,host_ip_to_host_name))
    pickle.dump(src_dest_to_next_hop,open("d1.p","w"))
    pickle.dump(host_ip_to_host_name,open("d2.p","w"))

    for host_idx in range(len(nx_topology.sender_to_receiver)):
        for idx in range(len(nx_topology.sender_to_receiver)):
            if host_idx==idx:
                continue
            if idx<15: 
                IP_to_MAC="10.0.0.{} 00:00:00:00:00:{}".format(idx+1,'0'+hex(idx+1).split('x')[-1])
            else:
                IP_to_MAC="10.0.0.{} 00:00:00:00:00:{}".format(idx+1,hex(idx+1).split('x')[-1])
            command_str="sudo arp -s {}".format(IP_to_MAC)
            sender_host = net.get('h'+str(host_idx))
            sender_host.cmd(command_str)
    
    '''
    s_popens = {}
    c_popens = {}
    for host in net.hosts:
        s_popens[host] = host.popen("iperf -s -i 1 &")

    for sender in range(len(nx_topology.sender_to_receiver)):
        receiver = nx_topology.sender_to_receiver[sender] # int
        sender_host = net.get('h'+str(sender)) # host object
        receiver_host = net.get('h'+str(receiver)) # host object
        c_popens[sender_host] = host.popen("iperf -c {} -i 1 -t 10 &".format(receiver_host.IP()))
        # print "iperf -c {} -i 1 -t 60".format(receiver_host.IP())
 
    # Monitor them and print output
    print (len(c_popens))
    for host, line in pmonitor(c_popens):
        if host:
            print("<%s>: %s" % (host.name, line))
    '''

    outfiles, errfiles = {}, {}

    for h in net.hosts:
        outfiles[h] = './%s.out' % h.name
        errfiles[h] = './%s.err' % h.name
        h.cmd('iperf ' + '-i ' + str(1) + ' -s' + ' &')
        
    sleep(10)

    for sender in range(len(nx_topology.sender_to_receiver)):
        receiver = nx_topology.sender_to_receiver[sender] # int
        sender_host = net.get('h'+str(sender)) # host object
        receiver_host = net.get('h'+str(receiver)) # host object
        command = 'sleep 1; iperf '+ '-i '+ str(1) + ' -t ' + str(iperf_time) + ' -c ' + receiver_host.IP() + ' -P '+str(number_of_tcp_flows)+' > '+ outfiles[sender_host] + ' 2> ' + errfiles[sender_host]
        print("sender:{} cmd:{}".format(sender_host.IP(), command))
        sender_host.sendCmd(command)


    for h in net.hosts:
        h.waitOutput()
        h.cmd("kill -9 %iperf")
        h.cmd('wait')
    
    average = 0
    for f in outfiles.values():
        start_flag = False
        bw = 0.0
        with open(f, 'r') as o:
            for line in o:
                if start_flag == True:
                    a = line.rfind('/sec')
                    if a < 0:
                        continue
                    a = line[0:a].rfind(' ')
                    b = line[0:a].rfind(' ')
                    bw = float(line[b+1:a])
                if 'Bandwidth' in line:
                    start_flag = True
        print(f, bw)
        average += bw
    average = float(average) / len(outfiles.values())
    print ('average bandwidth between all pairs = '+str(average))




    CLI(net)
    net.stop()
    Cleanup.cleanup()
