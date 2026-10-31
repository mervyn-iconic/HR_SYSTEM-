"""Interactive local launcher; does not store the administrator's password."""
import getpass
import os
import secrets
import socket
import threading
import time
import webbrowser

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    port=int(os.environ.get('PORT','5000'))
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1',port))==0:
            print(f'Port {port} is already in use. Stop the previous app or choose another PORT.')
            return
    print('\nGolden Marketing | HR Management | UI 20261031.1\n')
    print('Installation: '+os.path.dirname(os.path.abspath(__file__)))
    if not os.environ.get('HR_ADMIN_PASSWORD'):
        while True:
            password=getpass.getpass('Choose your administrator password (at least 12 characters): ')
            if len(password)<12:
                print('Use at least 12 characters.');continue
            if password!=getpass.getpass('Confirm password: '):
                print('Passwords did not match. Try again.');continue
            os.environ['HR_ADMIN_PASSWORD']=password
            break
    os.environ.setdefault('SECRET_KEY',secrets.token_hex(32))
    from app import app
    url=f'http://127.0.0.1:{port}'
    def open_when_ready():
        for _ in range(100):
            with socket.socket() as probe:
                if probe.connect_ex(('127.0.0.1',port))==0:
                    webbrowser.open(url);return
            time.sleep(.1)
    threading.Thread(target=open_when_ready,daemon=True).start()
    print(f'\nOpening {url}\nKeep this window open. Press Ctrl+C to stop.\n')
    app.run(host='127.0.0.1',port=port,debug=False)
if __name__=='__main__':main()
