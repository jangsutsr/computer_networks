# Project Documentation
In this programming assignment, a simplified TCP­like transport layer protocol is implemented. The protocol provides reliable, in order delivery of a stream of bytes. It can recover from in­network packet loss, packet corruption, packet duplication and packet reordering and can cope with dynamic network delays. However, it doesn’t congestion or flow control.

# Program Features
* The program is logically composed of two classes: the `Sender` class, which emulates how TCP formats and sends segments from application layer to link layer, and the `Receiver` class, which emulates how TCP checks incoming Packets from link layer and send corresponding ACKs back.
* Both classes follow TCP specifications to make sure all segments sent are finally received correctly with no loss or order errors.
* `Sender` keeps track of three statistics: number of packets sent, packets received and packets resent. Note here the set of resent packets is a subset of packets sent.
* Both classes would record relevant information on log files each time a packet is sent or received.

# Usage
First of all, open link emulator and specify a series of options. For example, `./newudpl -B50 -l10 -d0.25`. Details can be found [here](http://www.cs.columbia.edu/~hgs/research/projects/newudpl/)

Then run `TCP_recv.py`, the usage of which is `python TCP_recv.py <filename> <listening_port> <sender_IP> <sender_port> <log_filename>`.

Finally run `TCP_sender.py`, the usage of which is `python TCP_send.py <filename> <remote_IP> <remote_port> <ack_port_num> <log_filename> <window_size>`.

In order to use properly, make sure that sender, receiver and link emulator are correctly connected, which means data shoud send from sender to emulator to receiver. Note that ACKs should be sent directly from receiver to sender.

At the end of each execution, four files would exist, two of which are data files and the other two log files. Make sure the data file on sender's side is exist and non-empty before execution.

# Misc Info
## TCP Segment Structure Used
Every packet, including ACKs and FINs, follows the standard TCP header structure with no options. No ACK has checksum, though.

## States Visited 
`Sender` would visit 4 states:

1. If there are data from layer above, format and send the data to the layer below;
2. If an ACK is received, deal with it and manipulate corresponding attributes;
3. If timeout, resend the first unACKed packet and restart the timer;
4. If all data from layer above are sent and ACKed, close the connection and terminate the program.

`Receiver` would visit 2 states:

1. If data packet is received and verified, store it to the buffer or send it to upper layer, and reply with appropriate ACK;
2. If FIN packet is received and verified, reply with ACK, close the connection and terminate the program. 

## Loss Recovery Mechanism
The mechanism is identical to TCP's standard pipelined reliable data transfer mechanism, which is a mixture of go-back-N and selective repeat mechanisms.
