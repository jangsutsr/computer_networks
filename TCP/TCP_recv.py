#!/usr/bin/env python

'Definition of TCP receiver and related executable codes.'

__author__ = 'Sirui Tan'

from socket import *
import sys
import pdb
import struct
import filecmp
import datetime

MSS = 532 # Here the MSS must be equal to that of sender's

class Receiver:
    def __init__(self, fileName, lPort, sIP, sPort, logName):
        self.Sok = socket(AF_INET, SOCK_DGRAM)
        self.Sok.bind(('', lPort))
        self.FromIP = gethostbyname(gethostname())
        self.ToIP, self.ToPort, self.LPort = sIP, sPort, lPort
        self.RecvBuffer, self.UnackBuffer = [], []
        self.ExpSeqNum = 0
        self.Log = open(logName, 'w')
        self.File = open(fileName, 'w')
        self.Record = []

    '''
    The main receiver function
    '''
    def run(self):
        while True:
            message, addr = self.Sok.recvfrom(MSS)
            if self.notCorrupt(message):
                if len(message) > 20: # messages other than FIN have contents
                    self.dealWithMess(message)
                    self.sendACK()
                    while self.RecvBuffer != []:
                        self.File.write(self.RecvBuffer.pop(0))
                else:
                    self.finish(message)
                    break
        print('Delivery completed successfully. ')

    '''
    Function for testing bit errors
    '''
    def notCorrupt(self, message):
        calc = (message + '\x00') if len(message) % 2 != 0 else message
        check = list(struct.unpack('!' + str(len(calc) // 2) + 'H', calc))
        s = 0
        while check != []:
            s = self._add(s, check.pop(), 65535)
        return s == 65535

    '''
    Update RecvBuffer and UnackBuffer according to message received.
    '''
    def dealWithMess(self, message):
        decode = struct.unpack('!2H2I4H' + str(len(message) - 20) + 's', \
                               message)
        self.Record = [str(datetime.datetime.now()), \
                       self.ToIP + ':' + str(decode[0]), \
                       self.FromIP + ':' + str(decode[1]), \
                       str(decode[2]), str(decode[3])]
        self.Log.write(', '.join(self.Record) + '\n')
        self.Record = []
        head = decode[2] # SeqNum of the receiving packet
        tail = self._add(decode[2], len(decode[-1])) # SeqNum of next packet
        if self.ExpSeqNum == head: # Enqueue only if message is expected.
            self.RecvBuffer.append(decode[-1])
            self.ExpSeqNum = self._add(self.ExpSeqNum, len(decode[-1]))
            while self.UnackBuffer != [] and \
                  self.UnackBuffer[-1][1] == self.ExpSeqNum:
                self.ExpSeqNum = self.UnackBuffer[-1][2]
                self.RecvBuffer.append(self.UnackBuffer.pop()[0])
        else:
            self._insert([decode[-1], head, tail])

    '''
    Send ACK according to ExpSeqNum.
    '''
    def sendACK(self):
        packet = struct.pack('!2H2I4H', \
                             self.LPort, self.ToPort, \
                             0, self.ExpSeqNum, \
                             2 ** 4, 0, 0, 0)
        self.Sok.sendto(packet, (self.ToIP, self.ToPort))
        self.Record = [str(datetime.datetime.now()), \
                       self.FromIP + ':' + str(self.LPort), \
                       self.ToIP + ':' + str(self.ToPort), \
                       str(0), str(self.ExpSeqNum), 'ACK']
        self.Log.write(', '.join(self.Record) + '\n')
        self.Record = []

    '''
    Send ACK if FIN is received and close the connection and files.
    '''
    def finish(self, message):
        decode = struct.unpack('!2H2I4H', message)
        self.Record = [str(datetime.datetime.now()), \
                       self.ToIP + ':' + str(decode[0]), \
                       self.FromIP + ':' + str(decode[1]), \
                       str(decode[2]), str(decode[3]), 'FIN']
        self.Log.write(', '.join(self.Record) + '\n')
        self.Record = []
        if decode[4] == 1: # Verify that FIN is received
            packet = struct.pack('!2H2I4H', \
                                 self.LPort, self.ToPort, \
                                 0, self.ExpSeqNum, \
                                 2 ** 4 + 1, 0, 0, 0)
            self.Sok.sendto(packet, (self.ToIP, self.ToPort))
            self.Record = [str(datetime.datetime.now()), \
                           self.FromIP + ':' + str(self.LPort), \
                           self.ToIP + ':' + str(self.ToPort), \
                           str(0), str(self.ExpSeqNum), 'ACK', 'FIN']
            self.Log.write(', '.join(self.Record) + '\n')
            self.Record = []
            self.Log.close()
            self.File.close()
            self.Sok.close()

    '''
    Fixed-length unsigned integer increment. The length is specified by
    base
    '''
    def _add(self, num, increment, base=0xFFFFFFFF):
        num += increment
        if num > base:
            num -= (base + 1)
        return num

    '''
    Insert Unexpected packet into UnackBuffer. Situation when sequence
    number overflows is considered and dealt with.
    '''
    def _insert(self, seg):
        ht = [self.ExpSeqNum] # Array for storing head-tail info
        # Iterate to record head-tails and check duplicate packet
        for count in range(len(self.UnackBuffer) - 1, -1, -1):
            ht.append(self.UnackBuffer[count][1:])
            if seg == self.UnackBuffer[count]:
                return
        head, tail = seg[1], seg[2]
        if seg[1] > seg[2]: # If overflow happens in the packet recved
            tail += 0xFFFFFFFF
        rewind = False # Flag indicating whether rewind happens
        # Update ht from the point where rewind happens.
        if len(ht) > 1 and ht[0] > ht[1][0]:
            rewind = True
        for count in range(1, len(ht)):
            if rewind:
                ht[count][0] += 0xFFFFFFFF
                ht[count][1] += 0xFFFFFFFF
            else:
                if ht[count][0] > ht[count][1]:
                    ht[count][1] += 0xFFFFFFFF
                    rewind = True
                elif count < len(ht) - 1 and ht[count][1] > ht[count + 1][0]:
                    rewind = True
        # Insert segment to the proper position of UnackBuffer.
        if len(ht) == 1 or ht[0] <= head and ht[1][0] >= tail:
            self.UnackBuffer.append(seg)
        else:
            count = 1
            while count < len(ht) - 1:
                if ht[count][1] <= head and ht[count + 1][0] >= tail:
                    self.UnackBuffer.insert(len(self.UnackBuffer) - count, \
                                            seg)
                    return
                count += 1
            self.UnackBuffer.insert(0, seg)


if __name__ == '__main__':
    para = sys.argv
    if len(para) == 1:
        r = Receiver('file_recv.txt', 41194, \
                     'localhost', 41191, 'log_recv.txt')
        r.run()
        print filecmp.cmp('file_recv.txt', 'file_send.txt')
    else:
        r = Receiver(para[1], int(para[2]), para[3], int(para[4]), para[5])
        r.run()
