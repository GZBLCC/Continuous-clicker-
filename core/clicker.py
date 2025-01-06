import time
import threading
from pynput import mouse, keyboard
from utils.key_mapper import KeyMapper

class Clicker:
    def __init__(self):
        self.interval = 0.1
        self.duration = None
        self.mouse_button = None
        self.key = None
        self.key_start = ''
        self.key_stop = ''
        self.is_clicking = False
        self.keyboard_listener = None
        self.mouse_controller = mouse.Controller()
        self.key_mapper = KeyMapper()
        self.global_listener = None

    def start_clicking(self, interval, duration=None):
        if self.is_clicking:
            return
        self.interval = interval
        self.duration = duration
        self.is_clicking = True
        self.click_thread = threading.Thread(target=self._click_loop)
        self.click_thread.start()

    def stop_clicking(self):
        self.is_clicking = False
        if self.click_thread and self.click_thread.is_alive():
            self.click_thread.join()

    def _click_loop(self):
        start_time = time.time()
        while self.is_clicking:
            if self.mouse_button == 'left':
                self.mouse_controller.click(mouse.Button.left)
            elif self.mouse_button == 'right':
                self.mouse_controller.click(mouse.Button.right)
            elif self.mouse_button == 'middle':
                self.mouse_controller.click(mouse.Button.middle)
            time.sleep(self.interval)
            if self.duration and time.time() - start_time >= self.duration:
                self.stop_clicking()

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
        key_str = self.key_mapper.get_key_name(key)
        if key_str == self.key_start:
            self.start_clicking(self.interval, self.duration)
        elif key_str == self.key_stop:
            self.stop_clicking()
