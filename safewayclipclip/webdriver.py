import logging
import psutil

from selenium.common.exceptions import InvalidArgumentException, NoSuchElementException

# from selenium.webdriver import Chrome
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.by import By

from selenium_stealth import stealth
from undetected_chromedriver import Chrome

logger = logging.getLogger(__name__)


def get_webdriver(headless=False, session_path=None):
    chrome_options = ChromeOptions()
    if session_path is not None:
        chrome_options.add_argument(f"--user-data-dir={session_path}")

    webdriver = Chrome(options=chrome_options)
    # stealth(
    #     webdriver,
    #     languages=["en-US", "en"],
    #     vendor="Google Inc.",
    #     platform="Win32",
    #     webgl_vendor="Intel Inc.",
    #     renderer="Intel Iris OpenGL Engine",
    #     fix_hairline=True,
    # )
    return webdriver


def is_visible(element):
    return element and element.is_displayed()


def get_element_by_id(driver, id):
    try:
        return driver.find_element(By.ID, id)
    except NoSuchElementException:
        pass
    return None


def get_element_by_name(driver, name):
    try:
        return driver.find_element(By.NAME, name)
    except NoSuchElementException:
        pass
    return None


def get_element_by_xpath(driver, xpath):
    try:
        return driver.find_element(By.XPATH, xpath)
    except NoSuchElementException:
        pass
    return None


def get_element_by_link_text(driver, link_text):
    try:
        return driver.find_element(By.LINK_TEXT, link_text)
    except NoSuchElementException:
        pass
    return None


def get_elements_by_class_name(driver, class_name):
    try:
        return driver.find_elements(By.CLASS_NAME, class_name)
    except NoSuchElementException:
        pass
    return None


def get_elements_by_xpath(driver, xpath):
    try:
        return driver.find_elements(By.XPATH, xpath)
    except NoSuchElementException:
        pass
    return None
