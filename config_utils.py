import configparser
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')

DEFAULTS = {
    'setting': {
        'runtime': '0',
        'key': '',
        'maildz': '0',
        'sitekeyfs': 'e18a349a-46c2-46a0-87a8-74be79345c92',
        'yxljfs': '0',
        'account_fmt': '8',
        'password_fmt': '12',
        'thread_count': '1',
        'ip_source': '0',
    }
}


def load_config():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_PATH):
        config.read(CONFIG_PATH, encoding='utf-8')
    if 'setting' not in config:
        config['setting'] = {}
    for key, val in DEFAULTS['setting'].items():
        if key not in config['setting']:
            config['setting'][key] = val
    return config


def save_config(config):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        config.write(f)


def get(config, key, default=None):
    try:
        return config.get('setting', key)
    except Exception:
        return default


def set(config, key, value):
    if 'setting' not in config:
        config['setting'] = {}
    config['setting'][key] = str(value)
