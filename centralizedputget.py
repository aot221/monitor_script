#!/usr/bin/python
"""
<Program Name>
  centralizedputget.mix

<Started>
  January 8, 2008

<Author>
  justinc@cs.washington.edu
  Justin Cappos

<Purpose>
  Attempt to put a (k,v) into our centralized hash table and then get it back. 
  On error send an email to some folks.

<Usage>
  Modify the following global var params to have this script functional:
  - notify_list, a list of strings with emails denoting who will be
    emailed when something goes wrong

  This script takes no arguments. A typical use of this script is to
  have it run periodically using something like the following crontab line:
  7 * * * * /usr/bin/python /home/seattle/centralizedputget.py > /home/seattle/cron_log.centralizedputget
"""

import time
import os
import socket
import sys
import traceback
import threading
import random

import send_gmail
import integrationtestlib
import nonportable

from repyportability import *


#begin include centralizedadvertise.repy
""" 
Author: Justin Cappos

Start Date: July 8, 2008

Description:
Advertisements to a central server (similar to openDHT)


"""

#begin include centralizedadvertise_base.repy
""" 
Author: Justin Cappos

Start Date: July 8, 2008

Description:
Advertisements to a central server (similar to openDHT)


"""

#begin include session.repy
# This module wraps communications in a signaling protocol.   The purpose is to
# overlay a connection-based protocol with explicit message signaling.   
#
# The protocol is to send the size of the message followed by \n and then the
# message itself.   The size of a message must be able to be stored in 
# sessionmaxdigits.   A size of -1 indicates that this side of the connection
# should be considered closed.
#
# Note that the client will block while sending a message, and the receiver 
# will block while recieving a message.   
#
# While it should be possible to reuse the connectionbased socket for other 
# tasks so long as it does not overlap with the time periods when messages are 
# being sent, this is inadvisable.

class SessionEOF(Exception):
  pass

sessionmaxdigits = 20

# get the next message off of the socket...
def session_recvmessage(socketobj):

  messagesizestring = ''
  # first, read the number of characters...
  for junkcount in range(sessionmaxdigits):
    currentbyte = socketobj.recv(1)

    if currentbyte == '\n':
      break
    
    # not a valid digit
    if currentbyte not in '0123456789' and messagesizestring != '' and currentbyte != '-':
      raise ValueError, "Bad message size"
     
    messagesizestring = messagesizestring + currentbyte

  else:
    # too large
    raise ValueError, "Bad message size"

  try:
    messagesize = int(messagesizestring)
  except ValueError:
    raise ValueError, "Bad message size"
  
  # nothing to read...
  if messagesize == 0:
    return ''

  # end of messages
  if messagesize == -1:
    raise SessionEOF, "Connection Closed"

  if messagesize < 0:
    raise ValueError, "Bad message size"

  data = ''
  while len(data) < messagesize:
    chunk =  socketobj.recv(messagesize-len(data))
    if chunk == '': 
      raise SessionEOF, "Connection Closed"
    data = data + chunk

  return data

# a private helper function
def session_sendhelper(socketobj,data):
  sentlength = 0
  # if I'm still missing some, continue to send (I could have used sendall
  # instead but this isn't supported in repy currently)
  while sentlength < len(data):
    thissent = socketobj.send(data[sentlength:])
    sentlength = sentlength + thissent



# send the message 
def session_sendmessage(socketobj,data):
  header = str(len(data)) + '\n'
  # Sending these piecemeal does not accomplish anything, and can contribute 
  # to timeout issues when run by constantly overloaded machines.
  # session_sendhelper(socketobj,header)

  # Concatenate the header and data, rather than sending both separately.
  complete_packet = header + data

  # session_sendhelper(socketobj,data)

  session_sendhelper(socketobj, complete_packet)


