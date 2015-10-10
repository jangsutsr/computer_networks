import sys
from socket import *
import threading
import time
import pdb

'''
Data structure for storing user information and methods for processing
user info in cooperation with Client itself.
'''
class User:
    def __init__(self, passWord):
        self.Connection = None # Sokcet for interaction with client
        self.IdleSok = None # Socket for sending idle log off info
        self.MessSok = None # Socket for checking message cache and send
        self.Pass = passWord # Correct password for corresponding client
        self.LoggedIn = False # Flag indicating client's log in status
        self.LogInStart = 0.0 # Used by whoLast() function
        self.BlackList = [] # Record of blocked  IPs
        self.Message = [] # Message cache

    '''
    Called after client is authenticated. Intented to set up all
    necessary fields of User.
    '''
    def logIn(self, connectionSocket, ID):
        self.LoggedIn = ID
        self.LogInStart = time.time()
        self.Connection = connectionSocket
        print(self.Connection.getsockname())
        self.MessSok = socket(AF_INET, SOCK_STREAM)
        self.IdleSok = socket(AF_INET, SOCK_STREAM)
        self.Connection.send('welcome')
        # receive port numbers of auxiliary sockets also means sockets
        # on both sides are ready to be connected 
        portNames = self.Connection.recv(1024)
        portNames = portNames.split()
        self.MessSok.connect((ID[0], int(portNames[0])))
        self.IdleSok.connect((ID[0], int(portNames[1])))
        print(self.MessSok.getsockname())
        print(self.IdleSok.getsockname())

    def setBlackList(self, IP):
        self.BlackList.append([IP, time.time()])

    def checkBlackList(self, IP, interval):
        if self.BlackList != []:
            # IPs who are no longer blocked are released during checking
            while time.time() - self.BlackList[0][1] > interval:
                del self.BlackList[0]
                if self.BlackList == []:
                    break
            # Search to see if remaining (blocked) IPs contain target
            for count in range(len(self.BlackList)):
                if IP == self.BlackList[count][0]:
                    return True
        # Jumping out of if-clause means either BlackList is empty or
        # IP is not blacklisted.
        return False

    def logOut(self):
        self.LoggedIn = False
        self.Message = []
        self.Connection.close()
        self.MessSok.close()
        self.IdleSok.close()

