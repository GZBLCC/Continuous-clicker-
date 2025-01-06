import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import json
import logging
from logging.handlers import RotatingFileHandler
from pynput import keyboard, mouse
from pynput.keyboard import Controller, KeyCode, Key
from pynput.mouse import Controller as MouseController, Button
from utils.key_mapper import KeyMapper
from logging import root

class GUIManager:
    def __init__(self, master):
        self.master = master
        self.master.title("连点器")
        self.master.geometry("400x500")
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.setup_logging()
        
        self.menu_bar = tk.Menu(self.master)
        self.master.config(menu=self.menu_bar)
        self.settings_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="设置", menu=self.settings_menu)
        self.settings_menu.add_command(label="配置", command=self.open_settings)

        self.settings_dialog = None

        style = ttk.Style()
        style.theme_use('clam')

        self.frame = ttk.Frame(self.master)
        self.frame.pack(expand=True, fill='both', padx=10, pady=10)

        self.button_frame = ttk.Frame(self.frame)
        self.button_frame.pack(fill='x', padx=5, pady=5)

        self.start_button = ttk.Button(self.button_frame, text="开始连点", command=self.start_clicking)
        self.start_button.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.stop_button = ttk.Button(self.button_frame, text="停止连点", command=self.stop_clicking)
        self.stop_button.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        self.settings_frame = ttk.Frame(self.frame)
        self.settings_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(self.settings_frame, text="点击间隔（秒）：").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.interval_entry = tk.Entry(self.settings_frame, width=5)
        self.interval_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(self.settings_frame, text="持续时间（秒，留空则不停止）：").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.duration_entry = tk.Entry(self.settings_frame, width=5)
        self.duration_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        self.mouse_button_frame = ttk.Frame(self.frame)
        self.mouse_button_frame.pack(fill='x', padx=5, pady=5)

        self.buttons = [('左键', 'left'), ('右键', 'right'), ('中键', 'middle')]
        for i, (text, button) in enumerate(self.buttons):
            tk.Button(self.mouse_button_frame, text=text, command=lambda b=button: self.select_button(b)).grid(row=i, column=0, padx=5, pady=5, sticky="nsew")

        tk.Button(self.settings_frame, text="选择键盘按键", command=lambda: self.select_or_set_key("key")).grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        self.key_entry = tk.Entry(self.frame, width=20)
        self.key_entry.insert(0, "未设置")
        self.key_entry.pack(fill='x', padx=5, pady=5)

        self.mouse_button = None
        self.keyboard_listener = None
        self.lock = threading.Lock()
        self.click_thread = None
        self.interval = 0.1
        self.duration = None
        self.key = None
        self.stop_event = threading.Event()
        self.key_start = ''
        self.key_stop = ''

        self.key_mapper = KeyMapper()

        self.load_settings()
        self.start_global_listener()



    def setup_logging(self):
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        file_handler = RotatingFileHandler(
            'clicker.log',
            maxBytes=1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        logging.info("Logging initialized")

    def open_settings(self):
        logging.info("Opening settings dialog")
        self.settings_dialog = tk.Toplevel(self.master)
        self.settings_dialog.title("设置快捷键")
        
        ttk.Label(self.settings_dialog, text="设置开始连点快捷键：").pack(padx=5, pady=5)
        self.key_start_label = ttk.Label(self.settings_dialog, text=self.key_start)
        self.key_start_label.pack(padx=5, pady=5)
        ttk.Button(self.settings_dialog, text="选择", command=lambda: self.set_key("start")).pack(padx=5, pady=5)

        ttk.Label(self.settings_dialog, text="设置停止连点快捷键：").pack(padx=5, pady=5)
        self.key_stop_label = ttk.Label(self.settings_dialog, text=self.key_stop)
        self.key_stop_label.pack(padx=5, pady=5)
        ttk.Button(self.settings_dialog, text="选择", command=lambda: self.set_key("stop")).pack(padx=5, pady=5)

        ttk.Button(self.settings_dialog, text="确定", command=self.save_settings).pack(padx=5, pady=5)
        ttk.Button(self.settings_dialog, text="取消", command=self.cancel_settings).pack(padx=5, pady=5)

    def cancel_settings(self):
        logging.info("Canceling settings changes")
        if self.settings_dialog is not None:
            self.settings_dialog.destroy()
            self.settings_dialog = None
        if self.key_start_label is not None:
            self.key_start_label = None
        if self.key_stop_label is not None:
            self.key_stop_label = None

    def parse_modifiers(self, key_str):
        mods = []
        key_name = ''
        for part in key_str.split('+'):
            if part in ['ctrl', 'shift', 'alt']:
                mods.append(part)
            else:
                key_name = part
        return mods, key_name

    def start_clicking(self):
        original_title = self.master.title()
        try:
            interval = self.interval_entry.get()
            duration = self.get_duration()

            if not self.is_valid_number(interval):
                raise ValueError("间隔必须是合法的数字")

            self.interval = float(interval)

            if duration is not None and not self.is_valid_number(str(duration)):
                raise ValueError("持续时间必须是合法的数字或者为空")

            if duration is not None:
                self.duration = float(duration)
            else:
                self.duration = None

            self.stop_clicking()    

            self.click_thread = threading.Thread(target=self.clicker)
            self.click_thread.start()
            self.update_title("连点器 - 正在连点")
            logging.info(f"Started clicking with interval: {self.interval}, duration: {self.duration}")
        except ValueError as e:
            logging.error(f"ValueError: {e}")
            messagebox.showerror("输入错误", str(e))
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            messagebox.showerror("未知错误", str(e))
        finally:
            self.update_title(original_title)

    def reset_mouse_button_state(self):
        for widget in self.mouse_button_frame.winfo_children():
            if isinstance(widget, tk.Button):
                widget.config(relief='flat')
        self.mouse_button = None
        
    def is_valid_number(self, value):
        try:
            float(value)
            return True
        except ValueError:
            return False

    def stop_clicking(self):
        if self.click_thread is not None and self.click_thread.is_alive():
            logging.info("Stopping clicking")
            self.stop_event.set()
            self.click_thread.join()
            with self.lock:
                self.click_thread = None
            self.stop_event.clear()
            self.update_title("连点器 - 未连点")

    def clicker(self):
        start_time = time.time()
        self.keyboard_controller = Controller()
        self.mouse_controller = MouseController()
        
        while not self.stop_event.is_set() and (self.duration is None or (time.time() - start_time) < self.duration):
            with self.lock:
                if self.key:
                    mods, key_name = self.parse_modifiers(self.key)
                    for mod in mods:
                        mod_key = getattr(Key, mod, None)
                        if mod_key:
                            self.keyboard_controller.press(mod_key)
                    
                    if len(key_name) == 1:
                        self.keyboard_controller.press(KeyCode.from_char(key_name))
                        self.keyboard_controller.release(KeyCode.from_char(key_name))
                    elif key_name in self.key_mapper.KEY_MAP.values():
                        self.keyboard_controller.press(getattr(Key, key_name))
                        self.keyboard_controller.release(getattr(Key, key_name))
                    else:
                        self.keyboard_controller.press(KeyCode.from_char(key_name))
                        self.keyboard_controller.release(KeyCode.from_char(key_name))
                    
                    for mod in mods:
                        mod_key = getattr(Key, mod, None)
                        if mod_key:
                            self.keyboard_controller.release(mod_key)
                elif self.mouse_button:
                    button = getattr(Button, self.mouse_button)
                    self.mouse_controller.click(button)

                time.sleep(self.interval)

    def get_duration(self):         
        duration_str = self.duration_entry.get()
        if duration_str:
            try:
                return float(duration_str)
            except ValueError:
                messagebox.showerror("输入错误", "持续时间必须是合法的数字或者为空")
                return None
        return None

    def update_title(self, title):
        self.master.title(title)

    def select_button(self, button):
        self.mouse_button = button
        self.key = None

        for widget in self.mouse_button_frame.winfo_children():
            if isinstance(widget, tk.Button):
                widget.config(relief='flat')
        index = self.buttons.index((next(text for text, btn in self.buttons if btn == button), button))
        widget = self.mouse_button_frame.grid_slaves(row=index)[0]
        widget.config(relief='sunken')

    def select_or_set_key(self, key_type):
        def on_key_press(key):  
            if key == keyboard.Key.esc:
                return False
            key_str = self.key_mapper.format_keysym(key)
            if key_type == "start":
                self.key_start = key_str
                if self.key_start_label:
                    self.key_start_label.config(text=key_str)
            elif key_type == "stop":
                self.key_stop = key_str
                if self.key_stop_label:
                    self.key_stop_label.config(text=key_str)
            elif key_type == "key":
                self.key = key_str
                self.key_entry.delete(0, tk.END)    
                self.key_entry.insert(0, key_str)
                self.reset_mouse_button_state()
            self.keyboard_listener.stop()
            self.keyboard_listener = None

        self.keyboard_listener = keyboard.Listener(on_press=on_key_press)
        self.keyboard_listener.start()

    def format_keysym(self, key):
        return self.key_mapper.format_keysym(key)
    
    def set_key(self, key_type):
        def on_key_press(key):
            if key == keyboard.Key.esc:
                return False
            key_str = self.key_mapper.format_keysym(key)
            if key_type == "start":
                self.key_start = key_str
                if self.key_start_label:
                    self.key_start_label.config(text=key_str)
            elif key_type == "stop":
                self.key_stop = key_str
                if self.key_stop_label:
                    self.key_stop_label.config(text=key_str)
            self.keyboard_listener.stop()
            self.keyboard_listener = None

        self.keyboard_listener = keyboard.Listener(on_press=on_key_press)
        self.keyboard_listener.start()

    def on_closing(self):
        response = messagebox.askokcancel("退出", "是否保存当前设置？")
        if response:
            self.save_settings()

        if self.click_thread is not None and self.click_thread.is_alive():
            self.stop_event.set()
            self.click_thread.join()
            with self.lock:
                self.click_thread = None
            self.stop_event.clear()

        if self.keyboard_listener is not None and self.keyboard_listener.running:
            self.keyboard_listener.stop()

        logging.shutdown()
        self.master.destroy()

    def save_settings(self):
        settings = {
            'interval': self.interval,
            'duration': self.duration,
            'mouse_button': self.mouse_button,
            'key': self.key,
            'key_start': self.key_start,
            'key_stop': self.key_stop
        }
        with open('settings.json', 'w') as f:
            json.dump(settings, f, indent=4)
        
        if self.settings_dialog is not None:
            self.settings_dialog.destroy()
            self.settings_dialog = None
        self.key_start_label = None
        self.key_stop_label = None
        
        self.stop_global_listener()
        self.start_global_listener()
        logging.info("Settings saved")
        
    def load_settings(self):
        try:
            with open('settings.json', 'r') as f:
                settings = json.load(f)
            self.interval = float(settings['interval'])
            self.duration = float(settings['duration']) if settings.get('duration') is not None else None
            self.mouse_button = settings['mouse_button']
            self.key = settings['key']
            self.key_start = settings['key_start']
            self.key_stop = settings['key_stop']

            self.interval_entry.delete(0, tk.END)
            self.interval_entry.insert(0, str(self.interval))
            self.duration_entry.delete(0, tk.END)
            self.duration_entry.insert(0, str(self.duration) if self.duration is not None else '')
            self.key_entry.delete(0, tk.END)
            self.key_entry.insert(0, self.key if self.key else "未设置")

            for widget in self.mouse_button_frame.winfo_children():
                if isinstance(widget, tk.Button):
                    widget.config(relief='flat')
            if self.mouse_button:
                for i, (text, btn) in enumerate(self.buttons):
                    if btn == self.mouse_button:
                        button_widget = self.mouse_button_frame.grid_slaves(row=i)[0]
                        if isinstance(button_widget, tk.Button):
                            button_widget.config(relief='sunken')

            logging.info("Settings loaded successfully")
        except FileNotFoundError:
            logging.error("Settings file not found. Using default settings.")
        except json.JSONDecodeError:
            logging.error("Failed to decode JSON from settings file. Using default settings.")
        except KeyError as e:
            logging.error(f"Missing key in settings file: {e}. Using default settings.")
        except Exception as e:
            logging.error(f"An error occurred while loading settings: {e}")

    def start_global_listener(self):
        if self.keyboard_listener and self.keyboard_listener.running:
            self.keyboard_listener.stop()
        
        def on_global_key_press(key):
            key_str = self.key_mapper.format_keysym(key)
            if key_str == self.key_start:
                self.start_clicking()
            elif key_str == self.key_stop:
                self.stop_clicking()

        self.keyboard_listener = keyboard.Listener(on_press=on_global_key_press)
        self.keyboard_listener.start()
        logging.info("Global keyboard listener started")

    def stop_global_listener(self):
        if self.keyboard_listener and self.keyboard_listener.running:
           self.keyboard_listener.stop()
           logging.info("Global keyboard listener stopped")
