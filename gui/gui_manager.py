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
from core.clicker import Clicker

class GUIManager:
    def __init__(self, master):
        self.clicker = Clicker()
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

        # 随机区域设置
        self.random_area_frame = ttk.Frame(self.frame)
        self.random_area_frame.pack(fill='x', padx=5, pady=5)

        # 窗口选择按钮
        self.select_window_button = ttk.Button(self.random_area_frame, text="选择窗口", command=self.start_window_selection)
        self.select_window_button.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # 坐标显示
        self.random_area_entry = tk.Entry(self.random_area_frame, width=20)
        self.random_area_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        self.random_area_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.random_area_frame, text="启用随机区域", variable=self.random_area_enabled).grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="w")

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

            interval = float(interval)

            if duration is not None and not self.is_valid_number(str(duration)):
                raise ValueError("持续时间必须是合法的数字或者为空")

            if duration is not None:
                duration = float(duration)

            if self.random_area_enabled.get():
                try:
                    coords = self.random_area_entry.get().split(',')
                    if len(coords) != 4:
                        raise ValueError("请输入4个坐标值，用逗号分隔")
                    x1, y1, x2, y2 = map(int, coords)
                    if x1 < 0 or y1 < 0 or x2 < 0 or y2 < 0:
                        raise ValueError("坐标不能为负数")
                    if x1 >= x2 or y1 >= y2:
                        raise ValueError("x2,y2必须大于x1,y1")
                    self.clicker.random_area = (x1, y1, x2, y2)
                except ValueError as e:
                    raise ValueError(f"随机区域设置错误: {e}")

            self.clicker.start_clicking(interval, duration)
            self.update_title("连点器 - 正在连点")
            logging.info(f"Started clicking with interval: {interval}, duration: {duration}")
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
        self.clicker.stop_clicking()
        self.update_title("连点器 - 未连点")


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
            'key_stop': self.key_stop,
            'random_area': self.random_area_entry.get(),
            'random_area_enabled': self.random_area_enabled.get()
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
        self.clicker.start_global_listener()

    def stop_global_listener(self):
        self.clicker.stop_global_listener()

    def start_window_selection(self):
        """开始窗口选择"""
        try:
            import win32gui
            import win32process
            import win32con
            
            # 获取所有窗口
            windows = []
            def enum_windows_callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title:
                        try:
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            windows.append((hwnd, title, pid))
                        except:
                            pass
                return True
                
            win32gui.EnumWindows(enum_windows_callback, windows)
            
            # 创建选择对话框
            self.window_select_dialog = tk.Toplevel(self.master)
            self.window_select_dialog.title("选择窗口")
            
            # 创建列表框
            listbox = tk.Listbox(self.window_select_dialog, width=80, height=20)
            listbox.pack(padx=10, pady=10)
            
            # 填充窗口列表
            for hwnd, title, pid in windows:
                listbox.insert(tk.END, f"[PID: {pid}] {title}")
            
            # 自动选择并激活窗口
            def on_select(event):
                selection = listbox.curselection()
                if selection:
                    index = selection[0]
                    self.selected_hwnd = windows[index][0]
                    self.window_select_dialog.destroy()
                    
                    # 激活目标窗口
                    try:
                        import win32gui
                        import win32con
                        win32gui.ShowWindow(self.selected_hwnd, win32con.SW_RESTORE)
                        win32gui.SetForegroundWindow(self.selected_hwnd)
                        self.master.after(500, self.start_area_selection)  # 稍等片刻确保窗口激活
                    except Exception as e:
                        logging.error(f"激活窗口失败: {e}")
                        messagebox.showerror("错误", f"无法激活窗口: {str(e)}")
            
            # 绑定双击事件
            listbox.bind("<Double-Button-1>", on_select)
            
        except ImportError:
            messagebox.showerror("错误", "需要安装pywin32库才能使用窗口选择功能")
            self.install_pywin32()

    def start_area_selection(self):
        """开始区域选择"""
        try:
            import win32gui
            from tkinter import ttk
            
            # 创建全屏覆盖层
            self.overlay = tk.Toplevel()
            self.overlay.attributes("-fullscreen", True)
            self.overlay.attributes("-topmost", True)
            self.overlay.attributes("-alpha", 0.3)
            self.overlay.configure(bg="black")
            self.overlay.overrideredirect(True)
            
            # 创建画布
            self.selection_canvas = tk.Canvas(self.overlay, bg="black", highlightthickness=0, cursor="cross")
            self.selection_canvas.pack(fill=tk.BOTH, expand=True)
            
            # 添加提示文字
            self.selection_canvas.create_text(
                self.overlay.winfo_screenwidth()//2,
                50,
                text="按住鼠标左键拖动选择区域，按ESC取消",
                fill="white",
                font=("Arial", 16)
            )
            
            # 绑定鼠标事件
            self.selection_canvas.bind("<ButtonPress-1>", self.on_area_select_start)
            self.selection_canvas.bind("<B1-Motion>", self.on_area_select_move)
            self.selection_canvas.bind("<ButtonRelease-1>", self.on_area_select_end)
            self.selection_canvas.bind("<Escape>", lambda e: self.overlay.destroy())
            
            # 初始化选择状态
            self.selecting_area = False
            self.start_x = 0
            self.start_y = 0
            self.rect = None
            self.crosshair_v = None
            self.crosshair_h = None
            
        except Exception as e:
            logging.error(f"区域选择错误: {e}")
            messagebox.showerror("错误", f"区域选择失败: {str(e)}")

    def on_area_select_start(self, event):
        """开始区域选择"""
        if event.num == 1:  # 仅响应鼠标左键
            self.selecting_area = True
            self.start_x = event.x
            self.start_y = event.y
            
            # 创建十字准线
            self.crosshair_v = self.selection_canvas.create_line(
                event.x, 0,
                event.x, self.overlay.winfo_screenheight(),
                fill="white",
                dash=(4, 4)
            )
            self.crosshair_h = self.selection_canvas.create_line(
                0, event.y,
                self.overlay.winfo_screenwidth(), event.y,
                fill="white",
                dash=(4, 4)
            )
            
            # 创建选择框
            self.rect = self.selection_canvas.create_rectangle(
                self.start_x, self.start_y,
                self.start_x, self.start_y,
                outline="#00FF00",
                width=2,
                fill=""
            )

    def on_area_select_move(self, event):
        """区域选择移动"""
        if self.selecting_area and self.rect and event.state & 0x0100:  # 检查左键是否按下
            # 更新选择框
            self.selection_canvas.coords(
                self.rect,
                self.start_x, self.start_y,
                event.x, event.y
            )
            
            # 更新十字准线
            self.selection_canvas.coords(
                self.crosshair_v,
                event.x, 0,
                event.x, self.overlay.winfo_screenheight()
            )
            self.selection_canvas.coords(
                self.crosshair_h,
                0, event.y,
                self.overlay.winfo_screenwidth(), event.y
            )

    def on_area_select_end(self, event):
        """结束区域选择"""
        if event.num == 1 and self.selecting_area and self.rect:  # 仅响应鼠标左键释放
            self.selecting_area = False
            
            # 获取选择的区域坐标
            x1, y1, x2, y2 = self.selection_canvas.coords(self.rect)
            
            # 转换为绝对坐标
            abs_x1 = min(x1, x2)
            abs_y1 = min(y1, y2)
            abs_x2 = max(x1, x2)
            abs_y2 = max(y1, y2)
            
            # 更新区域输入框
            self.random_area_entry.delete(0, tk.END)
            self.random_area_entry.insert(0, f"{abs_x1},{abs_y1},{abs_x2},{abs_y2}")
            
            # 清除十字准线
            self.selection_canvas.delete(self.crosshair_v)
            self.selection_canvas.delete(self.crosshair_h)
            
            # 关闭覆盖窗口
            self.overlay.destroy()
            
            # 显示选择结果
            messagebox.showinfo("区域选择", f"已选择区域: {abs_x1},{abs_y1} - {abs_x2},{abs_y2}")

    def install_pywin32(self):
        """安装pywin32库"""
        try:
            import subprocess
            subprocess.run(["pip", "install", "pywin32"], check=True)
            messagebox.showinfo("成功", "pywin32安装成功，请重启程序")
        except Exception as e:
            logging.error(f"安装pywin32失败: {e}")
            messagebox.showerror("错误", f"安装pywin32失败: {str(e)}")