'''
All server-related data structures and functions are defined here,
server administrators can specify location of file storing user informa-
tion, block time in seconds for specious IPs and time out threshold in
minutes for idle users.
'''
class Server:
    def __init__(self, fileName = 'user_pass.txt', \
                 BLOCK_TIME = 60, TIME_OUT = 30):
        self.ClientInfo = dict() # Use dict() for user info storage
        # Create client dictionary according to user info file
        f = open(fileName, 'r')
        clientInfo = f.readlines()
        for count in range(len(clientInfo)):
            clientInfo[count] = clientInfo[count].split()
            self.ClientInfo[clientInfo[count][0]] = \
            User(clientInfo[count][1])
        print(clientInfo) # For TA's convinience :)
        self.BlockTime = BLOCK_TIME
        self.TimeOut = TIME_OUT
        self.ServerSocket = None
        self.OrderList = {
            'whoelse': self.whoElse,
            'wholast': self.whoLast,
            'broadcast': self.broadcast,
            'message': self.message,
            'logout': self.logOut,
        } # Map service function names to keys for concise service body

    '''
    Main thread which impliments ServerSocket to listen to incoming TCP
    connections. When an qurey for connection arrives, ServerSocekt
    finishes handshake and starts new thread to deal with that specific
    connection, as well as a new socket to be gateway for that connection.
    '''
    def listenToOrder(self, orderName, listenNum = 5):
        self.ServerSocket = socket(AF_INET, SOCK_STREAM)
        self.ServerSocket.bind(('', orderName))
        self.ServerSocket.listen(listenNum)
        try:
            while True:
                connectionSocket, addr=self.ServerSocket.accept()
                d = threading.Thread(target=self.dealWithOrder, \
                                     args=(connectionSocket, addr))
                d.daemon = True # Turn on daemon to enable ctrl-C
                d.start()
        # Impliment keyboard interrupt by ctrl-C
        except KeyboardInterrupt:
            sys.exit('Server ending...')

    '''
    Main thread for specific client which is invoked by main(listening)
    Thread. The corresponding connection is unitary, meaning socket on
    both ends would interact with each other.
    '''
    def dealWithOrder(self, connectionSocket, address):
        print('Order thread opening...')
        # Change the third argument of authenticate to reset chances
        name = self.authenticate(connectionSocket, address[0], 3)
        if name == False: # Discard unauthenticated connection.
            connectionSocket.send('disconnect')
            connectionSocket.close()
            print('Order thread closing...')
        else: # Only authenticated connection can enter service phase
            self.ClientInfo[name].logIn(connectionSocket, address)
            print('Order thread for ' + name + ' begining...')
            self.ClientInfo[name].Connection.settimeout(self.TimeOut * 60)
            m = threading.Thread(target=self.dealWithMessage, \
                                 args=(name, ))
            m.daemon = True # Turn on daemon to enable keyboard interrupt
            m.start() # Thread dealing with this client's incoming message
            try:
                while True: # Start of service phase
                    order = self.ClientInfo[name].Connection.recv(1024)
                    # Consider client keyboard interrupts during wait
                    if order == 'interrupt':
                        self.ClientInfo[name].Connection.send('quit')
                        print('User ' + name + ' does not quit smoothly.')
                        self.ClientInfo[name].logOut()
                        print('Order thread for ' + name + ' ending...')
                        return
                    status = self.OrderList[order](name) # execute order
                    if not status: # Only return false when log out 
                        self.ClientInfo[name].logOut()
                        print('Order thread for ' + name + ' ending...')
                        return
            except timeout: # Implement timeout function
                print(name + ' time out')
                self.ClientInfo[name].IdleSok.send('timeout')
                self.ClientInfo[name].logOut()
                print('Order thread for ' + name + ' ending...')

    '''
    Thread for serving particular client's MessSok. This thread is opened
    during the log in period of corresponding client.
    '''
    def dealWithMessage(self, record):
        print('Message thread for ' + record + ' begining...')
        while self.ClientInfo[record].LoggedIn:
            # Send out message whenever message cache is not empty
            while self.ClientInfo[record].Message != []:
                self.ClientInfo[record].MessSok.send( \
                self.ClientInfo[record].Message.pop(0))
        print('Message thread for ' + record + ' ending...')
        return

    '''
    Method for identify incoming connection. It is made up of two stages:
    check name and check password. Client would not be authenticated
    untill both checks are satisfied.
    '''
    def authenticate(self, connectionSocket, address, chance):
        # Start receiving and checking username
        connectionSocket.send('username')
        name = connectionSocket.recv(1024)
        while True: # Loop for checking incoming name
            if name == 'logout':
                return False
            elif not name in self.ClientInfo:
                connectionSocket.send('incorrect')
            elif self.ClientInfo[name].LoggedIn:
                connectionSocket.send('exist')
            elif self.ClientInfo[name].checkBlackList(address, \
                                                     self.BlockTime):
                connectionSocket.send('wait')
            else: # Only when none errors listed occur would loop end
                break
            name = connectionSocket.recv(1024)
        # Start receiving and checking password
        connectionSocket.send('password')
        # Set up limitation for recv-send rounds
        for count in range(chance, 0, -1):
            password = connectionSocket.recv(1024)
            if password == 'logout':
                return False
            elif password != self.ClientInfo[name].Pass:
                if count > 1:
                    connectionSocket.send('incorrect')
                else: # tell client loop ends and no chance left
                    connectionSocket.send('block')
            else:
                return name
        # Finish for-loop means this IP should be blocked
        self.ClientInfo[name].setBlackList(address)
        return False

    '''
    Service function for reacting 'whoelse' command. This function
    parses incoming command and send out other currently online client
    names
    '''
    def whoElse(self, name):
        nameString = '' # String for storing currently online client names
        for client in self.ClientInfo:
            if client == name:
                continue # Will not send querying client name
            if self.ClientInfo[client].LoggedIn:
                nameString += (client + ' ')
        if nameString == '':
            nameString = 'none'
        else:
            nameString = nameString[: -1] # the trailing space is omitted
        self.ClientInfo[name].Connection.send(nameString)
        return True

    '''
    Service function for reacting to 'wholast' command. This function
    parses incoming command and send out all who had logged in during
    the time specified by command body.
    '''
    def whoLast(self, name):
        self.ClientInfo[name].Connection.send('time')
        t = int(self.ClientInfo[name].Connection.recv(1024))
        nameString = ''
        # Check each client's latest log in time to determine
        for client in self.ClientInfo:
            if time.time() - self.ClientInfo[client].LogInStart \
               < t * 60:
                nameString += (client + ' ')
        if nameString == '':
            nameString = 'none'
        else:
            nameString = nameString[: -1] # the trailing space is omitted
        self.ClientInfo[name].Connection.send(nameString)
        return True

    '''
    Service function for reacting to 'broadcast' command. This function
    parses incoming command and send message to all online clients or
    clients specified in the command body.
    '''
    def broadcast(self, name):
        toName = [] # String list for storing destination names
        self.ClientInfo[name].Connection.send('check')
        if self.ClientInfo[name].Connection.recv(1024) == 'falsevalue':
            return True
        # Following lines will be executed only when 'ready' is received
        self.ClientInfo[name].Connection.send('user')
        order = self.ClientInfo[name].Connection.recv(1024)
        # Checking orders: if it is correct name, incorrect name or 'message'
        while order != 'message':
            if order not in self.ClientInfo:
                self.ClientInfo[name].Connection.send('incorrect')
                order = self.ClientInfo[name].Connection.recv(1024)
            else:
                toName.append(order)
                self.ClientInfo[name].Connection.send('user')
                order = self.ClientInfo[name].Connection.recv(1024)
        # tell client all user names has been received, ready to accept
        # message body
        self.ClientInfo[name].Connection.send('message')
        m = self.ClientInfo[name].Connection.recv(1024)
        if toName == []: # toName unchange means no name is given, broadcast to all
            for u in self.ClientInfo:
                if u != name and self.ClientInfo[u].LoggedIn:
                    self.ClientInfo[u].Message.append(name + ' ' + m)
        else: # Broadcast to specified users
            toName = list(set(toName))
            for u in toName:
                if u != name and self.ClientInfo[u].LoggedIn:
                    self.ClientInfo[u].Message.append(name + ' ' + m)
        return True

    '''
    Service function for reacting to 'message' command. This function
    parses incoming command and send message to exactly one client in
    the command body.
    '''
    def message(self, name):
        self.ClientInfo[name].Connection.send('name')
        u = self.ClientInfo[name].Connection.recv(1024)
        while u not in self.ClientInfo:
            self.ClientInfo[name].Connection.send('incorrect')
            u = self.ClientInfo[name].Connection.recv(1024)
        self.ClientInfo[name].Connection.send('message') # confirm name
        m = self.ClientInfo[name].Connection.recv(1024)
        if u != name:
            self.ClientInfo[u].Message.append(name + ' ' + m)
        return True

    '''
    Service function for reacting to 'message' command. This function
    send signal to close connected client
    '''
    def logOut(self, name):
        self.ClientInfo[name].Connection.send('closed')
        return False


# main thread
Port = int(sys.argv[1])

S = Server()
S.listenToOrder(Port)

