import os
import re
from selenium import webdriver
import warnings
import urlparse


from .utils import compare_screenshots, take_screenshot


class ScreenCompare(object):

    def __init__(self, screenshots_path='', host=''):
        self.host = host
        self.screenshots_path = screenshots_path

    def name_from_url(self, url):
        name = re.sub('[/:]+', '_', re.sub('https?://', '', url))
        if len(name.strip('_')) > 0:
            return name.strip('_')
        return name

    def get_screenshot_path(self, url, browser):
        return os.path.join(self.screenshots_path, self.name_from_url(url), browser) + '.png'

    def compare(self, expected, tested, result):
        not_identical = []
        for el in os.walk(tested):
            for filename in el[-1]:
                new_screen = os.path.join(el[0], filename)
                relpath = os.path.relpath(new_screen, tested)
                old_screen = os.path.join(expected, relpath)
                if os.path.exists(old_screen):
                    result_screen = os.path.join(result, relpath)
                    if not os.path.exists(os.path.dirname(result_screen)):
                        os.makedirs(os.path.dirname(result_screen))
                    is_identical = compare_screenshots(old_screen, new_screen, result_screen)
                    if not is_identical:
                        not_identical.append(result_screen)
                else:
                    warnings.warn('No expected image for "%s" at path %s' % (filename, old_screen))
        return not_identical

    def take_screenshots(self, urls, browsers=None, grid_url=None, ):
        grid_url = grid_url or 'http://127.0.0.1:4444/wd/hub'
        browsers = browsers or {}
        for browser_name, browser in browsers.items():
            driver = webdriver.Remote(
                command_executor=grid_url,
                desired_capabilities=browser['desired_capabilities'])
            try:
                if browser.has_key('window_size'):
                    driver.set_window_size(*browser['window_size'])
                else:
                    driver.maximize_window()
                for url in urls:
                    try:
                        full_url = urlparse.urljoin(self.host, url)
                        driver.get(full_url)
                        screen_path = self.get_screenshot_path(url, browser_name)
                        if not os.path.exists(os.path.dirname(screen_path)):
                            os.makedirs(os.path.dirname(screen_path))
                        self.take_one_screenshot(driver, screen_path)
                    except Exception as e:
                        warnings.warn('Exception on page %s\n%s' % (full_url, e))
            except Exception as e:
                warnings.warn('Exception on setup driver %s' % browser_name)
            finally:
                driver.quit()

    def take_one_screenshot(self, driver, file_path=''):
        take_screenshot(driver, file_path)
