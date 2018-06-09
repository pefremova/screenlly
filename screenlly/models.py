import os
import re
from selenium import webdriver
import warnings
from selenium.common.exceptions import StaleElementReferenceException
try:
    from urllib import parse as urlparse
except ImportError:
    import urlparse


from .utils import compare_screenshots, take_screenshot, take_element_screenshot


class ScreenCompare(object):

    def __init__(self, screenshots_path='',
                 host='',
                 grid_url='',
                 urls=None,
                 browsers=None,
                 elements_xpath=None,
                 hide_elements_xpath=None):
        self.host = host
        self.screenshots_path = screenshots_path
        self.grid_url = grid_url or 'http://127.0.0.1:4444/wd/hub'
        self.urls = urls or []
        self.browsers = browsers or {}
        self.elements_xpath = elements_xpath or []
        self.hide_elements_xpath = hide_elements_xpath or []

    def name_from_url(self, url):
        name = re.sub('[/:]+', '_', re.sub('https?://', '', url))
        if len(name.strip('_')) > 0:
            return name.strip('_')
        return name

    def get_screenshot_path(self, url, browser):
        return os.path.join(self.screenshots_path, self.name_from_url(url), browser) + '.png'

    def hide_elements(self, driver):
        for element_xpath in self.hide_elements_xpath:
            elements = driver.find_elements_by_xpath(element_xpath)
            for element in elements:
                try:
                    driver.execute_script("var ele=arguments[0]; ele.innerHTML = '<div style=\"text-align:center; "
                                          "width:{width}px; height:{height}px; background-color:yellow; color:black\"></div>';".format(
                                              **element.size),
                                          element)
                except StaleElementReferenceException:
                    pass

    def prepare_global(self, driver):
        pass

    def prepare_page(self, driver, url):
        pass

    def prepare_element(self, element, xpath):
        pass

    def update_report(self, file_paths, browser_name, url):
        pass

    def update_report_compare(self, difference, old_screen, new_screen, result_screen,
                              expected, tested, result):
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
                    difference = compare_screenshots(old_screen, new_screen, result_screen)
                    if difference:
                        not_identical.append(result_screen)
                    self.update_report_compare(difference, old_screen, new_screen, result_screen,
                                               expected, tested, result)
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
                if 'window_size' in browser:
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
                        self.hide_elements(driver)
                        self.prepare_page(driver, url)
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
