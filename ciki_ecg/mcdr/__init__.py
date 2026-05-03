from mcdreforged import *
from ciki_ecg.mcdr.config import Config
from ciki_ecg.mcdr.event import *

CONFIG = Config()


def on_load(plg: PluginServerInterface, *args):
    from ciki_ecg.mcdr.client import INSTANCE

    global CONFIG
    CONFIG = plg.load_config_simple(target_class=Config)
    INSTANCE.start()


def on_unload(plg: PluginServerInterface):
    from ciki_ecg.mcdr.client import INSTANCE
    INSTANCE.shutdown_with_blocking()

@event_listener(POWER_OFF)
def on_power_off(plg: PluginServerInterface):
    if CONFIG.backup and CONFIG.backup_command != "":
        plg.broadcast(RText("开始自动备份...", color=RColor.green))
        plg.execute_command(CONFIG.backup_command)