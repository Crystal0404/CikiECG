from argparse import ArgumentParser, Namespace

from ciki_ecg.cli.config import write_config, generate_key
from ciki_ecg.cli.logutil import LOG


def register() -> Namespace:
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(dest="type")

    subparsers.add_parser("init", help="Initialize the configuration file")
    subparsers.add_parser("start", help="Start")
    subparsers.add_parser("generate-key", help="Generate a new aes_key")

    return parser.parse_args()


def run():
    args = register()
    match args.type:
        case "init":
            write_config()
        case "start":
            from ciki_ecg.cli.server import INSTANCE
            INSTANCE.start()
        case "generate-key":
            generate_key()
        case _:
            LOG.info("Please add '--help' to view help information.")
