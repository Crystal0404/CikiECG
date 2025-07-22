from mcdreforged.plugin.plugin_event import LiteralEvent

PLUGIN_ID = "ciki_ecg"
POWER_OFF = LiteralEvent("{}.power_off".format(PLUGIN_ID))
POWER_ON = LiteralEvent("{}.power_on".format(PLUGIN_ID))
SERVER_STOP = LiteralEvent("{}.server_stop".format(PLUGIN_ID))
COMPUTER_STOP = LiteralEvent("{}.computer_stop".format(PLUGIN_ID))