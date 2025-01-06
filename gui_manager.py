import tkinter as tk
from tkinter import ttk
import logging
from clicker import Clicker
import json
from pynput import keyboard
from key_mapper import KeyMapper

class GUIManager:
    def __init__(self, master):
        self.master = master
        self.master.title("连点器")
        self.master.geometry("400x500")
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.menu_bar = tk.Menu(self.master)
        self.master.config(menu=self.menu_bar)
        self.settings_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="设置", menu=self.settings_menu)
        self.settings_menu.add_command(label="配置", command=self.open_settings)

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
        self.key = None
        self.clicker = Clicker()
        self.key_mapper = KeyMapper()

    def open_settings(self):
        self.settings_dialog = tk.Toplevel(self.master)
        self.settings_dialog.title("设置快捷键")
        
        ttk.Label(self.settings_dialog, text="设置开始连点快捷键：").pack(padx=5, pady=5)
        self.key_start_label = ttk.Label(self.settings_dialog, text=self.clicker.key_start)
        self.key_start_label.pack(padx=5, pady=5)
        ttk.Button(self.settings_dialog, text="选择", command=lambda: self.set_key("start")).pack(padx=5, pady=5)

        ttk.Label(self.settings_dialog, text="设置停止连点快捷键：").pack(padx=5, pady=5)
        self.key_stop_label = ttk.Label(self.settings_dialog, text=self.clicker.key_stop)
        self.key_stop_label.pack(padx=5, pady=5)
        ttk.Button(self.settings_dialog, text="选择", command=lambda: self.set_key("stop")).pack(padx=5, pady=5)

        ttk.Button(self.settings_dialog, text="确定", command=self.save_settings).pack(padx=5, pady=5)
        ttk.Button(self.settings_dialog, text="取消", command=self.cancel_settings).pack(padx=5, pady=5)

    def cancel_settings(self):
        self.settings_dialog.destroy()
        if self.key_start_label is not None:
            self.key_start_label = None
        if self.key_stop_label is not None:
            self.key_stop_label = None

    def select_button(self, button):
        self.mouse_button = button
        self.key = None

        for widget in self.mouse_button_frame.winfo_children():
            if isinstance(widget, tk.Button):
                widget.config(relief='flat')
        index = self.buttons.index((next(text for text, btn in self.buttons if btn == button), button))
        widget = self.mouse_button_frame.grid_slaves(row=index)[0]
        widget.config(relief='sunken')

    def set_key(self, key_type):
        def on_key_press(key):  
            if key == keyboard.Key.esc:
                return False
            key_str = self.key_mapper.get_key_name(key)
            if key_type == "start":
                self.clicker.key_start = key_str
                if self.key_start_label:
                    self.key_start_label.config(text=key_str)
            elif key_type == "stop":
                self.clicker.key_stop = key_str
                if self.key_stop_label:
                    self.key_stop_label.config(text=key_str)
            self.clicker.keyboard_listener.stop()
            self.clicker.keyboard_listener = None

        self.clicker.keyboard_listener = keyboard.Listener(on_press=on_key_press)
        self.clicker.keyboard_listener.start()

    def select_or_set_key(self, key_type):
        def on_key_press(key):  
            if key == keyboard.Key.esc:
                return False
            key_str = self.key_mapper.get_key_name(key)
            if key_type == "start":
                self.clicker.key_start = key_str
                if self.key_start_label:
                    self.key_start_label.config(text=key_str)
            elif key_type == "stop":
                self.clicker.key_stop = key_str
                if self.key_stop_label:
                    self.key_stop_label.config(text=key_str)
            elif key_type == "key":
                self.key = key_str
                self.key_entry.delete(0, tk.END)    
                self.key_entry.insert(0, key_str)
                self.reset_mouse_button_state()
            self.clicker.keyboard_listener.stop()
            self.clicker.keyboard_listener = None

        self.clicker.keyboard_listener = keyboard.Listener(on_press=on_key_press)
        self.clicker.keyboard_listener.start()

    def reset_mouse_button_state(self):
        for widget in self.mouse_button_frame.winfo_children():
            if isinstance(widget, tk.Button):
                widget.config(relief='flat')
        self.mouse_button = None

    def update_title(self, title):
        self.master.title(title)

    def on_closing(self):
        response = tk.messagebox.askokcancel("退出", "是否保存当前设置？")
        if response:
            self.save_settings()

        if self.clicker.keyboard_listener is not None and self.clicker.keyboard_listener.running:
            self.clicker.keyboard_listener.stop()

        logging.shutdown()
        self.master.destroy()

    def save_settings(self):
        settings = {
            'interval': self.clicker.interval,
            'duration': self.clicker.duration,
            'mouse_button': self.mouse_button,
            'key': self.key,
            'key_start': self.clicker.key_start,
            'key_stop': self.clicker.key_stop
        }
        with open('settings.json', 'w') as f:
            json.dump(settings, f, indent=4)
        
        if self.settings_dialog is not None:
            self.settings_dialog.destroy()
        self.key_start_label = None
        self.key_stop_label = None
        
        self.clicker.stop_global_listener()
        self.clicker.start_global_listener()

    def load_settings(self):
        try:
            with open('settings.json', 'r') as f:
                settings = json.load(f)
            self.clicker.interval = float(settings['interval'])
            self.clicker.duration = float(settings['duration']) if settings.get('duration') is not None else None
            self.mouse_button = settings['mouse_button']
            self.key = settings['key']
            self.clicker.key_start = settings['key_start']
            self.clicker.key_stop = settings['key_stop']

            self.interval_entry.delete(0, tk.END)
            self.interval_entry.insert(0, str(self.clicker.interval))
            self.duration_entry.delete(0, tk.END)
            self.duration_entry.insert(0, str(self.clicker.duration) if self.clicker.duration is not None else '')
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

        except FileNotFoundError:
            logging.error("Settings file not found. Using default settings.")
        except json.JSONDecodeError:
            logging.error("Failed to decode JSON from settings file. Using default settings.")
        except KeyError as e:
            logging.error(f"Missing key in settings file: {e}. Using default settings.")
        except Exception as e:
            logging.error(f"An error occurred while loading settings: {e}")

    def start_clicking(self):
        interval = self.interval_entry.get()
        duration = self.duration_entry.get()
        self.clicker.start_clicking(float(interval), float(duration) if duration else None)

    def stop_clicking(self):
        self.clicker.stop_clicking()
