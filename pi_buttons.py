#!/usr/bin/env python
from subprocess import Popen, check_output
import pi_messages as pi_msg
import os
import RPi.GPIO as GPIO
import signal
import sys
import time
import urllib2

PADD_PID_FILE = '/home/pi/PADD.pid'
SCREEN = '/dev/tty1'

def check_root():
  if os.getuid() == 0:
    print('Running as root ' + u'[\u2713]')
  else:
    print('Run this as root (sudo)')
    sys.exit(1)

def gpio_setup(gpio_list):
  GPIO.setup(gpio_list, GPIO.IN, pull_up_down=GPIO.PUD_UP)
  for pin in gpio_list:
    GPIO.add_event_detect(pin, GPIO.RISING, callback=my_callback, bouncetime=600)

def backlight_status(backlight_file):
  with open(backlight_file, 'r') as b_file:
    # Strip the newline and cast to int
    status = int(b_file.read().strip('\n'))
  return status

def backlight_control(backlight, backlight_file):
  if backlight:
    print('Turning display off')
    with open(backlight_file, 'w') as b_file:
      b_file.write('0')
  else:
    print('Turning display on')
    with open(backlight_file, 'w') as b_file:
      b_file.write('1')

def get_padd_pid():
  with open(PADD_PID_FILE, 'r') as pid_f:
    padd_pid = int(pid_f.read().strip('\n'))
  return padd_pid

def download_padd(padd_url, padd_file):
  response = urllib2.urlopen(padd_url)
  html = response.read()
  with open(padd_file, 'w') as padd_f:
    padd_f.write(html)
  return response

def pid_signal(pid, n_signal):
  os.kill(pid, n_signal) 

def update_pihole():
  pid = get_padd_pid()
  pid_signal(pid, signal.SIGSTOP)
  with open(SCREEN, 'w') as tty:
    tty.write(pi_msg.update_pihole_msg)
    p = Popen(['pihole', '-up'], stdout=tty)
  time.sleep(10)
  pid_signal(pid, signal.SIGCONT)

def update_padd():
  padd_url='https://raw.githubusercontent.com/jpmck/PADD/master/padd.sh'
  padd_dst='/home/pi/padd.sh'
  pid = get_padd_pid()
  pid_signal(pid, signal.SIGSTOP)
  with open(SCREEN, 'w') as tty:
    tty.write(pi_msg.update_padd_msg)
    ret = download_padd(padd_url, padd_dst)
    tty.write('Return code: %s, msg: %s' % (ret.code, ret.msg))
    tty.write('Restarting PADD...')
  pid_signal(pid, signal.SIGCONT)
  pid_signal(pid, signal.SIGTERM)

def print_help():
  pid = get_padd_pid()
  pid_signal(pid, signal.SIGSTOP)
  with open(SCREEN, 'w') as tty:
    tty.write(pi_msg.help_msg)
  time.sleep(10)
  pid_signal(pid, signal.SIGCONT)

def my_callback( button_input ):
  backlight_file = '/sys/class/backlight/soc:backlight/brightness'
  if button_input == 27:
    status = backlight_status(backlight_file)
    backlight_control(status, backlight_file)
  # For the rest if the backlight is off turn it on. I mean, you
  # need to see the run.
  elif button_input == 23:
    status = backlight_status(backlight_file)
    if status:
      print('Updating pi-hole')
      update_pihole()
    else:
      backlight_control(status, backlight_file)
  elif button_input == 22:
    status = backlight_status(backlight_file)
    if status:
      print('Update PADD')
      update_padd()
    else:
      backlight_control(status, backlight_file)
  elif button_input == 17:
    status = backlight_status(backlight_file)
    if status:
      print('Print help')
      print_help()
    else:
      backlight_control(status, backlight_file)

def signal_handler(sig, frame):
  print('You pressed Ctrl+C!')
  GPIO.cleanup()
  sys.exit(2)

def main():
  check_root()
  GPIO.setmode(GPIO.BCM)
  # Pin 17 is mentioned as pin 18 in the TFT docs.
  gpio_list = [17, 22, 23, 27]
  gpio_setup(gpio_list)
  signal.signal(signal.SIGINT, signal_handler)
  print('Press Ctrl+C to quit')
  signal.pause()
  while True:
    time.sleep(1)
  GPIO.cleanup()

if __name__ == '__main__':
  main()
