from argparse import ArgumentParser, Namespace

from ciki_ecg.cli.config import write_config
from ciki_ecg.cli.logutil import LOG


def register() -> Namespace:
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(dest="type")

    subparsers.add_parser("init")
    subparsers.add_parser("start")

    return parser.parse_args()


def run():
    args = register()
    match args.type:
        case "init":
            write_config()
        case "start":
            from ciki_ecg.cli.server import INSTANCE
            INSTANCE.start()
        case _:
            LOG.info("Please add '--help' to view help information.")
