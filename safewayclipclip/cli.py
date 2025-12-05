#!/usr/bin/env python3

# This script clips all available Safeway coupons.

import argparse
import atexit
from datetime import datetime
import logging
import os
from pprint import pprint
import random
import time

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    JavascriptException,
    StaleElementReferenceException,
)
from selenium.webdriver import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from safewayclipclip import VERSION
from safewayclipclip.args import define_common_args, BASE_PATH
from safewayclipclip.webdriver import (
    get_webdriver,
    get_element_by_id,
    get_element_by_name,
    get_element_by_xpath,
    get_element_by_link_text,
    get_elements_by_class_name,
    get_elements_by_xpath,
    is_visible,
)


logger = logging.getLogger(__name__)


SAFEWAY_HOME = "https://www.safeway.com"
# FOR_U = "{}/justforu/coupons-deals.html".format(SAFEWAY_HOME)
LOGIN_THEN_FOR_U = "{}/account/sign-in.html?goto=/foru/coupons-deals.html".format(
    SAFEWAY_HOME
)
COUPON_URL = "{}/loyalty/coupons-deals".format(SAFEWAY_HOME)

COUPON_BUTTON_XPATH = (
    '//button[contains(text(), "Activate") or contains(text(), "Clip Coupon")]'
)


def main():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(logging.StreamHandler())
    # Disable noisy log spam from filelock from within tldextract.
    logging.getLogger("filelock").setLevel(logging.WARN)

    # For helping remote debugging, also log to file.
    # Developers should be vigilant to NOT log any PII, ever (including being
    # mindful of what exceptions might be thrown).
    log_directory = os.path.join(BASE_PATH, "Logs")
    os.makedirs(log_directory, exist_ok=True)
    log_filename = os.path.join(
        log_directory, "{}.log".format(time.strftime("%Y-%m-%d_%H-%M-%S"))
    )
    root_logger.addHandler(logging.FileHandler(log_filename))

    parser = argparse.ArgumentParser(description="Clip Safeway coupons.")
    define_common_args(parser)
    args = parser.parse_args()

    if args.version:
        print("SafewayClipClip {}\nBy: Jeff Prouty".format(VERSION))
        exit(0)

    webdriver = get_webdriver(args.headless, args.session_path)
    webdriver.implicitly_wait(2)

    def close_webdriver():
        webdriver.close()

    atexit.register(close_webdriver)

    webdriver.get(LOGIN_THEN_FOR_U)
    # Wait - there is sometimes a redirect here.
    time.sleep(2)
    logger.info("At Safeway For U coupons page: {}".format(webdriver.current_url))
    if not login_if_needed(webdriver, args):
        logger.error("Cannot login - exiting")
        time.sleep(60)
        return

    # Accept cookies bottom

    # while True:
    coupons_clip_clip = get_elements_by_xpath(webdriver, COUPON_BUTTON_XPATH)
    if not coupons_clip_clip:
        logger.error("Cannot find coupons")
        time.sleep(60)
        return

    accept_all_cookies = get_element_by_xpath(
        webdriver, '//button[contains(text(), "Accept All")]'
    )
    if is_visible(accept_all_cookies):
        user_click(webdriver, accept_all_cookies)

    # Avoid stale ref error by getting a new list of buttons after each click
    while coupons_clip_clip:
        try:
            user_click(webdriver, coupons_clip_clip[0])
            # logger.info("Clipped a coupon!")
        except ElementClickInterceptedException:
            logger.exception("Click interception error; continuing")
        except StaleElementReferenceException:
            logger.exception("Stale ref error; continuing")
        except JavascriptException:
            logger.exception("JS error; continuing")

        # time.sleep(1)

        close_modal_button = get_element_by_xpath(
            webdriver, '//*[@id="errorModal"]//button[contains(text(), "Close")]'
        )
        if is_visible(close_modal_button):
            user_click(webdriver, close_modal_button)
            logger.info("Closed modal dialog")

        coupons_clip_clip = get_elements_by_xpath(webdriver, COUPON_BUTTON_XPATH)

        # No need to load more - clipped ones disappear and new ones come in.
        # load_mores = get_elements_by_class_name(webdriver, "load-more")
        # if not load_mores or not is_visible(load_mores[0]):
        #     logger.warning(
        #         'Cannot find "Load more" button; either done or unexpectedly ' "missing"
        #     )
        #     break
        # logger.info("Clicking load more!")
        # user_click(load_mores[0])
        # time.sleep(2)
    logger.info("All done! Sleeping for 5m before exiting to allow for review")
    time.sleep(60 * 5)


def user_click(webdriver, elem):
    rand_user_delay()
    ActionChains(webdriver).move_to_element(elem).click().perform()
    # elem.click()


def rand_user_delay():
    rand_sleep_time_s = random.randint(250, 1250) / 1000.0
    time.sleep(rand_sleep_time_s)


def on_critical(msg):
    logger.critical(msg)
    exit(1)


PROFILE_NAME_XPATH = "//a[contains(concat(' ',normalize-space(@class),' '),' menu-nav__profile-button ')]/span[1]"


def login_if_needed(webdriver, args):
    # Already logged in.
    profile_name_element = get_element_by_xpath(webdriver, PROFILE_NAME_XPATH)
    if (
        is_visible(profile_name_element)
        and profile_name_element.text.strip() != "Sign in"
    ):
        logger.error("Already logged in")
        return True

    maybe_prompt_for_safeway_credentials(args)

    if webdriver.current_url != LOGIN_THEN_FOR_U:
        webdriver.get(LOGIN_THEN_FOR_U)

    username_input = get_element_by_id(webdriver, "enterUsername")
    if not username_input:
        logger.error("Cannot find user input element")
        return False
    rand_user_delay()
    username_input.send_keys(args.safeway_username)

    sign_in_with_password_button = get_element_by_xpath(
        webdriver, '//button[contains(text(), "Sign in with password")]'
    )
    if not sign_in_with_password_button:
        logger.error("Cannot find 'Sign in with password' button")
        return False
    user_click(webdriver, sign_in_with_password_button)

    password_input = get_element_by_id(webdriver, "password")
    if not password_input:
        logger.error("Cannot find password input element")
        return False
    rand_user_delay()
    password_input.send_keys(args.safeway_password)

    sign_in_button = get_element_by_xpath(
        webdriver, '//button[contains(text(), "Sign In")]'
    )
    if not sign_in_button:
        logger.error("Cannot find 'Sign In' button")
        return False
    user_click(webdriver, sign_in_button)

    # Delay to allow for any 2FA or captcha.
    logger.info("Waiting up to 120s for any 2FA or captcha...")
    wait = WebDriverWait(webdriver, 2 * 60)
    wait.until(EC.url_to_be(COUPON_URL))

    logger.info("Login flow complete!")
    profile_name_element = get_element_by_xpath(webdriver, PROFILE_NAME_XPATH)
    return (
        is_visible(profile_name_element)
        and profile_name_element.text.strip() != "Sign in"
    )


def maybe_prompt_for_safeway_credentials(args):
    if not args.safeway_username and not args.safeway_user_will_login:
        args.safeway_username = input("Safeway email or phone: ")
    if not args.safeway_password and not args.safeway_user_will_login:
        args.safeway_password = input("Safeway password: ")


if __name__ == "__main__":
    main()
