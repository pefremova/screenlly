import base64
from io import BytesIO
import os
import subprocess
import tempfile
from time import sleep

from PIL import Image


def prepare_dimensions(path1, path2):
    """If image widths or heights differ make new tmp images with white background and same dimensions"""
    dimensions1 = subprocess.check_output(('identify', '-format', '%w,%h', path1))
    dimensions2 = subprocess.check_output(('identify', '-format', '%w,%h', path2))
    if dimensions1 != dimensions2:
        width1, height1 = dimensions1.split(',')
        width2, height2 = dimensions2.split(',')
        width = max(width1, width2)
        height = max(height1, height2)
        new_dimensions = 'x'.join([width, height])
        tmp_dir = tempfile.mkdtemp()
        new_path1 = os.path.join(tmp_dir, path1)
        new_path2 = os.path.join(tmp_dir, path2)
        command = ('convert', path1, '-background', 'white', '-extent', new_dimensions, new_path1)
        subprocess.call(command)
        command = ('convert', path2, '-background', 'white', '-extent', new_dimensions, new_path2)
        subprocess.call(command)
        return new_path1, new_path2
    return path1, path2


def compare_screenshots(path1, path2, result):
    path1, path2 = prepare_dimensions(path1, path2)
    p = subprocess.Popen(('compare', '-dissimilarity-threshold', '1', '-metric', 'AE', path1, path2, tempfile.mktemp()),
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    res, err = p.communicate()
    is_identical = not float(res or err)
    if not is_identical:
        command = ('convert', path1, '(', '-clone', '0', path2, '-compose', 'difference', '-composite', '-threshold', '5%',
                   '-fill', 'magenta', '-opaque', 'white', '-transparent', 'black', ')', '-compose', 'over', '-composite', result)
        subprocess.call(command)
    return is_identical


def take_screenshot(driver, file_path):
    driver.execute_script("window.scrollTo(0, 0);")

    def wait_position(position):
        i = 0
        current = -1
        while (current != position and
               driver.execute_script("return window.pageYOffset;") <
               driver.find_element_by_xpath('//body').size['height'] - driver.get_window_size()['height']) and i < 3:
            current = driver.execute_script("return window.pageYOffset;")
            i += 1
            sleep(0.5)

    wait_position(0)
    size = driver.find_element_by_xpath('//body').size
    height = rest_height = size['height']
    window_height = driver.execute_script('return window.innerHeight;') - 5
    screenshot = Image.new('RGB', (int(size['width']), int(size['height'])))

    while rest_height > window_height:
        png = base64.b64decode(driver.get_screenshot_as_base64())
        im = Image.open(BytesIO(png))
        screenshot.paste(im, (0, int(driver.execute_script("return window.pageYOffset;"))))
        rest_height = rest_height - window_height
        driver.execute_script("window.scrollTo(0, %s);" % (height - rest_height))
        wait_position(height - rest_height)

    png = base64.b64decode(driver.get_screenshot_as_base64())
    im = Image.open(BytesIO(png))
    screenshot.paste(im, (0, int(driver.execute_script("return window.pageYOffset;"))))

    screenshot.save(file_path)
    return file_path
