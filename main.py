import tkinter as tk
import logging
import sys
import os
import json
import argparse
import socket
from tkinter import messagebox
from os import path
from gui.gui_manager import GUIManager
from pystray import MenuItem as item, Icon
from PIL import Image as PILImage

# 版本信息常量
VERSION = "v1.2"

# 配置日志记录
logging.basicConfig(filename='clicker.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config():
    config_path = 'config/settings.json'
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError as e:
                    logging.error(f"Invalid JSON in config file: {e}")
                    tk.messagebox.showwarning("Config Error", 
                        "Invalid configuration file. Using default settings.")
        return {
            "window_width": 800,
            "window_height": 600,
            "icon_path": "icon.ico"
        }
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        tk.messagebox.showwarning("Config Error", 
            "Error loading configuration. Using default settings.")
        return {
            "window_width": 800,
            "window_height": 600,
            "icon_path": "icon.ico"
        }

def center_window(root, width, height):
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')

def global_exception_handler(exc_type, exc_value, exc_traceback):
    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    tk.messagebox.showerror("Error", f"An unexpected error occurred: {exc_value}")
    sys.exit(1)

def cleanup():
    logging.info("Performing cleanup before exiting...")
    sys.exit(0)

def create_system_tray(icon_path, root):
    def on_quit(icon, item):
        try:
            icon.stop()
            root.destroy()
        except Exception as e:
            logging.error(f"Error during system tray cleanup: {e}")
            raise

    try:
        image = PILImage.open(icon_path)
        menu = (item('Quit', on_quit),)
        icon = Icon("name", image, "连点器", menu)
        return icon
    except Exception as e:
        logging.error(f"Error creating system tray: {e}")
        tk.messagebox.showwarning("System Tray Error", 
            "Failed to create system tray icon. Application will continue without it.")
        return None

def check_single_instance():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 12345))
        return True
    except socket.error:
        tk.messagebox.showerror("Error", "Another instance is already running.")
        return False

def main():
    if not check_single_instance():
        return

    try:
        # 设置全局异常处理器
        sys.excepthook = global_exception_handler

        # 加载配置
        config = load_config()
        window_width = config.get("window_width", 800)
        window_height = config.get("window_height", 600)
        icon_path = config.get("icon_path", "icon.ico")

        # 解析命令行参数
        parser = argparse.ArgumentParser(description="连点器")
        parser.add_argument('--debug', action='store_true', help='Enable debug mode')
        args = parser.parse_args()

        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)

        root = tk.Tk()
        root.title(f"连点器 v{VERSION}")

        # 处理图标文件
        try:
            if os.path.exists(icon_path):
                root.iconbitmap(icon_path)
            else:
                logging.warning(f"Icon file not found: {icon_path}")
        except Exception as e:
            logging.error(f"Error setting window icon: {e}")
            tk.messagebox.showwarning("Icon Error", 
                "Failed to set window icon. Application will continue without it.")

        # 设置窗口大小并居中
        center_window(root, window_width, window_height)

        app = GUIManager(root)

        # 设置程序退出时的清理工作
        root.protocol("WM_DELETE_WINDOW", cleanup)

        # 创建系统托盘
        if os.path.exists(icon_path):
            icon = create_system_tray(icon_path, root)
            icon.run_detached()

        root.mainloop()
    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
