import sys
from socket import *
import threading
import string
import pdb

'''
All client-related data sturctures and functions are defined here
'''
class Client:
    def __init__(self):
        self.LogOffFlag = False # For main thread to determine if to close
        self.ClientSocket = None # Socket for interacting with server
        self.MessageSocket = None # Socket for receiving incoming messages
        self.IdleSocket = None # Socket for receiving idle logout signal
        self.OrderList = {
            'whoelse': self.whoElse,
            'wholast': self.whoLast,
            'broadcast': self.broadcast,
            'message': self.message,
            'logout': self.logOut
        } # Map service function names to keys for concise service body
        self.LogInName = None # Will store name after logged in as indicator

    '''
    Main service body
    '''
    def run(self, IP, Port):
        self.ClientSocket = socket(AF_INET, SOCK_STREAM)
        self.ClientSocket.connect((IP, Port))
        # Now TCP connection is established
        status = self.logIn()
        if not status: # Failure to log in would stop connection and end process
            print('logging off...')
            self.ClientSocket.close()
        else: # Enter service phase only when successful logged in
            print('Welcome to simple chat server! ')
            i = threading.Thread(target = self.interact,\
                                 args = ())
            r = threading.Thread(target = self.recvMessage,\
                                 args = ())
            c = threading.Thread(target = self.check, args = ())
            # turn on daemon to enable keyboard interrupt
            i.daemon = True
            r.daemon = True
            c.daemon = True
            try:
                i.start()
                r.start()
                c.start()
                while True:
                    # any of the three threads can set LogOffFlag
                    if self.LogOffFlag:
                        self.ClientSocket.close()
                        self.MessageSocket.close()
                        self.IdleSocket.close()
                        print('Logging off...')
                        return
            except KeyboardInterrupt: # deal with keyboard interrupt
                self.ClientSocket.send('interrupt')
                if self.ClientSocket.recv(1024):
                    self.ClientSocket.close()
                    self.MessageSocket.close()
                    self.IdleSocket.close()
                    sys.exit('Forceful quit by ctrl - C')

    '''
    Function for managing the log in phase
    '''
    def logIn(self):
        # Send and modify user name
        if self.ClientSocket.recv(1024) == 'username':
            print('Username: ')
        else:
            print('No correct answer from server.')
            return False
        self.LogInName = raw_input()
        # prevent entering empty string
        while self.LogInName == '':
            print('Empty string not allowed, enter something.')
            self.LogInName = raw_input()
        self.ClientSocket.send(self.LogInName)
        prompt = self.ClientSocket.recv(1024)
        while prompt != 'password':
            if prompt == 'disconnect':
                return False
            elif prompt == 'incorrect':
                print('Incorrect user name, try again: ')
            elif prompt == 'exist':
                print('This user has already logged in, try again: ')
            elif prompt == 'wait':
                print('You are blocked to log in with this user name at present, try again: ')
            self.LogInName = raw_input()
            self.ClientSocket.send(self.LogInName)
            prompt = self.ClientSocket.recv(1024)
        # Send and modify pass word
        print('Password: ')
        p = raw_input()
        while p == '':
            print('Empty string not allowed, enter something: ')
            p = raw_input()
        self.ClientSocket.send(p)
        prompt = self.ClientSocket.recv(1024)
        while prompt != 'welcome':
            if prompt == 'disconnect':
                return False
            elif prompt == 'incorrect':
                print('Password mismatches, try again: ')
            elif prompt == 'block':
                print('You are blocked, please try again later. ')
                return False
            p = raw_input()
            while p == '':
                print('Empty string not allowed, enter something: ')
                p = raw_input()
            self.ClientSocket.send(p)
            prompt = self.ClientSocket.recv(1024)
        # Set up listening sockets
        self.MessageSocket = socket(AF_INET, SOCK_STREAM)
        self.MessageSocket.bind(('', 0))
        self.MessageSocket.listen(1)
        self.IdleSocket = socket(AF_INET, SOCK_STREAM)
        self.IdleSocket.bind(('', 0))
        self.IdleSocket.listen(1)
        messPort = str(self.MessageSocket.getsockname()[1])
        idlePort = str(self.IdleSocket.getsockname()[1])
        self.ClientSocket.send(messPort + ' ' + idlePort)
        self.MessageSocket, addrM = self.MessageSocket.accept()
        self.IdleSocket, addrI = self.IdleSocket.accept()
        return True

    '''
    Thread for managing MessageSocket. MessageSocket constantly receive
    Incoming message and display them on the screen if any.
    '''
    def recvMessage(self):
        while True:
            m = self.MessageSocket.recv(1024)
            m = string.split(m, ' ', 1)
            print('Message from ' + m[0] + ': ')
            print(m[1])
            print('Enter order, ' + self.LogInName + ': ')

    '''
    Thread for managing IdleSocket. IdleSocket constantly listens for
    'timeout' and tells main thread to logout whenever it receives one
    '''
    def check(self):
        if self.IdleSocket.recv(1024) == 'timeout':
            self.LogOffFlag = True

    '''
    Thread for interacting with server. It constantly receives keyboard
    orders, does initial parsing and calls corresponding functions.
    '''
    def interact(self):
        while True:
            print('Enter order, ' + self.LogInName + ': ')
            s = raw_input()
            order = string.split(s, ' ', 1)
            if order[0] in self.OrderList:
                self.ClientSocket.send(order[0])
                self.LogOffFlag = self.OrderList[order[0]](order)
            else:
                print('Invalid order, try again')

    '''
    Service function for reacting to 'whoelse' command.
    '''
    def whoElse(self, order):
        nameList = self.ClientSocket.recv(1024)
        if nameList == 'none':
            print('You are the only client online at present. ')
        else:
            nameList = nameList.split()
            print('List of online clients at present: ')
            for name in nameList:
                print(name)
        return False

    '''
    Service function for reacting to 'wholast' command.
    '''
    def whoLast(self, order):
        if self.ClientSocket.recv(1024) == 'time':
            if len(order) == 1:
                order.append('')
            while not order[1].isdigit():
                print('Please input an integer as input: ')
                order[1] = raw_input()
            if int(order[1]) > 60:
                order[1] = str(60)
                print('Time exceed, truncate to 60 min')
            self.ClientSocket.send(order[1])
            nameList = self.ClientSocket.recv(1024)
            if nameList == 'none':
                print('No client logged in last ' + \
                      order[1] + ' minute(s). ')
            else:
                nameList = nameList.split()
                print('List of logged in clients in last ' + \
                      order[1] + ' minute(s): ')
                for name in nameList:
                    print(name)
            return False

    '''
    Service function for reacting to 'broadcast' command.
    '''
    def broadcast(self, order):
        self.ClientSocket.recv(1024)
        if len(order) == 1: # If client input only 'broadcast'
            order.append('message') # Automatically complete command
        o = string.split(order[1], ' ', 1) # discard 'broadcast'
        desNames = []
        while o[0] != 'message':
            desNames.append(o[0])
            if len(o) <= 1: # If the command contains names but no 'message'
                self.ClientSocket.send('falsevalue')
                print('Invalid order, try again')
                return False
            o = string.split(o[1], ' ', 1)
        o = desNames + o
        # Now o contains all the names (if any) plus 'message' plus
        # message body (if any), each of which is one separate string
        self.ClientSocket.send('ready')
        prompt = self.ClientSocket.recv(1024)
        count = 0
        while prompt != 'message':
            self.ClientSocket.send(o[count])
            prompt = self.ClientSocket.recv(1024)
            # Since the number of destinations is implicitly set, the client
            # is supposed to given each of the names correctly
            while prompt == 'incorrect':
                print('Incorrect user name No. ' + str(count + 1) + ', correct it')
                self.ClientSocket.send(raw_input())
                prompt = self.ClientSocket.recv(1024)
            count += 1
        # Consider the situation where message body is empty
        if o[-1] == 'message' and (len(o) == 1 or o[-2] != 'message'):
            o.append('')
        while o[-1] == '':
            print('Say something: ')
            o[-1] = raw_input()
        self.ClientSocket.send(o[-1])
        return False

    '''
    Service function for reacting to 'message' command.
    '''
    def message(self, order):
        if len(order) < 2:
            order.append('')
        while order[1] == '':
            print('Please enter user name. ')
            order[1] = raw_input()
        o = string.split(order[1], ' ', 1)
        # Now o only contains username and message body (if any)
        if self.ClientSocket.recv(1024) == 'name':
            self.ClientSocket.send(o[0])
            prompt = self.ClientSocket.recv(1024)
            while prompt != 'message': # 'message' also means right name
                print('No such user, try again: ')
                self.ClientSocket.send(raw_input())
                prompt = self.ClientSocket.recv(1024)
            if len(o) < 2:
                o.append('')
            while o[1] == '':
                print('Say something: ')
                o[1] = raw_input()
            self.ClientSocket.send(o[1])
            return False

    '''
    Service function for reacting to 'logout' command.
    '''
    def logOut(self, order):
        if self.ClientSocket.recv(1024) == 'closed':
            return True


# main thread
IP = sys.argv[1]
Port = int(sys.argv[2])

C = Client()
C.run(IP, Port)


