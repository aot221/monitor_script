"""
<Program Name>
  send_gmail.py

<Started>
  December 17, 2008

<Author>
  ivan@cs.washington.edu
  Ivan Beschastnikh

<Purpose>
  Sends an email using an existing gmail account

<Usage>
  This script can be run from the command line to generate a test
  email. The command line usage is:
  $ python seng_gmail.py [gmail_user] [gmail_pwd] [to] [subj] [body] [attach]
  Where all the arguments are strings and attach is a path to a
  readable file or is missing (for no attachment).

  As an import, this file should be used as follows:

  Fist, initialize the global username and password variables by
  calling init_gmail(gmail_user,gmail_pwd).

  Second, use send_gmail(to,subject,text,attach) to send emails.
"""

import os
import traceback
import sys

import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email import Encoders

GMAIL_USER=""
GMAIL_PWD=""

gmail_file_name = "/home/monzum/monitor_script/seattle_gmail_info"

def init_gmail(gmail_user="", gmail_pwd="", gmail_user_shvarname="GMAIL_USER", gmail_pwd_shvarname="GMAIL_PWD"):
    """
    <Purpose>
        Sets up the global variables GMAIL_USER and GMAIL_PWD for use by send_gmail()

    <Arguments>
        gmail_user (optional) :
                gmail username to use
        gmail_pwd (optional):
                gmail password for gmail_user
        gmail_user_shvarname (optional):
                if gmail_user is "" then this specifies the shell
                variable name to use for extracting the gmail username
        gmail_pwd_shvarname (optional):
                if gmail_pwd is "" then this specifies the shell
                variable name to use for extracting the gmail password
    <Exceptions>
        None

    <Side Effects>
        Sets GMAIL_USER and GMAIL_PWD global variables

    <Returns>
        (True, "") on success and (False, explanation) on failure,
        where explanation is a string explaining what went wrong
    """
    global GMAIL_USER
    global GMAIL_PWD

    gmail_user_info = {}

    # Get full file path
    file_path = os.path.join(os.getcwd(), gmail_file_name)

    if os.path.isfile(file_path):
      gmail_file_object = open(file_path, 'r')
      print 'read file ' + file_path 
      gmail_user_info = eval(gmail_file_object.read())
     
      GMAIL_USER = gmail_user_info['GMAIL_USER']
      GMAIL_PWD = gmail_user_info['GMAIL_PWD']     
      print 'loaded gmail info'  
    else:
      return False, "Make sure the file '" + gmail_file_name + "' is in the current directory"         

    return True, ""


def send_gmail(to, subject, text, attach):
    """
    <Purpose>
        Sends an email to 'to' with subject 'subject' with text 'test'
        and attachment filename 'attach'. Uses the gmail account
        specified by GMAIL_USER and GMAIL_PWD global variables.

        GMAIL_USER and GMAIL_PWD must be set up with init_gmail()
        prior to calling this function.

    <Arguments>
        to:
                who to send the email to, an email address string
        subject:
                the string subject line of the email
        text:
                the string text body of the email
        attach:
                the filename to attach to the message

    <Exceptions>
        Not sure?

    <Side Effects>
        Sends an email through gmail to a recipient.

    <Returns>
        (True,"") on succes, (False,explanation) on failure, where
        explanation contains the string explaining the failure
    """
    if GMAIL_USER is "":
        return False, "GMAIL_USER not set, did you run init_gmail()?"
    if GMAIL_PWD is "":
        return False, "GMAIL_PWD not set, did you run init_gmail()?"
    
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = to
    msg['Subject'] = subject

    msg.attach(MIMEText(text))

    if attach != "":
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(open(attach, 'rb').read())
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition',
                        'attachment; filename="%s"' % os.path.basename(attach))
        msg.attach(part)

    mailServer = smtplib.SMTP("smtp.gmail.com", 587)
    mailServer.ehlo()
    mailServer.starttls()
    mailServer.ehlo()

    try:
        mailServer.login(GMAIL_USER, GMAIL_PWD)
    except smtplib.SMTPAuthenticationError, (code,resp):
        return False, str(code) + " " + str(resp)
    
    mailServer.sendmail(GMAIL_USER, to, msg.as_string())

    # Should be mailServer.quit(), but that crashes...
    mailServer.close()
    return True, ""

if __name__ == "__main__":
    if len(sys.argv) != 6 and len(sys.argv) != 7:
        print "usage:", sys.argv[0], "[gmail_user] [gmail_pwd] [to] [subj] [body] [optional:attach]"
        sys.exit(0)
    

    gmail_user = sys.argv[1]
    gmail_pwd = sys.argv[2]
    to = sys.argv[3]
    subj = sys.argv[4]
    body = sys.argv[5]

    if len(sys.argv) == 6:
        attach = ""
    else:
        attach = sys.argv[6]
    
    succes, explain_str = init_gmail(gmail_user, gmail_pwd)
    if not succes:
        print explain_str
        sys.exit(0)
        
    success, explain_str = send_gmail(to,subj,body,attach)
    if not success:
        print explain_str
        sys.exit(0)
        
    print "sent"
    
