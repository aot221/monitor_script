"""
<Program Name>
  irc_seattlebot.py

<Started>
  June 16, 2009

<Author>
  Monzur Muhammad
  monzum@u.washington.edu
"""

import sys
import socket
import string
import time

#Exception that is raised if connection to the irc could not be made
class IRCConnectionFail(Exception):
  pass

def send_msg(message_string):
  """
  <Purpose>
    Opens up a connection to irc.freenode.net and then sends a message

  <Exceptions>
    Throws an exception if unable to connect to irc

  <Side Effects>
    None
  """

  #define all the necessary variables to connect to the right channel in the irc
  HOST='irc.freenode.net'
  PORT=6667 
  IDENT='SeattleMonitorBot'
  NICKNAME='Seattle_TestBot'
  REALNAME='Seattle'
  CHANNEL='#seattle'
  
  #create a connection to the irc and join a channel. Throw IRCConnectionFail exception on failure
  try:
    irc_connection=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    irc_connection.connect((HOST, PORT))
  except:
    raise IRCConnectionFail

  irc_connection.send("NICK "+NICKNAME+"\r\n")  #its important to have \r\n at the end
  irc_connection.send("USER "+IDENT+" "+HOST+" SeattleBot :"+REALNAME+"\r\n")
  irc_connection.send("JOIN "+CHANNEL+"\r\n")

  #wait for the connection to be made properly
  time.sleep(5)  
  
  #send a message on the channel then quit the channel then quit irc
  for line in message_string.split("\n"):
    irc_connection.send("PRIVMSG "+CHANNEL+" :"+line+"\r\n")
    time.sleep(1)
  
  irc_connection.send("PART "+CHANNEL+"\r\n")
  irc_connection.send("QUIT\r\n")

  #close irc connection
  irc_connection.close()

def main():
  """
  <Purpose>
    Send a message on irc.freenode.net as a bot on channel #seattle
 
  <Exceptions>
    None. Prints a message if invalid amount of argument

  <Side Effects>
    None

  <Usage>
    Run irc_seattlebot.py with an argument and the argument will be the message sent on the irc channel
    Example:

    python irc_seattlebot.py "Hello Everyone!!"
  """

  if len(sys.argv) < 2:
    print "Invalid number of arguments"
    print "Usage: python irc_seattlebot.py <message>"
    sys.exit(1)

  send_msg(sys.argv[1])



if __name__ == "__main__":
  main()
