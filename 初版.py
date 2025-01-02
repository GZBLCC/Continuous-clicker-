import tkinter as tk
from tkinter import ttk
import threading
import time
from pynput import keyboard, mouse

class ClickerGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("连点器")
        self.master.geometry("400x500")  # 设置窗口大小
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 创建菜单栏
        self.menu_bar = tk.Menu(self.master)
        self.master.config(menu=self.menu_bar)

        # 创建“设置”菜单
        self.settings_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="设置", menu=self.settings_menu)
        self.settings_menu.add_command(label="配置", command=self.open_settings)

        # 设置样式
        style = ttk.Style()
        style.theme_use('clam')  # 使用'clam'主题

        # 创建主框架
        self.frame = ttk.Frame(self.master)
        self.frame.pack(expand=True, fill='both', padx=10, pady=10)

        # 创建控制按钮框架
        self.button_frame = ttk.Frame(self.frame)
        self.button_frame.pack(fill='x', padx=5, pady=5)

        # 创建控制按钮
        self.start_button = ttk.Button(self.button_frame, text="开始连点", command=self.start_clicking)
        self.start_button.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.stop_button = ttk.Button(self.button_frame, text="停止连点", command=self.stop_clicking)
        self.stop_button.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        # 创建设置框架
        self.settings_frame = ttk.Frame(self.frame)
        self.settings_frame.pack(fill='x', padx=5, pady=5)

        # 创建设置控件
        ttk.Label(self.settings_frame, text="点击间隔（秒）：").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.interval_entry = tk.Entry(self.settings_frame, width=5)
        self.interval_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(self.settings_frame, text="持续时间（秒，留空则不停止）：").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.duration_entry = tk.Entry(self.settings_frame, width=5)
        self.duration_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Button(self.settings_frame, text="选择键盘按键", command=self.select_key).grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        # 创建鼠标按钮框架
        self.mouse_button_frame = ttk.Frame(self.frame)
        self.mouse_button_frame.pack(fill='x', padx=5, pady=5)

        buttons = [('左键', 'left'), ('右键', 'right'), ('中键', 'middle')]
        for i, (text, button) in enumerate(buttons):
            ttk.Button(self.mouse_button_frame, text=text, command=lambda b=button: self.select_button(b)).grid(row=i, column=0, padx=5, pady=5, sticky="nsew")

        # 创建键盘按键显示
        self.key_entry = tk.Entry(self.frame, width=20)
        self.key_entry.insert(0, "未设置")
        self.key_entry.pack(fill='x', padx=5, pady=5)

        self.mouse_button = None  # 用于存储选择的鼠标按钮

        # 初始化线程和锁
        self.lock = threading.Lock()
        self.click_thread = None
        self.interval = 0.1
        self.duration = None
        self.key = None
        self.stop_event = threading.Event()
        self.key_start = ''  # 用于存储开始连点的键盘按键
        self.key_stop = ''  # 用于存储停止连点的键盘按键

    def open_settings(self):
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
        ttk.Button(self.settings_dialog, text="取消", command=self.settings_dialog.destroy).pack(padx=5, pady=5)

    def set_key(self, key_type):
        def on_key_press(key):
            if key == keyboard.Key.esc:
                return False  # Stop the listener
            key_str = self.format_keysym(key)
            if key_type == "start":
                self.key_start = key_str
                self.key_start_label.config(text=key_str)
            elif key_type == "stop":
                self.key_stop = key_str
                self.key_stop_label.config(text=key_str)
            self.keyboard_listener.stop()
            self.keyboard_listener = None

        self.keyboard_listener = keyboard.Listener(on_press=on_key_press)
        self.keyboard_listener.start()

    def start_clicking(self):
        try:
            self.interval = float(self.interval_entry.get())
            self.duration = self.get_duration()
        except ValueError:
            self.master.title("连点器 - 错误：无效的输入")
            return
        self.stop_clicking()
        self.click_thread = threading.Thread(target=self.clicker, args=(self.key,))
        self.click_thread.start()
        self.update_title(f"连点器 - 正在连点：{self.key if self.key else 'None'}")

    def stop_clicking(self):
        if self.click_thread is not None and self.click_thread.is_alive():
            self.stop_event.set()
            self.click_thread.join()
            with self.lock:
                self.click_thread = None
            self.stop_event.clear()
            self.update_title("连点器 - 未连点")

    def clicker(self, key_name):
        start_time = time.time()
        while not self.stop_event.is_set() and (self.duration is None or (time.time() - start_time) < self.duration):
            with self.lock:
                if self.mouse_button:
                    # 如果设置了鼠标按钮，则执行鼠标点击
                    if self.mouse_button == 'left':
                        mouse.Controller().click(mouse.Button.left)
                    elif self.mouse_button == 'right':
                        mouse.Controller().click(mouse.Button.right)
                    elif self.mouse_button == 'middle':
                        mouse.Controller().click(mouse.Button.middle)
                elif key_name:
                    # 如果设置了键盘按键，则执行键盘按键
                    keyboard.Controller().press(key_name)
                    keyboard.Controller().release(key_name)
            time.sleep(self.interval)

    def get_duration(self):         
        duration_str = self.duration_entry.get()
        return float(duration_str) if duration_str else None

    def update_title(self, title):
        self.master.title(title)

    def select_button(self, button):
        self.mouse_button = button

    def select_key(self):
        def on_key_press(key):
            if key == keyboard.Key.esc:
                return False  # Stop the listener
            key_str = self.format_keysym(key)
            self.key = key_str
            self.key_entry.delete(0, tk.END)
            self.key_entry.insert(0, key_str)
            return False  # Stop the listener

        self.keyboard_listener = keyboard.Listener(on_press=on_key_press)
        self.keyboard_listener.start()

    def format_keysym(self, key):
            keymap = {
                keyboard.Key.f1: 'F1', keyboard.Key.f2: 'F2',
                keyboard.Key.f3: 'F3', keyboard.Key.f4: 'F4',
                keyboard.Key.f5: 'F5', keyboard.Key.f6: 'F6',
                keyboard.Key.f7: 'F7', keyboard.Key.f8: 'F8',
                keyboard.Key.f9: 'F9', keyboard.Key.f10: 'F10',
                keyboard.Key.f11: 'F11', keyboard.Key.f12: 'F12',
                keyboard.Key.ctrl_l: 'Ctrl', keyboard.Key.ctrl_r: 'Ctrl',
                keyboard.Key.shift_l: 'Shift', keyboard.Key.shift_r: 'Shift',
                keyboard.Key.alt_l: 'Alt', keyboard.Key.alt_r: 'Alt',
                keyboard.Key.cmd: 'Cmd', keyboard.Key.caps_lock: 'CapsLock',
                keyboard.Key.tab: 'Tab', keyboard.Key.space: 'Space',
                keyboard.Key.enter: 'Enter', keyboard.Key.backspace: 'Backspace',
                keyboard.Key.delete: 'Delete', keyboard.Key.end: 'End',
                keyboard.Key.home: 'Home', keyboard.Key.insert: 'Insert',
                keyboard.Key.page_up: 'PageUp', keyboard.Key.page_down: 'PageDown',
                keyboard.Key.up: 'Up', keyboard.Key.down: 'Down',
                keyboard.Key.left: 'Left', keyboard.Key.right: 'Right',
                keyboard.Key.esc: 'Esc', keyboard.Key.num_lock: 'NumLock',
                keyboard.Key.print_screen: 'PrtSc', keyboard.Key.scroll_lock: 'ScrollLock',
                keyboard.Key.pause: 'Pause', keyboard.Key.menu: 'Menu'
            }
             # 对于普通字符键，直接返回字符
            return keymap.get(key, key)

    def on_closing(self):
        self.stop_clicking()
        if hasattr(self, 'keyboard_listener') and self.keyboard_listener.running:
            self.keyboard_listener.stop()
        self.master.destroy()

    def save_settings(self):
        # 保存设置的逻辑
        print(f"开始连点快捷键: {self.key_start}")
        print(f"停止连点快捷键: {self.key_stop}")
        self.settings_dialog.destroy()  # 关闭设置窗口
        self.start_global_listener()  # 启动全局键盘监听器

    def start_global_listener(self):
        def on_global_key_press(key):
            key_str = self.format_keysym(key)
            if key_str == self.key_start:
                self.start_clicking()
            elif key_str == self.key_stop:
                self.stop_clicking()

        self.keyboard_listener = keyboard.Listener(on_press=on_global_key_press)
        self.keyboard_listener.start()

    def stop_global_listener(self):
        if self.keyboard_listener and self.keyboard_listener.running:
            self.keyboard_listener.stop()

def main():
    root = tk.Tk()
    app = ClickerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()

