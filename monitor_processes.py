"""
<Program Name>
  monitor_processes.py
  
<Started>
  June 9, 2009
  
<Author>
  Monzur Muhammad
  monzum@u.washington.edu
"""

import subprocess
import sys
import send_gmail
import irc_seattlebot
import integrationtestlib
import traceback
import time
import socket



def monitor_processes(monitor_process_list, command_list, machine_name):
  """
  <Purpose>
    Checks to make sure that the critical processes on the machine 'seattle' are still running

  <Exceptions>
    None

  <Arguments>
    monitor_process_list - a list of all the critical processes that should be checked to 
      see if they are up and running.

    command_list - a list of all the commands required to find all the relevant processes

  <Return>
    None
  """
  
  #string that holds the name of all the processes that are found to be running using the
  #ps commands that was passed in as argument
  processes_string=""

  integrationtestlib.log("Starting monitoring process on "+machine_name)  

  #run a command on the linux machine to find all the relevant processes
  for command in command_list:
    try:
      relevant_processes, command_error = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE).communicate() 
    except:
      integrationtestlib.handle_exception("Failed to run command: "+command)
      sys.exit(1)

    #make a string of all the processes
    processes_string = processes_string+relevant_processes
  print processes_string 
  #keeps track to see if any processes are down 
  critical_process_down=False
  error_message="WARNING: Critical processes down! Seattle developers please start the processes up as soon as possible\n"
  error_message=error_message+"Listing processes that are down:\n"

  #goes through the list of monitor_process_list to ensure that all processes are running
  for critical_process in monitor_process_list:
    integrationtestlib.log("Checking process: "+critical_process+".......")
    if not critical_process in processes_string:
      critical_process_down=True
      error_message = error_message+critical_process+" is down on "+machine_name+".cs.washington.edu\n"
      print "FAIL"

    else:
      print "PASS"
  error_message=error_message+"end of list of processes that are down.\n................................"

  if critical_process_down:
    integrationtestlib.notify(error_message, "Critical process down!")
    irc_seattlebot.send_msg(error_message)

  else:
    integrationtestlib.log("All critical processes on "+machine_name+" are up and running")

  print(".........................................................")


def main():
  """
  <Purpose>
    Runs at regular time intervals to make sure that critical processes on a machine
    are still up and running. If a critical process is not running then system admins
    are sent an email, as well as a message is posted on the IRC.
	
  <Exceptions>
    None

  <Usage>
    This script takes no arguments. A typical use of this script is to
    have it run periodically using something like the following crontab line:  
	
    */15 * * * * export GMAIL_USER='username' && export GMAIL_PWD='password' && /usr/bin/python /home/seattle/monitor_scripts/monitor_processes.py > 
    /home/seattle/monitor_scripts/cron_log.monitor_processes
  """
  
  # setup the gmail user/password to use when sending email
  success,explanation_str = send_gmail.init_gmail()
  if not success:
    integrationtestlib.log(explanation_str)
    sys.exit(0)  

  #integrationtestlib.notify_list.append("gppressi@gmail.com")
  #processes that should be running on seattle server
  seattle_process_list=['advertiseserver.py']	

  #The commands that should be run on seattle to get all the required processes
  seattle_command = ["ps auwx | grep python | grep -v grep | grep geni | awk '{print $14}'"]

  #processes that should be running on seattleclearinghouse server
  seattleclearinghouse_process_list=['transition_donation_to_canonical.py', 'transition_onepercentmanyevents_to_canonical.py', 'transition_canonical_to_twopercent.py', 'transition_twopercent_to_twopercent.py', 'check_active_db_nodes.py', 'apache2', '/usr/sbin/mysqld', 'backend_daemon.py', 'lockserver_daemon.py']

  #The commands that should be run on seattleclearinghouse to get all the required processes  
  seattleclearinghouse_command = ["ps auwx | grep python | grep -v grep | grep clearinghouse | awk '{print $12}'"]
  seattleclearinghouse_command.append("ps auwx | grep apache | grep -v grep | grep root | awk '{print $11}'")
  seattleclearinghouse_command.append("ps auwx | grep mysqld | grep -v grep | awk '{print $11}'")
  seattleclearinghouse_command.append("ps auwx | grep python | grep -v grep | grep justinc | awk '{print $12}'")
 
  #run monitor processes with the right command
  if sys.argv[1] == '-seattle':
    monitor_processes(seattle_process_list, seattle_command, "seattle")
  elif sys.argv[1] == '-seattleclearinghouse':
    monitor_processes(seattleclearinghouse_process_list, seattleclearinghouse_command, "seattleclearinghouse")

	
	
if __name__ == "__main__":
  main()
