# Copyright 2011-2012 James McCauley
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#          http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
An L2 learning switch.

It is derived from one written live for an SDN crash course.
It is somwhat similar to NOX's pyswitch in that it installs
exact-match rules for each flow.
"""

from pox.core import core
import pox.openflow.libopenflow_01 as of
import pox.lib.packet as pkt
from pox.lib.util import dpid_to_str, str_to_dpid
from pox.lib.util import str_to_bool
#from build_topology import get_next_hop
import build_topology
#from build_topology import get_next_hop
import time
import pickle

log = core.getLogger()

# We don't want to flood immediately when a switch connects.
# Can be overriden on commandline.
_flood_delay = 0


class JellySwitch (object):

    def __init__ (self, connection):
        # Switch we'll be adding L2 learning switch capabilities to
        self.connection = connection

        # We want to hear PacketIn messages, so we listen
        # to the connection
        connection.addListeners(self)

        # log.debug("Initializing LearningSwitch, transparent=%s",
        #                     str(self.transparent))

    def _handle_PacketIn (self, event):
        """
        Handle packet in messages from the switch to implement above algorithm.
        """

        packet = event.parsed
        #log.info(packet)

        def flood (message=None):
            """ Floods the packet """
            msg = of.ofp_packet_out()
            if time.time() - self.connection.connect_time >= _flood_delay:
                # Only flood if we've been connected for a little while...
                if message is not None: log.info("FLOODING::%s" % message)
                # log.debug("%i: flood %s -> %s", event.dpid,packet.src,packet.dst)
                # OFPP_FLOOD is optional; on some switches you may need to change
                # this to OFPP_ALL.
                msg.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD))
            else:
                pass
                # log.info("Holding down flood for %s", dpid_to_str(event.dpid))
            if (event.parsed.find('ipv6') is None): 
                log.info("s{} FLOODING {}".format(event.dpid,event.parsed))
            msg.data = event.ofp
            msg.in_port = event.port
            self.connection.send(msg)

        def drop (duration=None):
            """
            Drops this packet and optionally installs a flow to continue
            dropping similar ones for a while
            """
            log.info("s{} DROPPING {}".format(event.dpid,event.parsed))
            if duration is not None:
                if not isinstance(duration, tuple):
                    duration = (duration, duration)
                msg = of.ofp_flow_mod()
                msg.match = of.ofp_match.from_packet(packet)
                msg.idle_timeout = duration[0]
                msg.hard_timeout = duration[1]
                msg.buffer_id = event.ofp.buffer_id
                self.connection.send(msg)
            elif event.ofp.buffer_id is not None:
                msg = of.ofp_packet_out()
                msg.buffer_id = event.ofp.buffer_id
                msg.in_port = event.port
                self.connection.send(msg)

        # 2
        if packet.type == packet.LLDP_TYPE or packet.dst.isBridgeFiltered():
            drop()  # 2a
            return

        if packet.dst.is_multicast:
            flood()  # 3a
            return

        ip_packet=packet.find('ipv4')
        if ip_packet==None: #packet is ethernet in swtiches
            ip_packet=packet.find('ipv6')
        if ip_packet!=None:
            tcp_packet = ip_packet.find('tcp')
            if tcp_packet == None:
                flood()
                log.info("non TCP traffic: %s" % ip_packet)
                return
            else:
                log.info("%s, %s, %s, %s, %s" % (ip_packet.srcip,ip_packet.dstip,tcp_packet.srcport,tcp_packet.dstport,event.dpid))
                src_dest_to_next_hop=pickle.load(open("pox/ext/d1.p","r"))
                host_ip_to_host_name=pickle.load(open("pox/ext/d2.p","r"))
                #log.info(src_dest_to_next_hop)
                #log.info(host_ip_to_host_name)
                #log.info(str(ip_packet.srcip),str(ip_packet.dstip),str(tcp_packet.srcport),str(tcp_packet.dstport),str(event.dpid))
                try:
                    port=build_topology.get_next_hop(str(ip_packet.srcip),str(ip_packet.dstip),str(tcp_packet.srcport),str(tcp_packet.dstport),str(event.dpid),str(event.port),src_dest_to_next_hop,host_ip_to_host_name)
                except:
                    log.error("CANNOT GET NEXT HOP, CHECK DICTIONARIES")
                    #flood()
                    return
                if port == event.port:  # 
                    # 5a
                    log.warning("Same port for packet from %s -> %s on %s.%s.    Drop." % (packet.src, packet.dst, dpid_to_str(event.dpid), port))
                    drop(10)
                    return
                else:
                    log.info("installing flow on s%s for %s.%i -> %s.%i" % (str(event.dpid),packet.src, event.port, packet.dst, port))
                    msg = of.ofp_flow_mod()
                    msg.match = of.ofp_match.from_packet(packet, event.port)
                    msg.idle_timeout = 0
                    msg.hard_timeout = 10000
                    msg.actions.append(of.ofp_action_output(port=port))
                    msg.data = event.ofp  # 6a
                    self.connection.send(msg)
        else:
            flood() #non-ip traffic



class l2_jelly (object):
    """
    Waits for OpenFlow switches to connect and makes them jelly switches.
    """

    def __init__ (self):
        """
        Initialize

        """
        core.openflow.addListeners(self)

    def _handle_ConnectionUp (self, event):
        log.info("CONNECTION UP %s -- %s" % (event.connection,event.dpid))
        JellySwitch(event.connection)


def launch ():
    """
    Starts an L2 jelly switch.
    """
    import pox.openflow.discovery
    pox.openflow.discovery.launch()

    core.registerNew(l2_jelly)

    import pox.openflow.spanning_tree

    pox.openflow.spanning_tree.launch(no_flood = True, hold_down = True)
    #pox.openflow.spanning_tree.launch(no_flood = False, hold_down = False)