#end include session.repy
# I'll use socket timeout to prevent hanging when it takes a long time...
#begin include sockettimeout.repy
"""
<Author>
  Justin Cappos, Armon Dadgar
  This is a rewrite of the previous version by Richard Jordan

<Start Date>
  26 Aug 2009

<Description>
  A library that causes sockets to timeout if a recv / send call would
  block for more than an allotted amount of time.

"""


class SocketTimeoutError(Exception):
  """The socket timed out before receiving a response"""


class _timeout_socket():
  """
  <Purpose>
    Provides a socket like object which supports custom timeouts
    for send() and recv().
  """

  # Initialize with the socket object and a default timeout
  def __init__(self,socket,timeout=10, checkintv='fibonacci'):
    """
    <Purpose>
      Initializes a timeout socket object.

    <Arguments>
      socket:
              A socket like object to wrap. Must support send,recv,close, and willblock.

      timeout:
              The default timeout for send() and recv().

      checkintv:
              How often socket operations (send,recv) should check if
              they can run. The smaller the interval the more time is
              spent busy waiting.
    """
    # Store the socket, timeout and check interval
    self.socket = socket
    self.timeout = timeout
    self.checkintv = checkintv


  # Allow changing the default timeout
  def settimeout(self,timeout=10):
    """
    <Purpose>
      Allows changing the default timeout interval.

    <Arguments>
      timeout:
              The new default timeout interval. Defaults to 10.
              Use 0 for no timeout. Given in seconds.

    """
    # Update
    self.timeout = timeout
  
  
  # Wrap willblock
  def willblock(self):
    """
    See socket.willblock()
    """
    return self.socket.willblock()


  # Wrap close
  def close(self):
    """
    See socket.close()
    """
    return self.socket.close()


  # Provide a recv() implementation
  def recv(self,bytes,timeout=None):
    """
    <Purpose>
      Allows receiving data from the socket object with a custom timeout.

    <Arguments>
      bytes:
          The maximum amount of bytes to read

      timeout:
          (Optional) Defaults to the value given at initialization, or by settimeout.
          If provided, the socket operation will timeout after this amount of time (sec).
          Use 0 for no timeout.

    <Exceptions>
      As with socket.recv(), socket.willblock(). Additionally, SocketTimeoutError is
      raised if the operation times out.

    <Returns>
      The data received from the socket.
    """

    # It's worth noting that this fibonacci backoff begins with a 2ms poll rate, and 
    # provides a simple exponential backoff scheme.

    fibonacci_backoff = False
    backoff_cap = 100 # Never use more than 100ms poll rate.

    pre_value = 1.0     # Our iterators for Fibonacci sequence.
    pre_pre_value = 1.0 # 

    # Since we want to be able to initialize with static poll rates (backwards 
    # compatibility) we specify a string if we're using the fibonacci backoff.
    if type(self.checkintv) is str:
      if self.checkintv == 'fibonacci':
        fibonacci_backoff = True

    # Set the timeout if None
    if timeout is None:
      timeout = self.timeout

    # Get the start time
    starttime = getruntime()

    # Block until we can read
    rblock, wblock = self.socket.willblock()
    while rblock:
      # Check if we should break
      if timeout > 0:
        # Get the elapsed time
        diff = getruntime() - starttime

        # Raise an exception
        if diff > timeout:
          raise SocketTimeoutError,"recv() timed out!"

      if fibonacci_backoff:
        # Iterate the sequence once
        sleep_length = pre_value + pre_pre_value
        pre_pre_value = pre_value
        pre_value = sleep_length

        # Make sure we don't exceed maximum backoff.
        if sleep_length > backoff_cap:
          sleep_length = backoff_cap

        # Unit conversion to seconds
        sleep_length = sleep_length / 1000.0

        # Sleep
        sleep(sleep_length)
      else: # Classic functionality.
        # Sleep
        try:
          sleep(float(self.checkintv))
        except:
          sleep(0.1)

      # If available, move to the next value of checkintv.
      

      # Update rblock
      rblock, wblock = self.socket.willblock()

    # Do the recv
    return self.socket.recv(bytes)


  # Provide a send() implementation
  def send(self,data,timeout=None):
    """
    <Purpose>
      Allows sending data with the socket object with a custom timeout.

    <Arguments>
      data:
          The data to send

      timeout:
          (Optional) Defaults to the value given at initialization, or by settimeout.
          If provided, the socket operation will timeout after this amount of time (sec).
          Use 0 for no timeout.

    <Exceptions>
      As with socket.send(), socket.willblock(). Additionally, SocketTimeoutError is
      raised if the operation times out.

    <Returns>
      The number of bytes sent.
    """
    # Set the timeout if None
    if timeout is None:
      timeout = self.timeout

    # Get the start time
    starttime = getruntime()

    # Block until we can write
    rblock, wblock = self.socket.willblock()
    while wblock:
      # Check if we should break
      if timeout > 0:
        # Get the elapsed time
        diff = getruntime() - starttime

        # Raise an exception
        if diff > timeout:
          raise SocketTimeoutError,"send() timed out!"

      # Sleep
      # Since switching to the fibonacci backoff, the nature of 
      # this field has changed. Rather than implement the backoff 
      # for checking block status (seems wasteful) we'll just use 
      # a constant value. Ten ms seems appropriate.
      sleep(0.010)

      # Update rblock
      rblock, wblock = self.socket.willblock()

    # Do the recv
    return self.socket.send(data) 




