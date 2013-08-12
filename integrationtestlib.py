"""
<Program Name>
  log_and_notify.py
  
<Started>
  June 27th, 2009
  
<Author>
  Monzur Muhammad
  monzum@cs.washington.edu
 
<Purpose>
  The purpose of this file is to log msgs that any program wants to log, notify admins if 
  anything is down and the admins need to be notified. The admins may also be emailed the
  the traceback of the program.

<Usage>
  This is more like a library for the integration tests, usually this file is imported
  in order to use its functionalities
"""

import send_gmail
import traceback
import time
import socket
import sys

# the people to notify on failure/if anything goes wrong
notify_list = ["jcappos@poly.edu", "monzum@u.washington.edu", "gppressi@gmail.com", "leon.wlaw@gmail.com", "hermanchchen@gmail.com"]


def log(msg):
  """
  <Purpose>
    Prints a particularly formatted log msg to stdout

  <Arguments>
    msg, the text to print out

  <Exceptions>
    None.

  <Side Effects>
    Prints a line to stdout.

  <Returns>
    None.
  """
  print time.ctime() + " : " + msg
  return  
  
  
  
def notify(text, subject):
  """
  <Purpose>
    Send email with message body text to the members of the notify_list

  <Arguments>
    text, the text of the email message body to be generated

  <Exceptions>
    None.

  <Side Effects>
    Sends email.

  <Returns>
    None.
  """
  try:
    hostname = socket.gethostname()
  except:
    hostname = "unknown host"
  else:
    try:
      hostname = socket.gethostbyname_ex(hostname)[0]
    except:
      pass
  subject = subject + " @ "+ hostname + " : " + sys.argv[0]
  
  for emailaddr in notify_list:
    log("notifying " + emailaddr)
    send_gmail.send_gmail(emailaddr, subject, text, "")
	
  return

  
  
def handle_exception(text, subject):
  """
  <Purpose>
    Handles an exception with descriptive text.

  <Arguments>
    text, descriptive text to go along with a generated exception

  <Exceptions>
    None.

  <Side Effects>
    Logs the exception. Notifies people via email. 

  <Returns>
    None.
  """
  # log the exception
  text = "Exception: " + text + "\n"
  log(text)
  text = "[" + time.ctime() + "]" + text
  print '-'*60
  traceback.print_exc(file=sys.stdout)
  print '-'*60

  # build the exception traceback string
  error_type, error_value, trbk = sys.exc_info()
  # use traceback max recursion depth of 6
  tb_list = traceback.format_tb(trbk, 6)
  exception_traceback_str = "Error: %s \nDescription: %s \nTraceback:" % (error_type.__name__, error_value)
  for i in tb_list:
    exception_traceback_str += "\n" + i
    
  # notify folks via email with the traceback of the exception
  notify(text + exception_traceback_str, subject)

  return
