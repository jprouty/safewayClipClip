#!/usr/bin/env python3

# This script clips all available Safeway coupons.

import argparse
import atexit
import getpass
import logging
import os
import time

from safewayclipclip import VERSION
from safewayclipclip.args import define_common_args, BASE_PATH
from safewayclipclip.webdriver import get_webdriver

logger = logging.getLogger(__name__)


def main():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(logging.StreamHandler())
    # Disable noisy log spam from filelock from within tldextract.
    logging.getLogger("filelock").setLevel(logging.WARN)

    # For helping remote debugging, also log to file.
    # Developers should be vigilant to NOT log any PII, ever (including being
    # mindful of what exceptions might be thrown).
    log_directory = os.path.join(BASE_PATH, 'Logs')
    os.makedirs(log_directory, exist_ok=True)
    log_filename = os.path.join(log_directory, '{}.log'.format(
        time.strftime("%Y-%m-%d_%H-%M-%S")))
    root_logger.addHandler(logging.FileHandler(log_filename))

    parser = argparse.ArgumentParser(description='Clip Safeway coupons.')
    define_common_args(parser)
    args = parser.parse_args()

    if args.version:
        print('SafewayClipClip {}\nBy: Jeff Prouty'.format(VERSION))
        exit(0)

    maybe_prompt_for_safeway_credentials(args)
    webdriver = get_webdriver(args.headless, args.session_path)

    def close_webdriver():
        webdriver.close()
    atexit.register(close_webdriver)


def on_critical(msg):
    logger.critical(msg)
    exit(1)


def maybe_prompt_for_safeway_credentials(args):
    if not args.safeway_email and not args.safeway_user_will_login:
        args.safeway_email = input('Safeway email: ')
    if not args.safeway_password and not args.safeway_user_will_login:
        args.safeway_password = getpass.getpass('Safeway password: ')


if __name__ == '__main__':
    main()
