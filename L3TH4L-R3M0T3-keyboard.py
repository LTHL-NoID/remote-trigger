import os
import socket
import ctypes
import datetime
import threading
import subprocess
import PySimpleGUI as sg
from pynput.keyboard import Listener as KeyboardListener, Key

# vars
PORT = 13376
target_ip = ''
listener = None
update_state = False
save_dir = (r'C:\ProgramData\L3TH4L-R3M0T3')
config = (r'C:\ProgramData\L3TH4L-R3M0T3\L3TH4L-R3M0T3.cfg')
log = (r'C:\ProgramData\L3TH4L-R3M0T3\L3TH4L-error.log')
icon_path = (r'C:\ProgramData\L3TH4L-R3M0T3\appIcon.ico')
normal = (r'C:\ProgramData\L3TH4L-R3M0T3\normal.png')
muted = (r'C:\ProgramData\L3TH4L-R3M0T3\muted.png')
unmuted = (r'C:\ProgramData\L3TH4L-R3M0T3\unmuted.png')
#key_binding = None

# Save log error 
def error_log(info):
     timestamp = datetime.datetime.now().strftime("%d/%m/%Y - %H:%M:%S")
     with open(log, 'w') as file:
          file.write(f"{timestamp} - {str(info)}\n")

# Check previous saved config and load key variables based on info eg. target_ip and key_binding, then return these values for use later.
def check_config():
    if os.path.exists(config):
        with open(config, 'r') as file:
            target_ip = file.readline().strip()
            key_binding = file.readline().strip()
            return target_ip, key_binding
        print('Loaded values')
    else:
        target_ip = resolve_address()
        key_binding = None  # No key_binding set by default if config doesn't exist
        return key_binding, target_ip

# Save configuration (IP address and key_binding)
def save_config(ip, key_binding):
    if key_binding is None:
        key_binding = 'Not Set'
    with open(config, 'w') as f:
        f.write(f"{ip}\n{key_binding}\n")
    print(f"Configuration saved: Address: {ip}, Key:{key_binding}")
    
# Grab local ipv4 address
def resolve_address():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as host:
            host.connect(('1.1.1.1', 1))
            return host.getsockname()[0]
    except Exception as e:
        error_log('Unable to resolve host: ' + str(e))
        
# On d/c notify the listener on the other computer
def on_disconnect():
    timestamp = datetime.datetime.now().strftime("%d/%m/%Y - %H:%M:%S")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.015)
            s.connect((target_ip, PORT))
            s.sendall(b'Disconnected @'+ timestamp)
            listener.stop()
    except Exception:
        error_log('Unable to resolve host: on_disconnect')
        
    window['-OUTPUT-'].update('L3TH4L-L1573N Disconnected.')
    window['-IMAGE-'].update(filename=normal)
    window.refresh()
    
# Sanitise user input and ping target to see if it is online, attempt to send connected message
def validate_ip(target_ip, local_ip):
        allowed = '.'
        target_octets = target_ip.split('.')
        local_octets = local_ip.split('.')
        if len(target_octets) != 4:# or not all (octet.isdigit() and 1 <= int(octet) <= 254 for octet in target_octets):
            window['-OUTPUT-'].update('Invalid IP address!')
            return False
        elif target_octets[-1] in ['0', '1', '255']:
            window['-OUTPUT-'].update('0, 1 & 255 cannot be used.')
            return False
        elif target_octets[:3] != local_octets[:3]:
           window['-OUTPUT-'].update("First 3 octets don't match!")
           return False
        elif any(not (char.isdigit() or char == '.') for octet in target_octets for char in octet):
            window['-OUTPUT-'].update("Invalid characters in IP address!")
            return False
        else:
            try:
                result = subprocess.run(['ping', '-n', '1', '-w', '250', target_ip],
                                        capture_output=True,
                                        text=True,
                                        check=True,
                                        shell=True)
                online = 'Reply from' in result.stdout
                if online:
                     window['-OUTPUT-'].update(f'Target {target_ip} is Online!')
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(0.015)
                        s.connect((target_ip, PORT))
                        s.sendall(b'Connected!')
                except Exception:
                    error_log('Unable to resolve host during validate_ip')
                    window['-OUTPUT-'].update(f'Target is offline ¯\\_(ツ)_/¯')  
                return online
            except subprocess.CalledProcessError:
                window['-OUTPUT-'].update(f'Target is offline ¯\\_(ツ)_/¯')
                
                
# Test if listener is listening on the correct ip/port
def is_port_open(ip, PORT):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.015)
            s.connect((ip, PORT))
        return True
    except (socket.timeout, ConnectionRefusedError):
        return False
       

def on_key_press(key):
    global key_binding, target_ip, update_state
    
    try:
        # Check if the key is a regular key
        if hasattr(key, 'char') and key.char is not None:
            key_char = key.char
        else:
            # For special keys, convert them into a string that can be compared
            key_char = str(key).replace("Key.", "").lower()  # Convert to lower to handle case insensitivity

        # Check if the pressed key matches the bound key
        if key_char == key_binding:
            target_ip = str(window['-IP-'].get())
            try:
                # Check if the key_binding is set and send data based on state
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.015)
                    s.connect((target_ip, PORT))
                    update_state = not update_state
                    if update_state:
                        window['-OUTPUT-'].update('Muted Mic.')
                        window.write_event_value('UPDATE_IMAGE', 'muted')
                        s.sendall(b'Muted.')
                    else:
                        window['-OUTPUT-'].update('Unmuted Mic.')
                        window.write_event_value('UPDATE_IMAGE', 'unmuted')
                        s.sendall(b'Unmuted.')
            except Exception as e:
                print('on_key_press() failed')
                print(e)
                window['-OUTPUT-'].update("Error check log")
    except Exception as e:
        print(f"Error in on_key_press: {e}")