def timeout_openconn(desthost, destport, localip=None, localport=None, timeout=5):
  """
  <Purpose> 
    Wrapper for openconn.   Very, very similar

  <Args>
    Same as Repy openconn

  <Exception>
    Raises the same exceptions as openconn.

  <Side Effects>
    Creates a socket object for the user

  <Returns>
    socket obj on success
  """

  realsocketlikeobject = openconn(desthost, destport, localip, localport, timeout)

  thissocketlikeobject = _timeout_socket(realsocketlikeobject, timeout)
  return thissocketlikeobject





def timeout_waitforconn(localip, localport, function, timeout=5):
  """
  <Purpose> 
    Wrapper for waitforconn.   Essentially does the same thing...

  <Args>
    Same as Repy waitforconn with the addition of a timeout argument.

  <Exceptions> 
    Same as Repy waitforconn

  <Side Effects>
    Sets up event listener which calls function on messages.

  <Returns>
    Handle to listener.
  """

  # We use a closure for the callback we pass to waitforconn so that we don't
  # have to map mainch's to callback functions or deal with potential race
  # conditions if we did maintain such a mapping. 
  def _timeout_waitforconn_callback(localip, localport, sockobj, ch, mainch):
    # 'timeout' is the free variable 'timeout' that was the argument to
    #  timeout_waitforconn.
    thissocketlikeobject = _timeout_socket(sockobj, timeout)

    # 'function' is the free variable 'function' that was the argument to
    #  timeout_waitforconn.
    return function(localip, localport, thissocketlikeobject, ch, mainch)

  return waitforconn(localip, localport, _timeout_waitforconn_callback)

  
  


# a wrapper for stopcomm
def timeout_stopcomm(commhandle):
  """
    Wrapper for stopcomm.   Does the same thing...
  """

  return stopcomm(commhandle)
  
    


#end include sockettimeout.repy
#begin include serialize.repy
"""
Author: Justin Cappos


Start date: October 9th, 2009

Purpose: A simple library that serializes and deserializes built-in repy types.
This includes strings, integers, floats, booleans, None, complex, tuples, 
lists, sets, frozensets, and dictionaries.

There are no plans for including objects.

Note: that all items are treated as separate references.   This means things
like 'a = []; a.append(a)' will result in an infinite loop.   If you have
'b = []; c = (b,b)' then 'c[0] is c[1]' is True.   After deserialization 
'c[0] is c[1]' is False.

I can add support or detection of this if desired.
"""

