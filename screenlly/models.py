import os
import re
from selenium import webdriver
import warnings
try:
    from urllib.parse import urlparse
except ImportError:
    import urlparse


from .utils import compare_screenshots, take_screenshot, take_element_screenshot


class ScreenCompare(object):

    def __init__(self, screenshots_path='',
                 host='',
                 grid_url='',
                 urls=None,
                 browsers=None,
                 elements_xpath=None):
        self.host = host
        self.screenshots_path = screenshots_path
        self.grid_url = grid_url or 'http://127.0.0.1:4444/wd/hub'
        self.urls = urls or []
        self.browsers = browsers or {}
        self.elements_xpath = elements_xpath or []

    def name_from_url(self, url):
        name = re.sub('[/:]+', '_', re.sub('https?://', '', url))
        if len(name.strip('_')) > 0:
            return name.strip('_')
        return name

    def get_screenshot_path(self, url, browser):
        return os.path.join(self.screenshots_path, self.name_from_url(url), browser) + '.png'

    def prepare_global(self, driver):
        pass

    def prepare_page(self, driver):
        pass

    def prepare_element(self, element, xpath):
        pass

    def update_report(self, file_paths, browser_name, url):
        pass

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

    def take_screenshots(self, urls=None, browsers=None, elements_xpath=None):
        urls = urls or self.urls
        browsers = browsers or self.browsers
        elements_xpath = elements_xpath or self.elements_xpath
        for browser_name, browser in browsers.items():
            driver = webdriver.Remote(
                command_executor=self.grid_url,
                desired_capabilities=browser['desired_capabilities'])
            try:
                if browser.has_key('window_size'):
                    driver.set_window_size(*browser['window_size'])
                else:
                    driver.maximize_window()
                self.prepare_global(driver)
                for url in urls:
                    try:
                        full_url = urlparse.urljoin(self.host, url)
                        driver.get(full_url)
                        screen_path = self.get_screenshot_path(url, browser_name)
                        if not os.path.exists(os.path.dirname(screen_path)):
                            os.makedirs(os.path.dirname(screen_path))
                        self.prepare_page(driver)
                        file_paths = self.take_page_screenshot(driver, screen_path, elements_xpath)
                        self.update_report(file_paths, browser_name, url)
                    except Exception as e:
                        warnings.warn('Exception on page %s\n%s' % (full_url, e))
            except Exception as e:
                warnings.warn('Exception on setup driver %s\n%s' % (browser_name, e))
            finally:
                driver.quit()

    def take_page_screenshot(self, driver, file_path='', elements_xpath=None):
        if elements_xpath:
            file_paths = []
            for n, el_xpath in enumerate(elements_xpath):
                filename = os.path.basename(file_path)
                dirname = os.path.dirname(file_path)
                if len(elements_xpath) > 1:
                    file_path = os.path.join(dirname, str(n), filename)
                if not os.path.exists(os.path.dirname(file_path)):
                    os.makedirs(os.path.dirname(file_path))
                file_paths.extend(take_element_screenshot(driver, file_path, el_xpath,
                                                          prepare_element=self.prepare_element))
            return file_paths
        else:
            return [take_screenshot(driver, file_path)]
