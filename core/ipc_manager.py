import os
import time
import threading
import win32pipe
import win32file
import pywintypes
import json
from typing import Optional

class IPCServer:
    PIPE_NAME = r'\\.\pipe\auto_clicker'
    BUFFER_SIZE = 4096
    
    def __init__(self, clicker):
        self.clicker = clicker
        self.server_thread = None
        self.running = False
        
    def start(self):
        if self.running:
            return
        self.running = True
        self.server_thread = threading.Thread(target=self._run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        
    def stop(self):
        self.running = False
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=1)
            
    def _run_server(self):
        while self.running:
            handle = None
            try:
                handle = win32pipe.CreateNamedPipe(
                    self.PIPE_NAME,
                    win32pipe.PIPE_ACCESS_DUPLEX,
                    win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                    win32pipe.PIPE_UNLIMITED_INSTANCES,
                    self.BUFFER_SIZE,
                    self.BUFFER_SIZE,
                    0,
                    None
                )
                
                win32pipe.ConnectNamedPipe(handle, None)
                client_thread = threading.Thread(target=self._handle_client, args=(handle,))
                client_thread.daemon = True
                client_thread.start()
                
            except pywintypes.error as e:
                if handle:
                    win32file.CloseHandle(handle)
                if e.winerror != 231:  # All pipe instances are busy
                    logging.error(f"IPC server error: {e}")
                    time.sleep(1)  # Longer delay after error
                    continue
                time.sleep(0.1)
            except Exception as e:
                if handle:
                    win32file.CloseHandle(handle)
                logging.error(f"Unexpected IPC server error: {e}")
                time.sleep(1)  # Longer delay after error
                
    def _handle_client(self, handle):
        try:
            while self.running:
                try:
                    result, data = win32file.ReadFile(handle, self.BUFFER_SIZE)
                    if not data:
                        break
                        
                    try:
                        message = json.loads(data.decode('utf-8'))
                        response = self._process_message(message)
                        win32file.WriteFile(handle, json.dumps(response).encode('utf-8'))
                    except (json.JSONDecodeError, KeyError):
                        win32file.WriteFile(handle, b'{"error": "Invalid message format"}')
                        
                except pywintypes.error as e:
                    if e.winerror == 232:  # Pipe disconnected
                        break
                    raise
                    
        finally:
            win32file.CloseHandle(handle)
            
    def _process_message(self, message):
        action = message.get('action')
        
        if action == 'start':
            interval = message.get('interval', 0.1)
            duration = message.get('duration')
            self.clicker.start_clicking(interval, duration)
            return {'status': 'started'}
            
        elif action == 'stop':
            self.clicker.stop_clicking()
            return {'status': 'stopped'}
            
        elif action == 'status':
            return {
                'is_clicking': self.clicker.is_clicking,
                'interval': self.clicker.interval,
                'duration': self.clicker.duration
            }
            
        return {'error': 'Unknown action'}