# The basic idea is simple.   Say the type (a character) followed by the 
# type specific data.    This is adequate for simple types
# that do not contain other types.   Types that contain other types, have
# a length indicator and then the underlying items listed sequentially.   
# For a dict, this is key1value1key2value2.



def serialize_serializedata(data):
  """
   <Purpose>
      Convert a data item of any type into a string such that we can 
      deserialize it later.

   <Arguments>
      data: the thing to seriailize.   Can be of essentially any type except
            objects.

   <Exceptions>
      TypeError if the type of 'data' isn't allowed

   <Side Effects>
      None.

   <Returns>
      A string suitable for deserialization.
  """

  # this is essentially one huge case statement...

  # None
  if type(data) == type(None):
    return 'N'

  # Boolean
  elif type(data) == type(True):
    if data == True:
      return 'BT'
    else:
      return 'BF'

  # Integer / Long
  elif type(data) is int or type(data) is long:
    datastr = str(data) 
    return 'I'+datastr


  # Float
  elif type(data) is float:
    datastr = str(data) 
    return 'F'+datastr


  # Complex
  elif type(data) is complex:
    datastr = str(data) 
    if datastr[0] == '(' and datastr[-1] == ')':
      datastr = datastr[1:-1]
    return 'C'+datastr



  # String
  elif type(data) is str:
    return 'S'+data


  # List or tuple or set or frozenset
  elif type(data) is list or type(data) is tuple or type(data) is set or type(data) is frozenset:
    # the only impact is the first letter...
    if type(data) is list:
      mystr = 'L'
    elif type(data) is tuple:
      mystr = 'T'
    elif type(data) is set:
      mystr = 's'
    elif type(data) is frozenset:
      mystr = 'f'
    else:
      raise Exception("InternalError: not a known type after checking")

    for item in data:
      thisitem = serialize_serializedata(item)
      # Append the length of the item, plus ':', plus the item.   1 -> '2:I1'
      mystr = mystr + str(len(thisitem))+":"+thisitem

    mystr = mystr + '0:'

    return mystr


  # dict
  elif type(data) is dict:
    mystr = 'D'

    keysstr = serialize_serializedata(data.keys())
    # Append the length of the list, plus ':', plus the list.  
    mystr = mystr + str(len(keysstr))+":"+keysstr
    
    # just plop the values on the end.
    valuestr = serialize_serializedata(data.values())
    mystr = mystr + valuestr

    return mystr


  # Unknown!!!
  else:
    raise TypeError("Unknown type '"+str(type(data))+"' for data :"+str(data))



