"""
<Program Name>
  selexor_active.py

<Purpose>
  Attempts to acquire and release vessels via selexor.

<Usage>
  Modify the following global var params to have this script functional:
  - notify_list, a list of strings with emails denoting who will be
    emailed when something goes wrong

  This script takes no arguments. A typical use of this script is to
  have it run periodically using something like the following crontab line:
  7 * * * * /usr/bin/python /home/seattle/centralizedputget.py > /home/seattle/cron_log.centralizedputget
"""

import urllib
import send_gmail
import integrationtestlib
import urllib2
import subprocess


import repyhelper
repyhelper.translate_and_import('serialize.repy')


username = 'selexor_monitor'
apikey = '1X3YFBLPTKVSI8DQHWJZ0NR92645ECUA'

userdata = {username: {'apikey': apikey}}

ERROR_EMAIL_SUBJECT = "Selexor monitoring test failure!"
SELEXOR_PAGE = "https://selexor.poly.edu:8888/"


def retrieve_url(url, data=None):
  print "retrieve_url"
  args = ["curl", url, "--insecure"]
  if data:
    args += ['--data', '"'+data+'"']
  print "download_process"
  download_process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  print "downloadwait"
  download_process.wait()
  #print "communicate download: " + str(download_process.communicate()[0])
  #print download_process.communicate()[0]
  # Return the output of the URL download
  #print "communicate download: " + download_process.communicate()[0]
  return download_process.communicate()[0]


def test_selexor_alive():
  response_text = retrieve_url(SELEXOR_PAGE)
  if not response_text:
    raise Exception("Server returned no data!")

  if "404 Not Found" in response_text:
    raise Exception("Server reported 404 Not Found!")


def test_selexor_acquire():
  """
  <Purpose>
    Tests to make sure that users can acquire vessels.

  <Arguments>
    None

  <Side Effects>
    Acquires a single vessel on the user's behalf.

  <Exceptions>
    None

  <Return>
    The vessel dictionary of the acquired vessel.  This can be used to
    is how selexor references each vessel.
  """
  get_one_vessel = {
    '0': {
      'id': 0.0, 'allocate': '1', 'rules': {
        'port': {'port': '63139'}
      }}}
  requestinfo = {'request': {
    'userdata': userdata,
    'groups': get_one_vessel
    }}
  print "Mark0"
  print userdata
  response_text = retrieve_url(SELEXOR_PAGE,
    data=serialize_serializedata(requestinfo))
  print "Mark1"
  query_response = serialize_deserializedata(response_text)
  if query_response['data']['status'] != 'working':
    raise Exception("Failed to submit request! Response: " + str(query_response))
  print "Mark2"
  query = {'query': {
    'userdata': userdata
  }}
  while query_response['data']['status'] == 'working':
    # Give selexor some time to do its processing...
    sleep(10)
    response_text = retrieve_url(SELEXOR_PAGE,
      data=serialize_serializedata(query)).read()
    query_response = serialize_deserializedata(response_text)

  if query_response['data']['status'] != 'complete':
    raise Exception("Acquiring one vessel failed! response: " + str(query_response))

  return query_response['data']['groups']['0']


def test_selexor_release(vessel_dict):
  """
  <Purpose>
    Tests to make sure that users can release vessels.

  <Arguments>
    vessel_dict: A dictionary representing a single vessel to release.

  <Side Effects>
    Releases the vessel specified.

  <Exceptions>
    None

  <Return>
    None
  """
  userdata = {'leonwlaw': {'apikey': 'AHXRZ2D4FMU0SJPGKTNCLQ8VIE691WB5'}}
  requestinfo = {'request': {
    'userdata': userdata,
    'vessels': [vessel_dict]
    }}

  response_text = urllib.urlopen(SELEXOR_PAGE,
    data=serialize_serializedata(requestinfo)).read()


def main():
  send_gmail.init_gmail()

  try:
    if username is None or apikey is None:
      raise Exception("Username and/or API key is not set!")

    #test_selexor_alive()
    # Not working, might be that selexor's not performing HTTP requests
    # correctly
    acquired_vessel = test_selexor_acquire()
    # test_selexor_release(acquired_vessel)
  except:
    print("integrationtestlib.handle_exception(Exception occurred when contacting selexor, ERROR_EMAIL_SUBJECT)")
    exit()


if __name__ == "__main__":
  main()

