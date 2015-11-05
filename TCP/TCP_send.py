#!/usr/bin/env python

'Definition of TCP sender and related executable codes.'

__author__ = 'Sirui Tan'

from socket import *
import sys
import pdb
import threading
import struct
import time
import datetime

MSS = 532 # the maximum segment size here includes TCP header.

class Sender:
    def __init__(self, fileName, rIP, rPort, aPort, logName, windowSize):
        try:
            self.SendBuffer = self._loadData(fileName)
            self.Sok = socket(AF_INET, SOCK_DGRAM)
            self.Sok.bind(('', aPort))
            self.FromIP = gethostbyname(gethostname())
            self.FromPort, self.ToIP, self.ToPort = aPort, rIP, rPort
            self.WindowSize = windowSize
            self.RecvBuffer, self.UnackBuffer = [], []
            self.Log = open(logName, 'w')
            # At anytime except for UnackBuffer manipulation, UnackBuffer
            # is always enclosed by SendBase and NextSeqNum.
            self.NextSeqNum, self.SendBase = 0, 0
            self.Timer, self.TimeoutInterval = None, 1.0
            self.EstimatedRTT, self.SampleRTT, self.DevRTT = 0, 0, 0
            self.Stat, self.Record = [0, 0, 0], []
        except IOError:
            print('File to be sent not found, terminating...')
            exit()

    def _loadData(self, fileName):
        f = open(fileName, 'r')
        sB = []
        while True:
            segment = f.read(MSS - 20)
            if segment == '':
                break
            else:
                sB.append(segment)
        f.close()
        return sB

    '''
    The main sender function.
    '''
    def run(self):
        r = threading.Thread(target=self.recvACK, args=())
        r.daemon = True
        r.start()
        while True: # Main loop
            # Deal with ACKs as long as there are any incoming
            if self.RecvBuffer != []:
                while self.RecvBuffer != []:
                    self.dealWithUnack()
            if self.isTimeout():
                self.retransmit()
            if self.SendBuffer != [] and \
               len(self.UnackBuffer) != self.WindowSize:
                self.sendOutPacket()
            # Both buffers are empty means all packets are ACKed
            if self.SendBuffer == [] and self.UnackBuffer == []:
                self.finish()
                break
        print('Delivery completed successfully. ')
        print('Total bytes sent = ' + str(self.Stat[0]))
        print('Segments sent = ' + str(self.Stat[1]))
        print('Segments retransmitted = ' + str(self.Stat[2]))

    '''
    Daemon thread responsible for storing incoming ACKs to RecvBuffer
    '''
    def recvACK(self):
        while True:
            message, addr = self.Sok.recvfrom(20)
            # ACK's receving time is recorded along with the ACK itself.
            self.RecvBuffer.append([message, str(datetime.datetime.now()), \
                                    time.time()])

    '''
    Manipulate on UnackBuffer according to the earliest received ACK.
    '''
    def dealWithUnack(self):
        ACK = self.RecvBuffer.pop(0) # Dequeue the earlist received ACK
        decode = struct.unpack('!2H2I4H', ACK[0])
        # Record incoming ACK on log file.
        self.Record = [ACK[1], \
                       self.ToIP + ':' + str(decode[0]), \
                       self.FromIP + ':' + str(decode[1]), \
                       str(decode[2]), str(decode[3]), \
                       'ACK', str(self.EstimatedRTT)]
        self.Log.write(', '.join(self.Record) + '\n')
        self.Record = []
        # Manipulate UnackBuffer only if received ACK number > SendBase.
        if decode[3] > self.SendBase:
            self.SendBase = decode[3]
            while self.UnackBuffer != [] and \
                  self.UnackBuffer[0][1] < self.SendBase:
                self.SampleRTT = ACK[2] - self.UnackBuffer.pop(0)[2]
            self._update() # update related time variables
            if self.UnackBuffer == []:
                self.Timer = None
            else: # restart the timer
                self.Timer = time.time()

    '''
    Send out the first packet in SendBuffer.
    '''
    def sendOutPacket(self):
        packet = self._format() # Format segments into TCP packets
        if self.Timer == None:
            self.Timer = time.time()
        self._sendPak(packet) # Send out data packet
        # Update UnackBuffer and NextSeqNum
        self.UnackBuffer.append([packet, self.NextSeqNum, time.time()])
        self.NextSeqNum = self._add(self.NextSeqNum, len(packet) - 20)

    '''
    Retransmit the first packet in UnackBuffer and update timer. Note
    here the delayed ACK is ignored.
    '''
    def retransmit(self):
        packet = self.UnackBuffer[0][0]
        self.Record = [self.FromIP + ':' + str(self.FromPort), \
                       self.ToIP + ':' + str(self.ToPort), \
                       str(self.UnackBuffer[0][1]), str(0)]
        # There will be overlap between send and retrans counts
        self._sendPak(packet)
        self.Stat[2] += 1
        self.Timer = time.time()
        # Following the GBN paradigm to update all unacked packets' timers
        for count in range(len(self.UnackBuffer)):
            self.UnackBuffer[count][2] = self.Timer

    '''
    Function for checking timeout
    '''
    def isTimeout(self):
        if self.Timer == None:
            return False
        else:
            return time.time() - self.Timer > self.TimeoutInterval

    '''
    Terminate connection when all packets are sent and ACKed.
    '''
    def finish(self):
        # Send out the first FIN
        output = struct.pack('!2H2I3H', \
                             self.FromPort, self.ToPort, \
                             self.NextSeqNum, 0, \
                             1, 0, 0)
        nums = struct.unpack('!' + str(len(output) // 2) + 'H', output)
        checkSum = self._gene(list(nums))
        FIN =  struct.pack('!2H2I4H', \
                           self.FromPort, self.ToPort, \
                           self.NextSeqNum, 0, \
                           1, 0, checkSum, 0)
        self.Record = [self.FromIP + ':' + str(self.FromPort), \
                       self.ToIP + ':' + str(self.ToPort), \
                       str(self.NextSeqNum), str(0), 'FIN']
        self._sendPak(FIN)
        self.Timer = time.time()
        while True:
            # Resend FIN if timeout
            if self.isTimeout(): # TimeoutInterval will no longer update
                self.Record = [self.FromIP + ':' + str(self.FromPort), \
                               self.ToIP + ':' + str(self.ToPort), \
                               str(self.NextSeqNum), str(0), 'FIN']
                self._sendPak(FIN)
                self.Stat[2] += 1
                self.Timer = time.time()
            if self.RecvBuffer != []:
                ACK = self.RecvBuffer.pop() # would expect only one ACK
                decode = struct.unpack('!2H2I4H', ACK[0])
                if decode[4] == 2 ** 4 + 1: # Validate incoming ACK
                    self.Record = [ACK[1], \
                                   self.ToIP + ':' + str(decode[0]), \
                                   self.FromIP + ':' + str(decode[1]), \
                                   str(decode[2]), str(decode[3]), \
                                   'ACK', 'FIN', \
                                   str(self.EstimatedRTT)]
                    self.Log.write(', '.join(self.Record) + '\n')
                    self.Record = []
                    self.Sok.close()
                    self.Log.close()
                    break

    '''
    Generate TCP-styled packet out of original segment.
    '''
    def _format(self):
        packet = self.SendBuffer.pop(0)
        # Use separate string ref for generating checksum in case of 
        # odd-lengthed packet
        calc = (packet + '\x00') if len(packet) % 2 != 0 else packet
        output = struct.pack('!2H2I3H' + str(len(calc)) + 's', \
                             self.FromPort, self.ToPort, \
                             self.NextSeqNum, 0, \
                             0, 0, 0, \
                             calc)
        nums = struct.unpack('!' + str(len(output) // 2) + 'H', output)
        checkSum = self._gene(list(nums)) # calculate checkSum
        self.Record = [self.FromIP + ':' + str(self.FromPort), \
                       self.ToIP + ':' + str(self.ToPort), \
                       str(self.NextSeqNum), str(0)]
        return struct.pack('!2H2I4H' + str(len(packet)) + 's', \
                           self.FromPort, self.ToPort, \
                           self.NextSeqNum, 0, \
                           0, 0, checkSum, 0, \
                           packet)

    '''
    Send out formatted segment and update log file and stats accordingly.
    '''
    def _sendPak(self, packet):
        self.Sok.sendto(packet, (self.ToIP, self.ToPort))
        self.Record.insert(0, str(datetime.datetime.now()))
        self.Record.append(str(self.EstimatedRTT))
        self.Log.write(', '.join(self.Record) + '\n')
        self.Record = []
        self.Stat[0] += len(packet)
        self.Stat[1] += 1

    '''
    Generate checksum out of input array nums.
    '''
    def _gene(self, nums):
        s = 0
        while nums != []:
            s = self._add(s, nums.pop(), 65535)
        return 65535 - s

    '''
    Fixed-length unsigned integer increment. The length is specified by
    base.
    '''
    def _add(self, num, increment, base=0xFFFFFFFF):
        num += increment
        if num > base:
            num -= (base + 1)
        return num

    '''
    Update corresponding time variables according to (newly updated)
    SampleRTT. EWMA model is used here.
    '''
    def _update(self):
        if self.EstimatedRTT == 0:
            self.EstimatedRTT = self.SampleRTT
        else:
            self.EstimatedRTT = 0.875 * self.EstimatedRTT + \
                                0.125 * self.SampleRTT
        self.DevRTT = 0.75 * self.DevRTT + \
                      0.25 * abs(self.SampleRTT - self.EstimatedRTT)
        self.TimeoutInterval = self.EstimatedRTT + 4 * self.DevRTT

if __name__ == '__main__':
    para = sys.argv
    if len(para) == 1:
        s = Sender('file_send.txt', 'localhost', \
                   41192, 41191, 'log_send.txt', 5)
    else:
        if len(para) == 6:
            para.append(1)
        s = Sender(para[1], para[2], int(para[3]), \
                   int(para[4]), para[5], para[6])
    s.run()