def serialize_deserializedata(datastr):
  """
   <Purpose>
      Convert a serialized data string back into its original types.

   <Arguments>
      datastr: the string to deseriailize.

   <Exceptions>
      ValueError if the string is corrupted
      TypeError if the type of 'data' isn't allowed

   <Side Effects>
      None.

   <Returns>
      Items of the original type
  """

  if type(datastr) != str:
    raise TypeError("Cannot deserialize non-string of type '"+str(type(datastr))+"'")
  typeindicator = datastr[0]
  restofstring = datastr[1:]

  # this is essentially one huge case statement...

  # None
  if typeindicator == 'N':
    if restofstring != '':
      raise ValueError("Malformed None string '"+restofstring+"'")
    return None

  # Boolean
  elif typeindicator == 'B':
    if restofstring == 'T':
      return True
    elif restofstring == 'F':
      return False
    raise ValueError("Malformed Boolean string '"+restofstring+"'")

  # Integer / Long
  elif typeindicator == 'I':
    try:
      return int(restofstring) 
    except ValueError:
      raise ValueError("Malformed Integer string '"+restofstring+"'")


  # Float
  elif typeindicator == 'F':
    try:
      return float(restofstring) 
    except ValueError:
      raise ValueError("Malformed Float string '"+restofstring+"'")

  # Float
  elif typeindicator == 'C':
    try:
      return complex(restofstring) 
    except ValueError:
      raise ValueError("Malformed Complex string '"+restofstring+"'")



  # String
  elif typeindicator == 'S':
    return restofstring

  # List / Tuple / set / frozenset / dict
  elif typeindicator == 'L' or typeindicator == 'T' or typeindicator == 's' or typeindicator == 'f':
    # We'll split this and keep adding items to the list.   At the end, we'll
    # convert it to the right type

    thislist = []

    data = restofstring
    # We'll use '0:' as our 'end separator'
    while data != '0:':
      lengthstr, restofdata = data.split(':', 1)
      length = int(lengthstr)

      # get this item, convert to a string, append to the list.
      thisitemdata = restofdata[:length]
      thisitem = serialize_deserializedata(thisitemdata)
      thislist.append(thisitem)

      # Now toss away the part we parsed.
      data = restofdata[length:]

    if typeindicator == 'L':
      return thislist
    elif typeindicator == 'T':
      return tuple(thislist)
    elif typeindicator == 's':
      return set(thislist)
    elif typeindicator == 'f':
      return frozenset(thislist)
    else:
      raise Exception("InternalError: not a known type after checking")


  elif typeindicator == 'D':

    lengthstr, restofdata = restofstring.split(':', 1)
    length = int(lengthstr)

    # get this item, convert to a string, append to the list.
    keysdata = restofdata[:length]
    keys = serialize_deserializedata(keysdata)

    # The rest should be the values list.
    values = serialize_deserializedata(restofdata[length:])

    if type(keys) != list or type(values) != list or len(keys) != len(values):
      raise ValueError("Malformed Dict string '"+restofstring+"'")
    
    thisdict = {}
    for position in xrange(len(keys)):
      thisdict[keys[position]] = values[position]
    
    return thisdict




  # Unknown!!!
  else:
    raise ValueError("Unknown typeindicator '"+str(typeindicator)+"' for data :"+str(restofstring))




#end include serialize.repy


class CentralAdvertiseError(Exception):
  """Error when advertising a value to the central advertise service."""

def centralizedadvertisebase_announce(servername, serverport, key, value, ttlval):
  """
   <Purpose>
     Announce a key / value pair into the CHT.

   <Arguments>
     servername: the server ip/name to contact.  Must be a string.

     serverport: the server port to contact.  Must be an integer.

     key: the key to put the value under. This will be converted to a string.

     value: the value to store at the key. This is also converted to a string.

     ttlval: the amount of time until the value expires.   Must be an integer

   <Exceptions>
     TypeError if ttlval is of the wrong type.

     ValueError if ttlval is not positive 

     CentralAdvertiseError is raised the server response is corrupted

     Various network and timeout exceptions are raised by timeout_openconn
     and session_sendmessage / session_recvmessage

   <Side Effects>
     The CHT will store the key / value pair.

   <Returns>
     None
  """
  # do basic argument checking / munging
  key = str(key)
  value = str(value)

  if not type(ttlval) is int and not type(ttlval) is long:
    raise TypeError("Invalid type '"+str(type(ttlval))+"' for ttlval.")

  if ttlval < 1:
    raise ValueError("The argument ttlval must be positive, not '"+str(ttlval)+"'")

  
  # build the tuple to send, then convert to a string because only strings
  # (bytes) can be transmitted over the network...
  datatosend = ('PUT',key,value,ttlval)
  datastringtosend = serialize_serializedata(datatosend)

  
  # send the data over a timeout socket using the session library, then
  # get a response from the server.
  sockobj = timeout_openconn(servername,serverport, timeout=10)
  try:
    session_sendmessage(sockobj, datastringtosend)
    rawresponse = session_recvmessage(sockobj)
  finally:
    # BUG: This raises an error right now if the call times out ( #260 )
    # This isn't a big problem, but it is the "wrong" exception
    sockobj.close()
  
  # We should check that the response is 'OK'
  try:
    response = serialize_deserializedata(rawresponse)
    if response != 'OK':
      raise CentralAdvertiseError("Centralized announce failed with '"+response+"'")
  except ValueError, e:
    raise CentralAdvertiseError("Received unknown response from server '"+rawresponse+"'")
      



