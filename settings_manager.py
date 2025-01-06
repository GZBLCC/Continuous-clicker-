import json
import logging
from typing import Dict, Any, Callable, Optional

class SettingsManager:
    DEFAULT_SETTINGS = {
        'interval': 0.1,
        'duration': None,
        'mouse_button': None,
        'key': None,
        'key_start': '',
        'key_stop': ''
    }

    def __init__(self, settings_file='settings.json'):
        self.settings_file = settings_file
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.listeners = []
        self.load_settings()

    def add_listener(self, listener: Callable[[Dict[str, Any]], None]):
        """添加配置变更监听器"""
        self.listeners.append(listener)

    def remove_listener(self, listener: Callable[[Dict[str, Any]], None]):
        """移除配置变更监听器"""
        self.listeners.remove(listener)

    def notify_listeners(self):
        """通知所有监听器配置已变更"""
        for listener in self.listeners:
            listener(self.settings)

    def load_settings(self):
        """加载配置文件"""
        try:
            with open(self.settings_file, 'r') as f:
                loaded_settings = json.load(f)
                self.settings.update(loaded_settings)
                if not self.validate_settings():
                    logging.warning("Invalid settings detected, reverting to default values")
                    self.settings = self.DEFAULT_SETTINGS.copy()
                self.notify_listeners()
        except FileNotFoundError:
            logging.error("Settings file not found. Using default settings.")
        except json.JSONDecodeError:
            logging.error("Failed to decode JSON from settings file. Using default settings.")
        except KeyError as e:
            logging.error(f"Missing key in settings file: {e}. Using default settings.")
        except Exception as e:
            logging.error(f"An error occurred while loading settings: {e}")

    def save_settings(self):
        """保存配置文件"""
        try:
            if self.validate_settings():
                with open(self.settings_file, 'w') as f:
                    json.dump(self.settings, f, indent=4)
                self.notify_listeners()
            else:
                logging.error("Invalid settings, not saving to file")
        except Exception as e:
            logging.error(f"An error occurred while saving settings: {e}")

    def get_setting(self, key: str, default: Optional[Any] = None) -> Any:
        """获取配置项"""
        return self.settings.get(key, self.DEFAULT_SETTINGS.get(key, default))

    def set_setting(self, key: str, value: Any):
        """设置配置项"""
        if key in self.DEFAULT_SETTINGS:
            self.settings[key] = value
            if self.validate_settings():
                self.notify_listeners()
            else:
                logging.warning(f"Invalid value for setting {key}: {value}")
        else:
            logging.warning(f"Attempted to set unknown setting: {key}")

    def validate_settings(self) -> bool:
        """验证配置项的有效性"""
        try:
            interval = float(self.settings['interval'])
            if interval <= 0:
                raise ValueError("Interval must be a positive number")
            
            if self.settings['duration'] is not None:
                duration = float(self.settings['duration'])
                if duration <= 0:
                    raise ValueError("Duration must be a positive number or None")
            
            if self.settings['mouse_button'] not in [None, 'left', 'right', 'middle']:
                raise ValueError("Invalid mouse button setting")
            
            return True
        except ValueError as e:
            logging.error(f"Invalid settings: {e}")
            return False

    def reset_to_defaults(self):
        """重置为默认配置"""
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.notify_listeners()
