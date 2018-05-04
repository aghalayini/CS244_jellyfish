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
from pox.ext.jelly_pox import JELLYPOX
from subprocess import Popen
from time import sleep, time
from mininet.util import dumpNodeConnections


class JellyFishTop(Topo):
    ''' TODO, build your topology here'''

    def build(self):
        leftHost = self.addHost('h1')
        
        rightHost = self.addHost('h2')
        leftSwitch = self.addSwitch('s3')
        rightSwitch = self.addSwitch('s4')

        # Add links
        self.addLink(leftHost, leftSwitch)
        self.addLink(leftSwitch, rightSwitch)
        self.addLink(rightSwitch, rightHost)
    

if __name__ == "__main__":
    topo = JellyFishTop()
    net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink, controller=JELLYPOX)
    
    net.start()
    
    h1 = net.get('h1')    
    h2 = net.get('h2')    
    print(h1.IP())
    print(h2.IP())
    
    #h1.cmd('iperf -s &')
    #h2.cmd('iperf -c 10.0.0.1 -t 10 &')
    #sleep(10)
    #h1.cmd('kill %iperf')
    #print(h2.cmd('kill %iperf'))
    
    h2.cmd('ping 10.0.0.1 &')
    sleep(5)
    h2.cmd('kill %ping')
    
    #CLI(net)
    net.stop()
    Cleanup.cleanup()