def centralizedadvertisebase_lookup(servername, serverport, key, maxvals=100):
  """
   <Purpose>
     Returns a list of valid values stored under a key

   <Arguments>
     servername: the server ip/name to contact.  Must be a string.

     serverport: the server port to contact.  Must be an integer.

     key: the key to put the value under. This will be converted to a string.

     maxvals: the maximum number of values to return.   Must be an integer

   <Exceptions>
     TypeError if maxvals is of the wrong type.

     ValueError if maxvals is not a positive number

     CentralAdvertiseError is raised the server response is corrupted

     Various network and timeout exceptions are raised by timeout_openconn
     and session_sendmessage / session_recvmessage

   <Side Effects>
     None

   <Returns>
     The list of values
  """

  # do basic argument checking / munging
  key = str(key)

  if not type(maxvals) is int and not type(maxvals) is long:
    raise TypeError("Invalid type '"+str(type(maxvals))+"' for ttlval.")

  if maxvals < 1:
    raise ValueError("The argument ttlval must be positive, not '"+str(ttlval)+"'")

  # build the tuple to send, then convert to a string because only strings
  # (bytes) can be transmitted over the network...
  messagetosend = ('GET',key,maxvals)
  messagestringtosend = serialize_serializedata(messagetosend)


  sockobj = timeout_openconn(servername,serverport, timeout=10)
  try:
    session_sendmessage(sockobj, messagestringtosend)
    rawreceiveddata = session_recvmessage(sockobj)
  finally:
    # BUG: This raises an error right now if the call times out ( #260 )
    # This isn't a big problem, but it is the "wrong" exception
    sockobj.close()


  try:
    responsetuple = serialize_deserializedata(rawreceiveddata)
  except ValueError, e:
    raise CentralAdvertiseError("Received unknown response from server '"+rawresponse+"'")

  # For a set of values, 'a','b','c',  I should see the response: 
  # ('OK', ['a','b','c'])    Anything else is WRONG!!!
  
  if not type(responsetuple) is tuple:
    raise CentralAdvertiseError("Received data is not a tuple '"+rawresponse+"'")

  if len(responsetuple) != 2:
    raise CentralAdvertiseError("Response tuple did not have exactly two elements '"+rawresponse+"'")
  if responsetuple[0] != 'OK':
    raise CentralAdvertiseError("Central server returns error '"+str(responsetuple)+"'")

  
  if not type(responsetuple[1]) is list:
    raise CentralAdvertiseError("Received item is not a list '"+rawresponse+"'")

  for responseitem in responsetuple[1]:
    if not type(responseitem) is str:
      raise CentralAdvertiseError("Received item '"+str(responseitem)+"' is not a string in '"+rawresponse+"'")

  # okay, we *finally* seem to have what we expect...

  return responsetuple[1]

#end include centralizedadvertise_base.repy

# Hmm, perhaps I should make an initialization call instead of hardcoding this?
# I suppose it doesn't matter since one can always override these values
servername = "advertiseserver.poly.edu"
# This port is updated to use the new port (legacy port is 10101)
serverport = 10102


def centralizedadvertise_announce(key, value, ttlval):
  """
   <Purpose>
     Announce a key / value pair into the CHT.

   <Arguments>
     key: the key to put the value under. This will be converted to a string.

     value: the value to store at the key. This is also converted to a string.

     ttlval: the amount of time until the value expires.   Must be an integer

   <Exceptions>
     TypeError if ttlval is of the wrong type.

     ValueError if ttlval is not positive 

     CentralAdvertiseError is raised the server response is corrupted

     Various network and timeout exceptions are raised by timeout_openconn
     and session_sendmessage / session_recvmessage

   <Side Effects>
     The CHT will store the key / value pair.

   <Returns>
     None
  """
  return centralizedadvertisebase_announce(servername, serverport, key, value, ttlval)


