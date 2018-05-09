# CS244_jellyfish
Reconstructing the Jellyfish paper

## How to install and run our code

You can use a local machine, but we recommend using Amazon EC2 or Google Cloud Compute Engine. We used Google Cloud and selected n1-highmem-8 (8 vCPUs, 52 GB memory) with Debian version 9.4 as our instance.

1. Make sure python2 and pip2 are installed.
2. Run “pip2 install matplotlib”
3. Run “pip2 install networkx”
4. Run “git clone git://github.com/mininet/mininet”
5. Run “git checkout -b 2.2.1 2.2.1”
6. Run “mininet/util/install.sh -a”
7. Using “ls” command, you should see several new directories.
8. Run “git clone https://github.com/aghalayini/CS244_jellyfish.git”
9. Run “cd CS244_jellyfish/pox/ext/”
10. Run “python2 ./graph.py”
* You should see two .svg files in your current directory. They are the shape of your random graph and reproduced figure 9 from the paper.
Run “sudo python2 ./build_topology.py”
* Data collection will happen before the mininet CLI(net) command which gives the user access to the mininet command prompt. Iperf results at every host will be outputted in an h.out file in the same /ext directory, along with an h.err file in case there were any errors. 
* You will also see an average throughput in the printed output.
* You can change parameters in # parameters section # of build_topology.py to change routing method (e.g. ‘ecmp8’), number of TCP connections and size of the network.
