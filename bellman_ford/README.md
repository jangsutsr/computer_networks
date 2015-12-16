# Introduction
This is the implementation of simplified version of distributed Bellman-Fort algorithm. The algorithm would run on a network of simulated routers identified by `<IP>, <Port Number>` pairs. Each router of the network would exchange messages with neighbors and update its distance vector table to finally reach convergence. Every link, or edge in the router graph, can be killed and then resurrected by either end points. A shut-down of one router in the router graph is equivalent to sending postponed linkdown messages to every neighbor router. 

# Message Protocol
There are three types of messages: route update, link up and link down. The syntaxes are as follow:
* route update:
``
ROUTE UPDATE
<host IP>:<host port>
<node IP>,<node port>,<node path cost>
...
``
* link up:
``
LINK UP
<host IP>:<host port>
``
* link down:
``
LINK DOWN
<host IP>:<host port>
``
# Notices
* The topology of the router graph is considered constant. That is, each router knows all its neighbors ahead of time. The argument to `router.py`, therefore, should be carefully configured to ensure two end points of each link learns exactly the same link cost.
* Set the timeout value of each router to an appropriate value, 3 sec for example, to avoid any potential conflictions.
* Note kill a link is equivalent to setting the link cost to infinity, therefore count-to-infinity problem might arise w.r.t certain graph topologies.

# Commands
* `LINKDOWN` `<ip_address> <port>`. This allows the user to destroy an existing link, i.e., change the link cost to infinity to the mentioned neighbor.
* `LINKUP` `<ip_address> <port>`. This allows the user to restore the link to the mentioned
neighbor to the original value after it was destroyed by a `LINKDOWN`.
* `SHOWRT`. This allows the user to view the current routing table of the client. It should indicate for each other client in the network, the cost and neighbor used to reach that client.
* `CLOSE`. With this command the client process should close/shutdown. Link failures is also assumed when a client doesn’t receive a `ROUTE UPDATE` message from a neighbor (i.e., hasn’t ‘heard’ from a neighbor) for `3*TIMEOUT` seconds. This happens when the neighbor client crashes or if the user calls the `CLOSE` command for it. When this happens, the link cost should be set to infinity and the client should stop sending ROUTE UPDATE messages to that neighbor. The link is assumed to be dead until the process comes up and a `ROUTE UPDATE` message is received again from that neighbor.

# Use Case
* Open up routers. For example, `python router.py 4115 3 128.59.196.2 4116 5.0 128.59.196.2 4118 30.0`
* After some time, check the converges of each router. For example, type `SHOWRT` on the above router would display:
``
<Current Time>Distance vector list is:
Destination = 128.59.196.2:4116, Cost = 5.0, Link = (128.59.196.2:4116) 
Destination = 128.59.196.2:4118, Cost = 30.0, Link = (128.59.196.2:4118)
``
* When all nodes converge, try link down command. For example, `LINKDOWN 128.59.196.2 4116`. Wait for a while to see if routers' dv tables change accrodingly.
* Try link up by calling `LINKUP 128.59.196.2 4116`.
* Close the router by calling `CLOSE`, wait for reasonable time to see the effect.
