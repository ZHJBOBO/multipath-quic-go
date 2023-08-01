#!/usr/bin/pythonmpquic-sbd

import time
import sys
import argparse
import os

from mininet.node import RemoteController
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Node
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from mininet.node import CPULimitedHost

from datetime import datetime


programs_dir = "/home/zcp/Downloads/mpquic-sbd-zcp/mpquic-sbd-master/src/quic-go/example/sample/"
dataset_dir = "/home/zcp/Downloads/mpquic-sbd-zcp/mpquic-sbd-master/src/quic-go/"



class LinuxRouter( Node ):
    "A Node with IP forwarding enabled."

    def config( self, **params ):
        super( LinuxRouter, self).config( **params )
        # Enable forwarding on the router
        self.cmd( 'sysctl net.ipv4.ip_forward=1' )

    def terminate( self ):
        self.cmd( 'sysctl net.ipv4.ip_forward=0' )
        super( LinuxRouter, self ).terminate()

        
class NetworkTopo( Topo ):
    "A LinuxRouter connecting three IP subnets"

    def __init__( self, l1_bw, l2_bw,l3_bw, **opts):
        "Create custom topo."

        # Initialize topology
        Topo.__init__( self, **opts )
      
        r1 = self.addHost('r1', cls=LinuxRouter, ip='10.0.0.1/30')
        r2 = self.addHost('r2', cls=LinuxRouter, ip='10.0.0.2/30')
        self.addLink(r1, r2,  cls=TCLink, bw=100, delay='1ms', intfName1='r1-eth0', intfName2='r2-eth0')

        client = self.addHost('client', ip='10.0.1.2/24', defaultRoute='via 10.0.1.1')
        server = self.addHost('server', ip='10.0.2.2/24', defaultRoute='via 10.0.2.1')

        # client
        self.addLink( client, r1, cls=TCLink, bw=l1_bw, delay='20ms', max_queue_size=1000, use_htb=True, intfName2='r1-eth1', params2={ 'ip' : '10.0.1.1/24' } )
        # server
        self.addLink( server, r2, cls=TCLink, bw=l3_bw, delay='20ms', max_queue_size=1000, use_htb=True, intfName2='r2-eth1', params2={ 'ip' : '10.0.2.1/24' } )
        
        self.addLink( client, r2, cls=TCLink, bw=l2_bw, delay='20ms', max_queue_size=1000, use_htb=True, intfName1='client-eth1', params1={ 'ip' : '10.0.3.2/24' }, 
                      intfName2='r2-eth2', params2={ 'ip' : '10.0.3.1/24' } )

                

def run():
    "Test linux router"
    server_link1_bw = 100
    for client_link1_bw, client_link2_bw in [(5,20),(5,10),(5,5),(10,20),(10,10),(10,5)]:
       topo = NetworkTopo(client_link1_bw, client_link2_bw, server_link1_bw)
       #c = RemoteController('c', '0.0.0.0', 6633)
       net = Mininet(topo=topo)  # controller is used by s1-s3
       #net.addController(c)
       net.start()

       #configure route table
       net['r1'].cmd('sysctl net.ipv4.ip_forward=1')
       net['r2'].cmd('sysctl net.ipv4.ip_forward=1')
       net['client'].cmd('route add -net 10.0.1.0/24 dev client-eth0')
       net['client'].cmd('route add -net 10.0.1.0/24 gw 10.0.1.1')
            
       net['client'].cmd('route add -net 10.0.2.0/24 dev client-eth1')
       net['client'].cmd('route add -net 10.0.2.0/24 gw 10.0.2.1')
    
       net['server'].cmd('route add -net 10.0.1.0/24 dev server-eth0')
       net['server'].cmd('route add -net 10.0.1.0/24 gw 10.0.2.1')
    
       net['server'].cmd('route add -net 10.0.3.0/24 dev server-eth0')
       net['server'].cmd('route add -net 10.0.3.0/24 gw 10.0.2.1')
    
       net['r1'].cmd("ip route add 10.0.2.0/24 via 10.0.0.2 dev r1-eth0")
       net['r2'].cmd("ip route add 10.0.1.0/24 via 10.0.0.1 dev r2-eth0")
    
       time.sleep(1)   
    
       print("test network bandwidth")
       #bandwidth_test(net)
       print("start experiment")
       conduct_experiment(net,client_link1_bw, client_link2_bw, server_link1_bw)
    
       #CLI(net)
       net.stop()

