import socket
import sys
import pdb
import threading
import datetime
import time

class Router(object):
    """The main router class

    Instances of Router class play the role of nodes in the routers network.
    To set a router up and run, initialize it, initialize its neighbors by
    calling init_neighbor() method, and finally call run() method.

    Attributes:
        name: tuple of (host_IP, host_port).
        name_str: colon-separated string showing the unique name of host
            router in the router network.
        sok: UDP socket for receiving messages from neighbors.
        timeout: Float number specifying timeout interval.
        neighbors: Dictionary of Neighbor objects.
        distance_vector: Dictionary of OtherRouter objects, which is in
            fact the host router's own DV table.
    """
    class Neighbor(object):
        """Used as elements of Router's neighbor table.

        Attributes:
            addr: string representing IP address of neighbor.
            port: Float number representing port number of neighbor.
            weight: Float number representing weight of the edge to
                neighbor.
            sok: An UDP socket for sending messages to underlying
                neighbor.
            distance_vector: A dictionary of key-value pairs, with
                key being a string of node name in <IP>:<port> format,
                value being float number representing route cost.
            send_timer: Timer indicating whether route update message
                should be resent.
            kill_timer: Timer indicating wheter the underlying neigbor
                is silent for too long to be kept alive.
            is_killed: Boolean to tell send thread whether this neighbor
                is reachable or not.
            *_ready: Boolean flags to tell send thread if certain message
                should be send out.
        """
        def __init__(self, addr, port, weight):
            """Instanciation of class.

            Args:
                addr: string representing IP address of neighbor.
                port: Float number representing port number of neighbor.
                weight: Float number representing weight of the edge to
                    neighbor.

            Returns:
                None.
            """
            self.addr, self.port = addr, port
            self.weight = weight
            self.sok = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.distance_vector = dict()
            self.send_timer, self.kill_timer = time.time(), time.time()
            self.is_killed = False
            self.update_ready, self.linkup_ready, self.linkdown_ready = True, False, False

        def dv_update(self, dv_list):
            """Update neighbor's DV table.

            Args:
                dv_list: List of strings, each contain comma-separated
                    fields of node IP, node port and node path cost.

            Returns:
                None.
            """
            for line in dv_list:
                line_sep = line.split(',')
                other_name = line_sep[0] + ':' + line_sep[1]
                other_cost = float(line_sep[2])
                self.distance_vector[other_name] = other_cost

    class OtherRouter(object):
        """Elements of Router's distance_vector attribute.

        Attributes:
            cost: Float number showing the path cost.
            link: String of the name of next-hop router.
        """
        def __init__(self, cost, link):
            self.cost, self.link = cost, link


    def __init__(self, local_port, timeout):
        """Instanciation of Router class.

        Args:
            local_port: Integer representing router's port number.
            timeout: Float number specifying timeout interval.

        Returns:
            None
        """
        self.name = (socket.gethostbyname(socket.gethostname()), local_port)
        self.name_str = ':'.join([self.name[0], str(self.name[1])])
        self.sok = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sok.bind(self.name)
        self.timeout = timeout
        self.neighbors = dict()
        self.distance_vector = dict()
        self.distance_vector[self.name_str] = Router.OtherRouter(0., self.name_str)

    def init_neighbor(self, addr, port, weight):
        """Add a new neighbor to neighbors list.

        Note this method must be executed before calling run() method as the
        topology of the whole router graph is assumed constant.

        Args:
            addr: String representing neighbor IP address.
            port: Integer representing neighbor port number.
            weight: Float representing link weight to the neighbor.
        """
        neighbor_name = ':'.join([addr, str(port)])
        self.neighbors[neighbor_name] = Router.Neighbor(addr, port, weight)
        self.distance_vector[neighbor_name] = Router.OtherRouter(weight, neighbor_name)

    def run(self):
        """The main life cycle of a router.

        Args:
            None.

        Returns:
            None. (This method is supposed to terminate the program)
        """
        # Open three threads to execute receiving message, sending out message
        # and checking timeouts simutaneously.
        RV = threading.Thread(target=self.recv, args=())
        RV.daemon = True
        RV.start()
        TO = threading.Thread(target=self.check_time, args=())
        TO.daemon = True
        TO.start()
        SD = threading.Thread(target=self.send, args=())
        SD.daemon = True
        SD.start()
        while True:
            type_in = raw_input(self.name_str + '--> ')
            order = type_in.split(' ', 1)
            if order[0] == 'LINKDOWN' and len(order) == 2:
                self.link_down(order[1])
            elif order[0] == 'LINKUP' and len(order) == 2:
                self.link_up(order[1])
            elif order[0] == 'SHOWRT' and len(order) == 1:
                self.showrt()
            elif order[0] == 'CLOSE' and len(order) == 1:
                self.close()
                break
            else:
                print('invalid order, try again!')
        sys.exit()

    def link_down(self, order):
        """Response function to 'LINKDOWN' command.

        Link down function is only valid w.r.t alive neighbors. It sets
        corresponding flag to inform sender to close the link and send out
        LINK DOWN message.

        Args:
            order: Space-separated string of IP and port of the neighbor to
                be linked down.

        Returns:
            None.
        """
        order = order.split(' ')
        if len(order) != 2:
            print('Invalid LINKDOWN format')
        else:
            neighbor_name = ':'.join(order)
            if neighbor_name not in self.neighbors:
                print('No such neighbor')
            elif self.neighbors[neighbor_name].is_killed:
                print('This link is already killed')
            else:
                self.neighbors[neighbor_name].linkdown_ready = True

    def link_up(self, order):
        """Response function to 'LINKUP' command.

        Link up function is only valid w.r.t dead neighbors. It sets
        corresponding flag to inform sender to reopen the link and send out
        LINK UP message.

        Args:
            order: Space-separated string of IP and port of the neighbor to
                be linked down.

        Returns:
            None.
        """
        order = order.split(' ')
        if len(order) != 2:
            print('Invalid LINKUP format')
        else:
            neighbor_name = ':'.join(order)
            if neighbor_name not in self.neighbors:
                print('No such neighbor')
            elif not self.neighbors[neighbor_name].is_killed:
                print('This link is still alive')
            else:
                self.neighbors[neighbor_name].linkup_ready = True

    def showrt(self):
        """Response function to 'SHOWRT' command.

        If showrt finds that all neighbors are dead, which means this router
        can reach nowhere, it would display an 'All neighbors offline' message
        instead of the DV table itself.

        Args:
            None.

        Returns:
            None.
        """
        for name in self.neighbors:
            if not self.neighbors[name].is_killed:
                break
        else:
            print('All neighbors offline, all distances are set to infinity. ')
            return
        print str(datetime.datetime.now().replace(microsecond=0)) + ' Distance vector list is:'
        for name in self.distance_vector:
            print('Destination={}, Cost={}, link=({})').format(name, self.distance_vector[name].cost, self.distance_vector[name].link)

    def close(self):
        """Response function to 'CLOSE' command.

        Args:
            None.

        Returns:
            None.
        """
        print 'close'


    def check_time(self):
        """Thread that constantly checks neighbors' timers.

        Only alive neighbors would be checked, this method informs sender when
        no route updates are sent to a neighbor for  more than 1 * timeout,
        and kills a neighbor when it is not heard for more than 3 * timeout
        time.

        Args:
            None.

        Returns:
            None.
        """
        while True:
            for name in self.neighbors:
                if not self.neighbors[name].is_killed:
                    if not self.neighbors[name].update_ready and time.time() - self.neighbors[name].send_timer > self.timeout:
                        self.neighbors[name].update_ready = True
                    if time.time() - self.neighbors[name].kill_timer > 3 * self.timeout:
                        self.neighbors[name].is_killed = True

    def send(self):
        """Thread that send out messages to neighbors.

        This method would check each neighbor's *_ready flags to determine
        whether to send corresponding messages. Note route updates would only
        consider living neighbors. At the end of each message delivery, cor-
        responding flag would be unset.

        Args:
            None

        Returns:
            None
        """
        while True:
            for neighbor_name in self.neighbors:
                if not self.neighbors[neighbor_name].is_killed:
                    if self.neighbors[neighbor_name].update_ready:
                        self.send_update(self.neighbors[neighbor_name])
                if self.neighbors[neighbor_name].linkup_ready:
                    self.send_linkup(self.neighbors[neighbor_name])
                if self.neighbors[neighbor_name].linkdown_ready:
                    self.send_linkdown(self.neighbors[neighbor_name])

    def send_update(self, neighbor):
        """Assemble and send out route updates to a neighbor.

        After route update is sent out, the neighbor's send_timer is reset.

        Args:
            neighbor: A Neighbor object of the neighbor to send message.

        Returns:
            None
        """
        message = 'ROUTE UPDATE'
        source = ':'.join([self.name[0], str(self.name[1])])
        dv = []
        for others in self.distance_vector:
            others_sep = others.split(':')
            dv.append(','.join([others_sep[0], others_sep[1], str(self.distance_vector[others].cost)]))
        dv = '\n'.join(dv)
        to_send = '\n'.join([message, source, dv])
        neighbor.sok.sendto(to_send, (neighbor.addr, neighbor.port))
        neighbor.send_timer = time.time()
        neighbor.update_ready = False

    def send_linkup(self, neighbor):
        """Assemble and send out link up to a neighbor.

        Args:
            neighbor: A Neighbor object of the neighbor to send message.

        Returns:
            None
        """
        message = 'LINK UP'
        source = ':'.join([self.name[0], str(self.name[1])])
        to_send = '\n'.join([message, source])
        neighbor.sok.sendto(to_send, (neighbor.addr, neighbor.port))
        neighbor.is_killed = False
        neighbor.linkup_ready = False
        # Since the neighbor resurrects after link up, both of its timers are
        # reset.
        neighbor.send_timer, neighbor.kill_timer = time.time(), time.time()

    def send_linkdown(self, neighbor):
        """Assemble and send out link down to a neighbor.

        Args:
            neighbor: A Neighbor object of the neighbor to send message.

        Returns:
            None
        """
        message = 'LINK DOWN'
        source = ':'.join([self.name[0], str(self.name[1])])
        to_send = '\n'.join([message, source])
        neighbor.sok.sendto(to_send, (neighbor.addr, neighbor.port))
        neighbor.is_killed = True
        neighbor.linkdown_ready = False

    def recv(self):
        """Thread that receives messages from neighbors.

        This function responds to received messages. Note in each case the
        update_dv() is called in case of updates of host's DV table.

        Args:
            None

        Returns:
            None
        """
        while True:
            data, useless = self.sok.recvfrom(1024)
            lines = data.split('\n')
            neighbor_name = lines[1]
            if neighbor_name in self.neighbors:
                if lines[0] == 'ROUTE UPDATE':
                    self.route_update(self.neighbors[neighbor_name], lines[2:])
                elif lines[0] == 'LINK UP':
                    self.link_up_respond(self.neighbors[neighbor_name])
                elif lines[0] == 'LINK DOWN':
                    self.link_down_respond(self.neighbors[neighbor_name])

    def route_update(self, neighbor, dv_list):
        """Response function to route update message.

        Note this function plays the same role as link_up_respond() as it
        indicates a neighbor is reachable (again).

        Args:
            neighbor: Neighbor object from which the message is sent.
            dv_list: String to be passed to neighbor's dv_update() function.

        Returns:
            None.
        """
        neighbor.is_killed = False
        neighbor.kill_timer = time.time()
        neighbor.dv_update(dv_list)
        # Iterate to see if new node is included in the graph.
        for name in neighbor.distance_vector:
            if name not in self.distance_vector:
                self.distance_vector[name] = Router.OtherRouter(float('Inf'), None)
        if self.update_dv():
            for name in self.neighbors:
                self.neighbors[name].update_ready = True
                self.neighbors[name].send_timer = time.time()

    def link_down_respond(self, neighbor):
        """Response function to link down message.

        Args:
            neighbor: Neighbor object from which the message is sent.

        Returns:
            None.
        """
        neighbor.is_killed = True
        if self.update_dv():
            for name in self.neighbors:
                self.neighbors[name].update_ready = True
                self.neighbors[name].send_timer = time.time()

    def link_up_respond(self, neighbor):
        """Response function to link up message.

        Args:
            neighbor: Neighbor object from which the message is sent.

        Returns:
            None.
        """
        neighbor.is_killed = False
        neighbor.send_timer = time.time()
        neighbor.kill_timer = time.time()
        if self.update_dv():
            for name in self.neighbors:
                self.neighbors[name].update_ready = True
                self.neighbors[name].send_timer = time.time()

    def update_dv(self):
        """The process of updating dv.

        The dv is updated elementwisely according to neighbors' dv entries.
        A flag would be set if the dv changes during the update.

        Args:
            None.

        Returns:
            Boolean flag indicating whether the dv changes or not.
        """
        is_changed = False
        for name in self.distance_vector:
            smallest = float('Inf')
            smallest_neighbor = None
            for neighbor_name in self.neighbors:
                if self.neighbors[neighbor_name].is_killed:
                    weight = float('Inf')
                else:
                    weight = self.neighbors[neighbor_name].weight
                if name in self.neighbors[neighbor_name].distance_vector:
                    candidate = self.neighbors[neighbor_name].distance_vector[name]
                    candidate += weight
                    if smallest > candidate:
                        smallest = candidate
                        smallest_neighbor = neighbor_name
            if self.distance_vector[name].cost != smallest and name != self.name_str:
                self.distance_vector[name].cost = smallest
                self.distance_vector[name].link = smallest_neighbor
                is_changed = True
        return is_changed

if __name__ == '__main__':
    local_port, time_out = sys.argv[1], sys.argv[2]
    r = Router(int(local_port), float(time_out))
    for i in range(3, len(sys.argv), 3):
        r.init_neighbor(sys.argv[i], int(sys.argv[i+1]), float(sys.argv[i+2]))
    r.run()
