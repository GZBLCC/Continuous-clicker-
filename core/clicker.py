import logging
import time
import threading
import random
from pynput import mouse, keyboard
from utils.key_mapper import KeyMapper
from .ipc_manager import IPCServer

class Clicker:
    def __init__(self):
        self.interval = 0.1
        self.duration = None
        self.mouse_button = None
        self.key = None
        self.key_start = ''
        self.key_stop = ''
        self.is_clicking = False
        self.random_area = None  # (x1, y1, x2, y2)
        self.keyboard_listener = None
        self.mouse_controller = mouse.Controller()
        self.key_mapper = KeyMapper()
        self.global_listener = None
        self.ipc_server = IPCServer(self)
        self.ipc_server.start()
        self.stop_event = threading.Event()
        self.lock = threading.Lock()

    def __del__(self):
        self.stop_clicking()
        self.stop_global_listener()
        if self.ipc_server:
            self.ipc_server.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.mouse_controller:
            del self.mouse_controller

    def start_clicking(self, interval=None, duration=None):
        if self.is_clicking:
            return
        if interval is not None:
            self.interval = interval
        if duration is not None:
            self.duration = duration
        self.is_clicking = True
        self.stop_event.clear()
        self.click_thread = threading.Thread(target=self._click_loop)
        self.click_thread.start()

    def stop_clicking(self):
        self.is_clicking = False
        self.stop_event.set()
        try:
            if self.click_thread and self.click_thread.is_alive():
                self.click_thread.join(timeout=1)
                if self.click_thread.is_alive():
                    logging.warning("Click thread did not terminate cleanly")
        except Exception as e:
            logging.error(f"Error stopping click thread: {e}")
            raise

    def _click_loop(self):
        start_time = time.perf_counter()
        try:
            while self.is_clicking and not self.stop_event.is_set():
                try:
                    if self.key:
                        mods, key_name = self.parse_modifiers(self.key)
                        for mod in mods:
                            mod_key = getattr(keyboard.Key, mod, None)
                            if mod_key:
                                self.keyboard_controller.press(mod_key)
                        
                        if len(key_name) == 1:
                            self.keyboard_controller.press(keyboard.KeyCode.from_char(key_name))
                            self.keyboard_controller.release(keyboard.KeyCode.from_char(key_name))
                        elif key_name in self.key_mapper.KEY_MAP.values():
                            self.keyboard_controller.press(getattr(keyboard.Key, key_name))
                            self.keyboard_controller.release(getattr(keyboard.Key, key_name))
                        else:
                            self.keyboard_controller.press(keyboard.KeyCode.from_char(key_name))
                            self.keyboard_controller.release(keyboard.KeyCode.from_char(key_name))
                        
                        for mod in mods:
                            mod_key = getattr(keyboard.Key, mod, None)
                            if mod_key:
                                self.keyboard_controller.release(mod_key)
                    elif self.mouse_button:
                        button = getattr(mouse.Button, self.mouse_button)
                        if self.random_area:
                            try:
                                x1, y1, x2, y2 = self.random_area
                                x = random.uniform(x1, x2)
                                y = random.uniform(y1, y2)
                                self.mouse_controller.position = (x, y)
                                self.mouse_controller.click(button)
                            except Exception as e:
                                logging.error(f"Random area error: {e}")
                                self.stop_clicking()
                        else:
                            self.mouse_controller.click(button)

                    time.sleep(self.interval)
                    
                    if self.duration and time.perf_counter() - start_time >= self.duration:
                        self.stop_clicking()
                except Exception as e:
                    logging.error(f"Click error: {e}")
                    self.stop_clicking()
                    break
        except Exception as e:
            logging.error(f"Click loop error: {e}")
            self.stop_clicking()

    def parse_modifiers(self, key_str):
        mods = []
        key_name = ''
        for part in key_str.split('+'):
            if part in ['ctrl', 'shift', 'alt']:
                mods.append(part)
            else:
                key_name = part
        return mods, key_name

    def start_global_listener(self):
        if self.global_listener is not None and self.global_listener.running:
            return
        self.global_listener = keyboard.Listener(on_press=self._on_global_key_press)
        self.global_listener.start()

    def stop_global_listener(self):
        if self.global_listener is not None and self.global_listener.running:
            self.global_listener.stop()
        self.global_listener = None

    def _on_global_key_press(self, key):
        try:
            key_str = self.key_mapper.get_key_name(key)
            if key_str == self.key_start:
                self.start_clicking(self.interval, self.duration)
            elif key_str == self.key_stop:
                self.stop_clicking()
        except Exception as e:
            logging.error(f"Error handling key press: {e}")
