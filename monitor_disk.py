"""
<Program Name>
  monitor_disk.py

<Author>
  Monzur Muhammad
  monzum@cs.washington.edu

<Usage>
  python monitor_disk.py
"""

import os
import sys
import socket
import subprocess
import send_gmail
import irc_seattlebot
import integrationtestlib


def main():


  success,explanation_str = send_gmail.init_gmail()
  #integrationtestlib.notify_list=['monzum@gmail.com']
  if not success:
    integrationtestlib.log(explanation_str)
    sys.exit(0)

  command = "df -h | grep '/dev/sda' | awk '{print $5}'"
  command_output_fd = os.popen(command)

  # Get the output and get rid of the extra lines and % sign.
  disk_use_percent = int(command_output_fd.read().split()[0][:-1])
  command_output_fd.close()

  disk_free_command = "df -h | grep '/dev/sda' | awk '{print $4}'"
  disk_free_fd = os.popen(disk_free_command)
  free_space = disk_free_fd.read()
  disk_free_fd.close()

  hostname = socket.gethostname() + ".poly.edu"
  subject = "High disk usage"

  if disk_use_percent >= 95:
    message = "CRITICAL: Very High Disk Usage on %s: %s percent used.\n" % ( hostname, disk_use_percent)
    message += "Disk space free: %s" % free_space
    integrationtestlib.log(message)
    integrationtestlib.notify(message, subject)
    irc_seattlebot.send_msg(message)

  elif disk_use_percent > 90:
    message = "WARNING: High disk usage on %s: %s percent used.\n" % ( hostname, disk_use_percent)
    message += "Disk space free: %s" % free_space
    integrationtestlib.log(message)
    integrationtestlib.notify(message, subject)

  
  print "Current disk usage: %s percent" % disk_use_percent
  print "Free disk space: %s" % free_space



if __name__ == "__main__":
  main()