def centralizedadvertise_lookup(key, maxvals=100):
  """
   <Purpose>
     Returns a list of valid values stored under a key

   <Arguments>
     key: the key to put the value under. This will be converted to a string.

     maxvals: the maximum number of values to return.   Must be an integer

   <Exceptions>
     TypeError if maxvals is of the wrong type.

     ValueError if maxvals is not a positive number

     CentralAdvertiseError is raised the server response is corrupted

     Various network and timeout exceptions are raised by timeout_openconn
     and session_sendmessage / session_recvmessage

   <Side Effects>
     None

   <Returns>
     The list of values
  """
  return centralizedadvertisebase_lookup(servername, serverport, key, maxvals)

#end include centralizedadvertise.repy

# event for communicating when the lookup is done or timedout
lookup_done_event = threading.Event()



def lookup_timedout():
    """
    <Purpose>
       Waits for lookup_done_event and notifies the folks on the
       notify_list (global var) of the lookup timeout.

    <Arguments>
        None.

    <Exceptions>
        None.

    <Side Effects>
        Sends an email to the notify_list folks

    <Returns>
        None.
    """
    integrationtestlib.log("in lookup_timedout()")
    notify_msg = "Centralized lookup failed -- lookup_timedout() fired after 30 sec."
    
    # wait for the event to be set, timeout after 30 minutes
    wait_time = 1800
    tstamp_before_wait = nonportable.getruntime()
    lookup_done_event.wait(wait_time)
    tstamp_after_wait = nonportable.getruntime()

    t_waited = tstamp_after_wait - tstamp_before_wait
    if abs(wait_time - t_waited) < 5:
        notify_msg += " And lookup stalled for over 30 minutes (max timeout value)."
    else:
        notify_msg += " And lookup stalled for " + str(t_waited) + " seconds"

    integrationtestlib.notify(notify_msg)
    return

def main():
    """
    <Purpose>
        Program's main.

    <Arguments>
        None.

    <Exceptions>
        All exceptions are caught.

    <Side Effects>
        None.

    <Returns>
        None.
    """
    # setup the gmail user/password to use when sending email
    success,explanation_str = send_gmail.init_gmail()
    if not success:
        integrationtestlib.log(explanation_str)
        sys.exit(0)
        
    key = random.randint(4,2**30)
    value = random.randint(4,2**30)
    ttlval = 60

    # put(key,value) with ttlval into the Centralized HT
    integrationtestlib.log("calling centralizedadvertise_announce(key: " + str(key) + ", val: " + str(value) + ", ttl: " + str(ttlval) + ")")
    try:
        centralizedadvertise_announce(key,value,ttlval)
    except:
        integrationtestlib.handle_exception("centralizedadvertise_announce() failed")
        sys.exit(0)

    # a 30 second timer to email the notify_list on slow lookups
    lookup_timedout_timer = threading.Timer(30, lookup_timedout)
    # start the lookup timer
    lookup_timedout_timer.start()

    # get(key) from the centralized HT
    integrationtestlib.log("calling centralizedadvertise_lookup(key: " + str(key) + ")")
    try:
        ret_value = centralizedadvertise_lookup(key)
        print ret_value
        # TODO: check the return value as well
        ret_value = int(ret_value[0])
        if (ret_value != value):
            integrationtestlib.handle_exception("ret_value is incorrect")
            print ("ret_value is incorrect")
    except:
        integrationtestlib.handle_exception("centralizedadvertise_lookup() failed")
        sys.exit(0)

    lookup_timedout_timer.cancel()
    lookup_done_event.set()
    return

if __name__ == "__main__":
    main()
    