def bandwidth_test(net):
   net['server'].cmd("killall iperf3")
   net['r1'].cmd("killall iperf3")
   net['r2'].cmd("killall iperf3")

   net['server'].cmd("iperf3 -s -B  10.0.2.2 -p 5003 &")
   time.sleep(1)
   
   net['client'].cmd("rm network_bandwidth_udp_test.txt")
   net['client'].cmd("rm network_bandwidth_tcp_test.txt")
   
   net['client'].cmd("echo client to server >> network_bandwidth_udp_test.txt")
   net['client'].cmd("iperf3 -u -c 10.0.2.2 -p 5003 -b 1000M -t 30 >> network_bandwidth_udp_test.txt")
   time.sleep(1)
   net['client'].cmd("echo client to server >> network_bandwidth_tcp_test.txt")
   net['client'].cmd("iperf3 -c 10.0.2.2 -p 5003 -b 1000M -t 30 >> network_bandwidth_tcp_test.txt")
   time.sleep(1)
   
   net['r1'].cmd("echo client to r1 >> network_bandwidth_udp_test.txt")   
   net['r1'].cmd("iperf3 -s -B  10.0.1.1 -p 5003 &")
   net['client'].cmd("iperf3 -u -c 10.0.1.1 -p 5003 -b 1000M -t 30 >> network_bandwidth_udp_test.txt")
   
   net['r1'].cmd("echo client to r1 >> network_bandwidth_tcp_test.txt")
   net['client'].cmd("iperf3 -c 10.0.1.1 -p 5003 -b 1000M -t 30 >> network_bandwidth_tcp_test.txt")
   
   net['r2'].cmd("echo client to r2 >> network_bandwidth_udp_test.txt")     
   net['r2'].cmd("iperf3 -s -B  10.0.3.1 -p 5003 &")
   net['client'].cmd("iperf3 -u -c 10.0.3.1 -p 5003 -b 1000M -t 30 >> network_bandwidth_udp_test.txt")
   
   net['r2'].cmd("echo client to r2 >> network_bandwidth_tcp_test.txt")
   net['client'].cmd("iperf3 -c 10.0.3.1 -p 5003 -b 1000M -t 30 >> network_bandwidth_tcp_test.txt")
   
   net['r2'].cmd("echo r2 to server >> network_bandwidth_udp_test.txt")     
   net['r2'].cmd("iperf3 -u -c 10.0.2.2 -p 5003 -b 1000M -t 30 >> network_bandwidth_udp_test.txt")
   
   net['r2'].cmd("echo r2 to server >> network_bandwidth_tcp_test.txt")
   net['r2'].cmd("iperf3 -c 10.0.2.2 -p 5003 -b 1000M -t 30 >> network_bandwidth_tcp_test.txt")
      
   time.sleep(1)
   #net['r1'].cmd("iperf3 -c 10.0.3.2 -p 5003 -b 1000M -t 30 >> network_bandwidth_tcp_test.txt")
   #net['r1'].cmd("iperf3 -c 10.0.4.2 -p 5004 -b 1000M -t 30 >> network_bandwidth_tcp_test.txt")
   
   net['server'].cmd("killall iperf3")
   net['client'].cmd("killall iperf3")
   net['r1'].cmd("killall iperf3")
   net['r2'].cmd("killall iperf3")
   #net['server'].cmd("killall iperf3")


def copy_experiment_data(net, dataset_name, multipath_flag, client_link1_bw, client_link2_bw, server_link1_bw):
    result_dir = ""
    post_fix = 'link1_'+ str(client_link1_bw) + '_' + 'link2_'+ str(client_link2_bw) + '_' + 'link3_'+ str(server_link1_bw)
    if multipath_flag == "true":
       result_dir = "multipath_result_" + post_fix
    else:
       result_dir = "singlepath_result_" + post_fix
        
    net['client'].cmd("mkdir -p " + result_dir)    
    
    net['client'].cmd("mv /tmp/zcp_server_packets_path.csv " + result_dir)
    net['client'].cmd("mv /tmp/zcp_client_packets_path.csv " + result_dir)
    net['client'].cmd("mv /tmp/zcp_server_path_info.csv " + result_dir)
    net['client'].cmd("mv /tmp/zcp_client_path_info.csv " + result_dir)
    
    net['client'].cmd("mv /tmp/serv_test " + result_dir)
    net['client'].cmd("mv /tmp/zcp_server_recv_perf_" + multipath_flag + ".csv " + result_dir)
    net['client'].cmd("mv /tmp/zcp_client_recv_perf_" + multipath_flag + ".csv " + result_dir)

    net['client'].cmd("mv " + dataset_name + "_" + multipath_flag  + "_client_result.txt " + result_dir)
    net['client'].cmd("mv " + dataset_name + "_" + multipath_flag  + "_server_result.txt " + result_dir)
    
        
def conduct_experiment(net,client_link1_bw, client_link2_bw, server_link1_bw):
    net['server'].cmd("cd " + programs_dir)
    net['client'].cmd("cd " + programs_dir)

    #for dataset_name in ["dataset_text", "dataset_pic", "dataset_video"]:
    for dataset_name in ["dataset_single_file"]:
       files = os.listdir(dataset_dir + os.path.sep + dataset_name)
       print(files)
       for multipath_flag in ["true","false"]: 
          net['client'].cmd("sudo rm -r /tmp/serv_test")
          client_result = dataset_name + "_" + multipath_flag +  "_client_result.txt"
          server_result = dataset_name + "_" + multipath_flag +  "_server_result.txt"
          net['client'].cmd("rm " + client_result)
          net['client'].cmd("rm " + server_result)
          if multipath_flag == "false":
             net.configLinkStatus('client','r2','down')
          for f in files:
             f_path = dataset_dir + os.path.sep + dataset_name + os.path.sep + f
             print(f_path)
             net['server'].cmd("killall server-multipath.go")
             net['client'].cmd("killall client-multipath.go")
             time.sleep(1)
             net['server'].cmd("/usr/local/go/bin/go run server-multipath_v3.go " + multipath_flag + " 10.0.2.2 >> "  +  server_result + "&")
             time.sleep(1)
             net['client'].cmd("/usr/local/go/bin/go run client-multipath.go " + multipath_flag + " 10.0.2.2 "  + f_path + ">>" + client_result)
             time.sleep(1)
	     #break
          copy_experiment_data(net, dataset_name, multipath_flag,client_link1_bw, client_link2_bw, server_link1_bw)   
	     
if __name__ == '__main__':

    setLogLevel( 'info' )
    run()



# src/dash/caddy/caddy -conf /home/mininet/Caddyfile -quic -mp
# python src/AStream/dist/client/dash_client.py -m https://10.0.1.2:4242/output_dash.mpd -p 'basic' -q -mp >> out
# sudo mn --custom build_mininet_router3.py --topo networkTopo --controller=remote,ip=127.0.0.1 --link=tc -x

