#!/usr/bin/env python3

# This script clips all available Safeway coupons.

import argparse
import atexit
from datetime import datetime
import logging
import os
import random
import time

from selenium.common.exceptions import (
    ElementClickInterceptedException, StaleElementReferenceException)

from safewayclipclip import VERSION
from safewayclipclip.args import define_common_args, BASE_PATH
from safewayclipclip.webdriver import (
    get_webdriver,
    get_element_by_id, get_element_by_name, get_element_by_xpath,
    get_element_by_link_text, get_elements_by_class_name, is_visible)


logger = logging.getLogger(__name__)


SAFEWAY_HOME = 'https://www.safeway.com'
FOR_U = '{}/justforu/coupons-deals.html'.format(SAFEWAY_HOME)


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

    webdriver = get_webdriver(args.headless, args.session_path)
    webdriver.implicitly_wait(5)

    def close_webdriver():
        webdriver.close()
    atexit.register(close_webdriver)

    login(webdriver, args)
    webdriver.get(FOR_U)

    while True:
        coupons_clip_clip = get_elements_by_class_name(
            webdriver, 'grid-coupon-btn')
        if not coupons_clip_clip:
            logger.error('Cannot find coupons')
            break

        for c in coupons_clip_clip:
            try:
                user_click(c)
            except ElementClickInterceptedException:
                logger.exception('Click interception error; continuing')

        load_mores = get_elements_by_class_name(webdriver, 'load-more')
        if not load_mores or not is_visible(load_mores[0]):
            logger.warning(
                'Cannot find "Load more" button; either done or unexpectedly '
                'missing')
            break
        logger.info('Clicking load more!')
        user_click(load_mores[0])
        time.sleep(2)
    logger.info('All done!')


def user_click(elem):
    rand_user_delay()
    elem.click()


def rand_user_delay():
    rand_sleep_time_s = random.randint(250, 1250) / 1000.0
    time.sleep(rand_sleep_time_s)


def on_critical(msg):
    logger.critical(msg)
    exit(1)


def login(webdriver, args):
    maybe_prompt_for_safeway_credentials(args)
    logger.info('Navigating to Safeway homepage.')
    webdriver.get(SAFEWAY_HOME)

    menu_buttons = get_elements_by_class_name(
        webdriver, 'menu-nav__profile-button-sign-in-up')
    if not menu_buttons:
        logger.error('Cannot find menu element')
        return False
    menu_button = menu_buttons[0]
    if menu_button.text.strip().lower() == 'account':
        logger.info('Login menu button indicates user is already logged in')
        return True
    user_click(menu_button)

    login_button = get_element_by_id(webdriver, 'sign-in-modal-link')
    if not login_button:
        logger.error('Cannot find login menu item')
        return False
    if login_button.text.strip().lower() != 'sign in':
        logger.info('Login menu indicates user is already logged in')
        return True
    user_click(login_button)

    login_via_otps = get_elements_by_class_name(webdriver, 'otp-link')
    if not login_via_otps:
        logger.error('Cannot find login via OTP link')
        return False
    login_via_otp = login_via_otps[0]
    user_click(login_via_otp)

    user_input = get_element_by_id(webdriver, 'email-mobile-otp')
    if not user_input:
        logger.error('Cannot find username input')
        return False
    user_input.send_keys(args.safeway_username)

    otp_submit = get_element_by_id(webdriver, 'update-otp-continue-btn')
    if not otp_submit:
        logger.error('Cannot find OTP submit button')
        return False
    user_click(otp_submit)

    otp_code = get_element_by_id(webdriver, 'otp-code')
    if not otp_code:
        logger.error('Cannot find OTP code input')
        return False

    otp_code_value = input('Enter the OTP code you received at {}: '.format(
        args.safeway_username))
    otp_code.send_keys(otp_code_value)
    time.sleep(1)

    otp_submit = get_element_by_id(webdriver, 'sign-in-otp-btn')
    if not otp_submit:
        logger.error('Cannot find OTP submit button')
        return False
    user_click(otp_submit)

    return wait_for_login(webdriver)


def wait_for_login(webdriver, max_wait_s=1 * 60):
    start_time = datetime.now()
    while True:
        time.sleep(1)
        since_start = datetime.now() - start_time
        if since_start.total_seconds() > max_wait_s:
            logger.error('Exceeded timeout waiting for authed homepage')
            return False
        try:
            menu_buttons = get_elements_by_class_name(
                webdriver, 'menu-nav__profile-button-sign-in-up')
            if not menu_buttons:
                continue
            menu_button = menu_buttons[0]
            if menu_button.text.strip().lower() == 'account':
                break
            user_click(menu_button)
        except StaleElementReferenceException:
            logger.warning(
                'Stale reference while waiting for homepage to load')
    logger.info('Authed login homepage - login complete')
    return True


def maybe_prompt_for_safeway_credentials(args):
    if not args.safeway_username and not args.safeway_user_will_login:
        args.safeway_username = input('Safeway email or phone: ')


if __name__ == '__main__':
    main()
