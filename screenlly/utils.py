import base64
from io import BytesIO
import os
import subprocess
import tempfile
from time import sleep

from PIL import Image
import warnings


def prepare_dimensions(path1, path2):
    """If image widths or heights differ make new tmp images with white background and same dimensions"""
    dimensions1 = subprocess.check_output(('identify', '-format', '%w,%h', path1)).decode('utf-8')
    dimensions2 = subprocess.check_output(('identify', '-format', '%w,%h', path2)).decode('utf-8')
    if dimensions1 != dimensions2:
        width1, height1 = dimensions1.split(',')
        width2, height2 = dimensions2.split(',')
        width = max(width1, width2)
        height = max(height1, height2)
        new_dimensions = 'x'.join([width, height])
        tmp_dir = tempfile.mkdtemp()
        new_path1 = os.path.join(tmp_dir, '1' + os.path.basename(path1))
        new_path2 = os.path.join(tmp_dir, '2' + os.path.basename(path2))
        command = ('convert', path1, '-background', 'white', '-extent', new_dimensions, new_path1)
        subprocess.call(command)
        command = ('convert', path2, '-background', 'white', '-extent', new_dimensions, new_path2)
        subprocess.call(command)
        return new_path1, new_path2
    return path1, path2


def compare_screenshots(path1, path2, result, diff_color='magenta'):
    path1, path2 = prepare_dimensions(path1, path2)
    p = subprocess.Popen(('compare', '-dissimilarity-threshold', '1', '-metric', 'AE', path1, path2, tempfile.mktemp()),
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    res, err = p.communicate()
    difference = float(res or err)
    if difference:
        command = ('convert', path1, '(', '-clone', '0', path2, '-compose', 'difference', '-composite', '-threshold', '5%',
                   '-fill', diff_color, '-opaque', 'white', '-transparent', 'black', ')', '-compose', 'over', '-composite', result)
        subprocess.call(command)
    return difference


def take_screenshot(driver, file_path, top_left=(0, 0), bottom_right=None,
                    return_img=False, return_content=False, fixed_header_xpath=None):

    def scroll_to(x, y):
        driver.execute_script("window.scrollTo(arguments[0], arguments[1]);", x, y)

    def get_current_y():
        return int(driver.execute_script("return window.pageYOffset;"))

    def wait_position(position):
        i = 0
        current = -1
        while (current != position and
               get_current_y() <
               driver.find_element_by_xpath('//body').size['height'] - driver.get_window_size()['height']) and i < 3:
            current = get_current_y()
            i += 1
            sleep(0.5)

    def get_screen_piece():
        png = base64.b64decode(driver.get_screenshot_as_base64())
        im = Image.open(BytesIO(png))
        x1 = top_left[0]
        x2 = bottom_right[0]
        y1 = 0
        if get_current_y() < top_left[1] or im.height == body_height:
            y1 = top_left[1]
        if get_current_y() > 0:
            y1 = fixed_header_height
        y2 = min(bottom_right[1], im.height)
        im = im.crop((x1, y1, x2, y2))
        return im

    scroll_to(*top_left)

    fixed_header_height = 0
    if fixed_header_xpath:
        elements = driver.find_elements_by_xpath(fixed_header_xpath)
        if elements:
            fixed_header_height = max([el.location['y'] + int(el.size['height']) for el in elements])

    body_height = driver.execute_script('return Math.max(document.body.scrollHeight, document.body.offsetHeight, '
                                        'document.documentElement.clientHeight, document.documentElement.scrollHeight, '
                                        'document.documentElement.offsetHeight );')
    body_width = driver.execute_script('return Math.max(document.body.scrollWidth, document.body.offsetWidth, '
                                       'document.documentElement.clientWidth, document.documentElement.scrollWidth, '
                                       'document.documentElement.offsetWidth );')
    if not bottom_right:
        bottom_right = (body_width, body_height)

    window_height = driver.execute_script('return window.innerHeight;') - 5
    wait_position(min(top_left[1], body_height - window_height))

    img_height = rest_height = bottom_right[1] - top_left[1]
    img_width = bottom_right[0] - top_left[0]
    screenshot = Image.new('RGB', (int(img_width), int(img_height)))

    y_positions = [top_left[1], ]
    for n in range(1, int(bottom_right[1] / (window_height - fixed_header_height)) + 1):
        y_positions.append(min((window_height - fixed_header_height) * n,
                               bottom_right[1]))
    y_positions.append(min(body_height, bottom_right[1]) - fixed_header_height)

    for y_position in y_positions:
        scroll_to(0, y_position)
        wait_position(y_position)
        im = get_screen_piece()
        screenshot.paste(im, (0, get_current_y() + fixed_header_height if y_position > 0 else 0))

    if return_content:
        output = BytesIO()
        screenshot.save(output, format='PNG')
        return output.getvalue()
    if return_img:
        return screenshot
    screenshot.save(file_path)
    return file_path


def take_element_screenshot(driver, file_path, element_xpath, prepare_element=None):
    dummy = lambda *args, **kwargs: None
    prepare_element = prepare_element or dummy
    elements = driver.find_elements_by_xpath(element_xpath)
    file_name, ext = os.path.splitext(os.path.basename(file_path))
    dirname = os.path.dirname(file_path)
    file_paths = []
    for n, element in enumerate(elements):
        prepare_element(element, element_xpath)
        screen_name = os.path.join(dirname, file_name + ('_%d' % n if len(elements) > 1 else '') + ext)
        try:
            png = base64.b64decode(element.screenshot_as_base64)
            with open(screen_name, 'w') as screenshot:
                screenshot.write(png)
        except Exception as e:
            warnings.warn('Exception on take screenshot for %s-th element %s. Screen element from full page screenshot\n%s' %
                          (n, element_xpath, e))
            location = element.location
            size = element.size
            x1 = int(location['x'])
            y1 = int(location['y'])
            x2 = location['x'] + int(size['width'])
            y2 = location['y'] + int(size['height'])

            take_screenshot(driver, screen_name, top_left=(x1, y1), bottom_right=(x2, y2))
        finally:
            file_paths.append(screen_name)
    return file_paths


def get_element_part_screenshot(element, img_content):
    im = Image.open(BytesIO(img_content))
    location = element.location
    size = element.size
    im = im.crop((location['x'], location['y'], location['x'] + size['width'], location['y'] + size['height']))
    output = BytesIO()
    im.save(output, format='PNG')
    return output.getvalue()
