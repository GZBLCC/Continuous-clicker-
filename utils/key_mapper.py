from pynput import keyboard
from pynput.keyboard import Key, KeyCode

class KeyMapper:
    KEY_MAP = {
        keyboard.Key.f1: 'f1', keyboard.Key.f2: 'f2',
        keyboard.Key.f3: 'f3', keyboard.Key.f4: 'f4',
        keyboard.Key.f5: 'f5', keyboard.Key.f6: 'f6',
        keyboard.Key.f7: 'f7', keyboard.Key.f8: 'f8',
        keyboard.Key.f9: 'f9', keyboard.Key.f10: 'f10',
        keyboard.Key.f11: 'f11', keyboard.Key.f12: 'f12',
        keyboard.Key.ctrl_l: 'ctrl', keyboard.Key.ctrl_r: 'ctrl',
        keyboard.Key.shift_l: 'shift', keyboard.Key.shift_r: 'shift',
        keyboard.Key.alt_l: 'alt', keyboard.Key.alt_r: 'alt',
        keyboard.Key.cmd: 'cmd', keyboard.Key.caps_lock: 'caps_lock',
        keyboard.Key.tab: 'tab', keyboard.Key.space: 'space',
        keyboard.Key.enter: 'enter', keyboard.Key.backspace: 'backspace',
        keyboard.Key.delete: 'delete', keyboard.Key.end: 'end',
        keyboard.Key.home: 'home', keyboard.Key.insert: 'insert',
        keyboard.Key.page_up: 'page_up', keyboard.Key.page_down: 'page_down',
        keyboard.Key.up: 'up', keyboard.Key.down: 'down',
        keyboard.Key.left: 'left', keyboard.Key.right: 'right',
        keyboard.Key.esc: 'esc', keyboard.Key.num_lock: 'num_lock',
        keyboard.Key.print_screen: 'print_screen', keyboard.Key.scroll_lock: 'scroll_lock',
        keyboard.Key.pause: 'pause', keyboard.Key.menu: 'menu'
    }

    def __init__(self):
        self.modifiers = ['ctrl', 'shift', 'alt']

    def format_keysym(self, key):
        if isinstance(key, KeyCode):
            return key.char
        return self.KEY_MAP.get(key, str(key))

    def parse_modifiers(self, key_str):
        mods = []
        key_name = ''
        for part in key_str.split('+'):
            if part in self.modifiers:
                mods.append(part)
            else:
                key_name = part
        return mods, key_name

    def is_modifier(self, key_str):
        return key_str in self.modifiers

    def get_key_name(self, key):
        return self.format_keysym(key)

    def is_valid_key(self, key_str):
        if key_str in self.KEY_MAP.values():
            return True
        if len(key_str) == 1:
            return True
        return False
