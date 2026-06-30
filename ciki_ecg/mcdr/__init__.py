from mcdreforged import *

from ciki_ecg.mcdr.config import Config
from ciki_ecg.mcdr.event import *

CONFIG: Config | None = None


def on_load(plg: PluginServerInterface, _):
    global CONFIG
    CONFIG = plg.load_config_simple(target_class=Config)

    if CONFIG.decrypt.aes_key != "":  # Do not start without setting the aes_key
        from ciki_ecg.mcdr.client import INSTANCE
        INSTANCE.start()
    else:
        plg.logger.warning(plg.rtr("ciki_ecg.aes_key_not_set"))


def on_unload(_: PluginServerInterface):
    if CONFIG.decrypt.aes_key != "":  # Do not shut down without setting the aes_key
        from ciki_ecg.mcdr.client import INSTANCE
        INSTANCE.shutdown_with_blocking()


@event_listener(POWER_OFF)
def on_power_off(plg: PluginServerInterface):
    if CONFIG.backup and CONFIG.backup_command != "":
        plg.broadcast(RText(plg.rtr("ciki_ecg.back_up"), color=RColor.green))
        plg.execute_command(CONFIG.backup_command)