# Ensure 'key_binding' is updated globally in on_press
def on_press(key):
    global key_binding  # Add this to update the global variable
    try:
        pressed_key = key.char  # capture the key pressed
    except AttributeError:
        if key == Key.space:
            pressed_key = 'Space'
        else:
            pressed_key = str(key).strip("Key.")  # special keys

    key_binding = pressed_key  # Update global key_binding
    window.write_event_value('-KEYBIND_UPDATE-', f'{key_binding}')  # Update window with the key_binding
    print(f"key_binding updated to: {key_binding}")  # Debugging line

    return False  # Stop the listener after capturing the key

# Create pySimpleGUI window layout
def create_window():
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('L3TH4L-R3M0T3')
    sg.ChangeLookAndFeel('DarkGrey1')

    image_size = (100, 100)
    image_column = [
        [sg.Image(normal, key='-IMAGE-', size=image_size, expand_x=True, expand_y=True)]
    ]

    text_column = [
        [sg.Text('Your local address is: ' + resolve_address(), text_color=('black'))],
        [sg.Text('Set remote computer ip:', text_color=('black'))] + [sg.Input(check_config()[0], size=(15), key='-IP-', text_color=('black'))],
        [sg.Text('Key binding', text_color=('black'))] + [sg.Text(check_config()[1] if check_config()[1] else 'Not set', size=7, key='-KEYBIND-', text_color=('black'))],
        [sg.Text('Status: ', size=(5, 1), text_color=('black'))] + [sg.Text('Waiting for connection...', key='-OUTPUT-', text_color=('black'))]
    ]

    layout = [
        [sg.Frame('', text_column, element_justification='left', border_width=0),
         sg.Frame('', image_column, element_justification='right', border_width=0)],
        [sg.Button('Connect', button_color=('black')),
         sg.Button('Bind Key', button_color=('black')),
         sg.Button('Save', button_color=('black')),
         sg.Button('Quit/Disconnect', button_color=('black'))]
    ]

    window = sg.Window("L3TH4L-R3M0T3",
                       layout,
                       icon=icon_path,
                       finalize=True,
                       resizable=False)
    return window

# Function to start keyboard listener in a separate thread
def start_key_listener():
    with KeyboardListener(on_press=on_press) as listener:
        listener.join()  # Wait for key press
        
# This will handle listening for the key_binding once the connection is made
def start_key_listener_for_loop():
    while True: 
        if key_binding:  # Check if the key_binding is set
            with KeyboardListener(on_press=on_key_press) as listener:
                listener.join()  # Start listening for key events

# Main event listener
def main():
    global listener
    while True:
        event, values = window.read()

        # Handle the image update event from the listener thread
        if event == 'UPDATE_IMAGE':
            new_state = values[event]
            if new_state == 'muted':
                window['-OUTPUT-'].update('Muted Mic.')
                window['-IMAGE-'].update(filename=muted)
            else:
                window['-OUTPUT-'].update('Unmuted Mic.')
                window['-IMAGE-'].update(filename=unmuted)
            
        # Handle the key_binding update event
        if event == '-KEYBIND_UPDATE-':
            window['-KEYBIND-'].update(values[event])

        # On connect press, test and if successful start the listener
        if event == 'Connect':
            window['-OUTPUT-'].set_focus()
            target_ip = str(values['-IP-'])
            validate_ip(target_ip, local_ip)
            window['-OUTPUT-'].update('Connected to L3TH4L-L1573N.')
            
            if key_binding == None:
                window['-OUTPUT-'].update('No key bound. Please bind key first!')
            elif is_port_open(target_ip, PORT):
                    if listener is None:
                        listener_on = KeyboardListener(on_press=on_key_press)  # Start the key listener in a new thread
                        listener_on.start() 
            else:
                window['-OUTPUT-'].update(f"Target is offline ¯\\_(ツ)_/¯")

        # On bind key press, start key listener in a new thread
        if event == 'Bind Key':
            threading.Thread(target=start_key_listener, daemon=True).start()
            window['-KEYBIND-'].update('')
            window['-KEYBIND-'].set_focus()
            save_config(str(values['-IP-']), key_binding)

        # Save config
        if event == 'Save':
            save_config(str(values['-IP-']), key_binding)

        # Quit event, disconnect and stop listener
        if event == "Quit/Disconnect" or event == sg.WIN_CLOSED:
            on_disconnect()
            if listener:
                listener.stop()
            listener = None
            break
    window.close()

if __name__ == '__main__':
    global key_binding  # Ensure we are using the global variable
    target_ip, key_binding = check_config()  # Load from config when the program starts

    # Now you can use key_binding in your program
    print(f"Loaded Key Binding: {key_binding}")
    window = create_window()
    window.set_icon(icon_path)
    local_ip = resolve_address()
    main()
