Socket Programming
===

#### CONTENTS OF THIS FILE

 * Description
 * Environment
 * Instructions
 * Sample
 * Bonus


### DESCRIPTION
This chatting system is composed of two python scripts, Server.py, which
needs the support of user_pass.txt, and Client.py. One host running Server.py 
and multiple hosts running Client.py would enable message delivery among logged
in clients. Both codes basically involve implimenting multi-threading and socket.
The big picture is every time a server receives a TCP request from a client, it
opens up one to three threads to deal with it, and in server there is a database
for storing relevant user informations.

### ENVIRONMENT
Text editor: vim
interpreter: python 2.7.3
OS: OS X 10.10.5 Yosemite

### INSTRUCTIONS
* Copy Server.py into the file system of a host which would be the server.
* Copy Client.py into file systems of hosts which would clients.
* on server's terminal, type "python Server.py <Port Number>" to open the server process.
* on clients' terminals, type "python Client.py <IP number of server> <port number of server>" to open the client process.
* To close a client, type 'logout' whenever you are prompted to enter something. A client can also be forcefully terminated by keyboard interrupt.
* To close a server, use keyboard interrupt.

### SAMPLES
Suppose the server has been opened and a client has built up a TCP connection with the server. Type the commands in order to see the outcome.

- columbia
- 109bway
- 116bway
- whoelse
- message seas mo mo da!

Now open another terminal, open up a client following the instructions, and type the commands in order to see the outcome on both client terminals.

- columbia
- seas
- summerisover
- broadcast message cao cao da!!
- broadcast columbia message diao diao da!!!
- wholast 10
- logout (at the first terminal)
- whoelse
- <keyboard interrupt-

### BONUS

* Offline Messaging: private messages to a offline client would be displayed as soon as the client logs in. To test, simply send messages to an 
offline client and later log it in to see what happens.

* Parse and Correct: during interaction, when it comes to incorrect commands, the server not just send the message but provide hints to help the 
client correct. To test, be a dummy ( only this time ;) ) and make as many mistakes as you can when typing, see how the server corrects you step
by step.
