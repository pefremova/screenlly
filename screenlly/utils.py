import base64
from io import BytesIO
import os
import selenium
import subprocess
import tempfile
from time import sleep
import warnings

from PIL import Image
from selenium.webdriver.common.by import By


def find_element_by_xpath(driver, xpath):
    if selenium.__version__ < '4':
        return driver.find_element_by_xpath(xpath)
    return driver.find_element(By.XPATH, xpath)


def find_elements_by_xpath(driver, xpath):
    if selenium.__version__ < '4':
        return driver.find_elements_by_xpath(xpath)
    return driver.find_elements(By.XPATH, xpath)


def prepare_dimensions(path1, path2):
    """If image widths or heights differ make new tmp images with white background and same dimensions"""
    dimensions1 = subprocess.check_output(
        ('identify', '-format', '%w,%h', path1)
    ).decode('utf-8')
    dimensions2 = subprocess.check_output(
        ('identify', '-format', '%w,%h', path2)
    ).decode('utf-8')
    if dimensions1 != dimensions2:
        width1, height1 = dimensions1.split(',')
        width2, height2 = dimensions2.split(',')
        width = max(width1, width2)
        height = max(height1, height2)
        new_dimensions = 'x'.join([width, height])
        tmp_dir = tempfile.mkdtemp()
        new_path1 = os.path.join(tmp_dir, '1' + os.path.basename(path1))
        new_path2 = os.path.join(tmp_dir, '2' + os.path.basename(path2))
        command = (
            'convert',
            path1,
            '-background',
            'white',
            '-extent',
            new_dimensions,
            new_path1,
        )
        subprocess.call(command)
        command = (
            'convert',
            path2,
            '-background',
            'white',
            '-extent',
            new_dimensions,
            new_path2,
        )
        subprocess.call(command)
        return new_path1, new_path2
    return path1, path2


def compare_screenshots(path1, path2, result, diff_color='magenta'):
    path1, path2 = prepare_dimensions(path1, path2)
    p = subprocess.Popen(
        (
            'compare',
            '-dissimilarity-threshold',
            '1',
            '-metric',
            'AE',
            path1,
            path2,
            tempfile.mktemp(),
        ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    res, err = p.communicate()
    difference = float(res or err)
    if difference:
        command = (
            'convert',
            path1,
            '(',
            '-clone',
            '0',
            path2,
            '-compose',
            'difference',
            '-composite',
            '-threshold',
            '5%',
            '-fill',
            diff_color,
            '-opaque',
            'white',
            '-transparent',
            'black',
            ')',
            '-compose',
            'over',
            '-composite',
            result,
        )
        subprocess.call(command)
    return difference


def get_inner_window_size(driver):
    return driver.execute_script(
        'return {"width": window.innerWidth, "height": window.innerHeight};'
    )


def take_screenshot(
    driver,
    file_path,
    top_left=(0, 0),
    bottom_right=None,
    return_img=False,
    return_content=False,
    fixed_header_xpath=None,
    scrollable_element_xpath=None,
):
    def scroll_to(x, y):
        driver.execute_script("window.scrollTo(arguments[0], arguments[1]);", x, y)

    def element_scroll_to(el, x, y):
        driver.execute_script(
            "arguments[0].scrollTo(arguments[1], arguments[2]);", el, x, y
        )

    def get_current_x():
        return int(driver.execute_script("return window.pageXOffset;"))

    def get_current_y():
        return int(driver.execute_script("return window.pageYOffset;"))

    def element_get_current_x(el):
        return int(driver.execute_script("return arguments[0].scrollLeft;", el))

    def element_get_current_y(el):
        return int(driver.execute_script("return arguments[0].scrollTop;", el))

    def wait_position(x, y):
        i = 0
        current_x = current_y = -1
        while (
            current_x != x
            and current_y != y
            and get_current_x()
            < find_element_by_xpath(driver, '//body').size['width']
            - driver.get_window_size()['width']
            and get_current_y()
            < find_element_by_xpath(driver, '//body').size['height']
            - driver.get_window_size()['height']
        ) and i < 3:
            current_x = get_current_x()
            current_y = get_current_y()
            i += 1
            sleep(0.5)

    def element_wait_position(el, x, y):
        i = 0
        current_x = current_y = -1
        while (
            current_x != x
            and current_y != y
            and element_get_current_x(el)
            < (
                find_element_by_xpath(driver, '//body').size['width']
                - driver.get_window_size()['width']
            )
            and element_get_current_y(el)
            < (
                find_element_by_xpath(driver, '//body').size['height']
                - driver.get_window_size()['height']
            )
        ) and i < 3:
            current_x = element_get_current_x(el)
            current_y = element_get_current_y(el)
            i += 1
            sleep(0.5)

    def get_screen_piece():
        png = base64.b64decode(driver.get_screenshot_as_base64())
        im = Image.open(BytesIO(png))
        inner_window_size = get_inner_window_size(driver)
        im = im.resize((inner_window_size['width'], inner_window_size['height']))
        x1 = 0
        y1 = 0
        current_x = get_current_x()
        if current_x < top_left[0] or im.width == body_width:
            x1 = top_left[0]
        if current_x > 0:
            x1 = 0
        x2 = min(bottom_right[0], im.width)
        current_y = (
            element_get_current_y(scrollable_element)
            if scrollable_element
            else get_current_y()
        )
        if current_y < top_left[1] or im.height == body_height:
            y1 = top_left[1]
        if current_y > 0:
            y1 = fixed_header_height
        y2 = min(bottom_right[1], im.height)
        im = im.crop((x1, y1, x2, y2))
        return im

    scrollable_element = (
        find_element_by_xpath(driver, scrollable_element_xpath)
        if scrollable_element_xpath
        else None
    )
    if scrollable_element:
        element_scroll_to(scrollable_element, *top_left)
    else:
        scroll_to(*top_left)

    fixed_header_height = 0
    if fixed_header_xpath:
        elements = find_elements_by_xpath(driver, fixed_header_xpath)
        if elements:
            fixed_header_height = max(
                [el.location['y'] + int(el.size['height']) for el in elements]
            )

    body_height = driver.execute_script(
        'return Math.max(document.body.scrollHeight, document.body.offsetHeight, '
        'document.documentElement.clientHeight, document.documentElement.scrollHeight, '
        'document.documentElement.offsetHeight );'
    )
    if scrollable_element:
        body_height = max(
            [
                body_height,
                driver.execute_script(
                    'return arguments[0].scrollHeight', scrollable_element
                ),
            ]
        )
    body_width = driver.execute_script(
        'return Math.max(document.body.scrollWidth, document.body.offsetWidth, '
        'document.documentElement.clientWidth, document.documentElement.scrollWidth, '
        'document.documentElement.offsetWidth );'
    )
    if not bottom_right:
        bottom_right = (body_width, body_height)

    inner_window_size = get_inner_window_size(driver)
    if scrollable_element:
        element_wait_position(
            scrollable_element,
            0,
            min(top_left[1], body_height - inner_window_size['height']),
        )
    else:
        wait_position(0, min(top_left[1], body_height - inner_window_size['height']))

    img_height = rest_height = bottom_right[1] - top_left[1]
    img_width = bottom_right[0] - top_left[0]
    screenshot = Image.new('RGB', (int(img_width), int(img_height)))
    x_positions = [
        top_left[0],
    ]
    for n in range(1, int(bottom_right[0] / inner_window_size['width']) + 1):
        x_positions.append(min(inner_window_size['width'] * n, bottom_right[0]))
    x_positions.append(min(body_width, bottom_right[0]))

    y_positions = [
        top_left[1],
    ]
    for n in range(
        1,
        int(bottom_right[1] / (inner_window_size['height'] - fixed_header_height)) + 1,
    ):
        y_positions.append(
            min(
                (inner_window_size['height'] - fixed_header_height) * n, bottom_right[1]
            )
        )
    y_positions.append(min(body_height, bottom_right[1]) - fixed_header_height)

    for x_position in x_positions:
        for y_position in y_positions:
            if scrollable_element:
                element_scroll_to(scrollable_element, x_position, y_position)
                element_wait_position(scrollable_element, x_position, y_position)
            else:
                scroll_to(x_position, y_position)
                wait_position(x_position, y_position)
            im = get_screen_piece()
            current_x = (
                element_get_current_x(scrollable_element)
                if scrollable_element
                else get_current_x()
            )
            current_y = (
                element_get_current_y(scrollable_element)
                if scrollable_element
                else get_current_y()
            )
            screenshot.paste(
                im,
                (
                    current_x,
                    current_y + fixed_header_height if y_position > 0 else 0,
                ),
            )

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
    elements = find_elements_by_xpath(driver, element_xpath)
    file_name, ext = os.path.splitext(os.path.basename(file_path))
    dirname = os.path.dirname(file_path)
    file_paths = []
    for n, element in enumerate(elements):
        prepare_element(element, element_xpath)
        screen_name = os.path.join(
            dirname, file_name + ('_%d' % n if len(elements) > 1 else '') + ext
        )
        try:
            png = base64.b64decode(element.screenshot_as_base64)
            with open(screen_name, 'w') as screenshot:
                screenshot.write(png)
        except Exception as e:
            warnings.warn(
                'Exception on take screenshot for %s-th element %s. Screen element from full page screenshot\n%s'
                % (n, element_xpath, e)
            )
            location = element.location
            size = element.size
            x1 = int(location['x'])
            y1 = int(location['y'])
            x2 = location['x'] + int(size['width'])
            y2 = location['y'] + int(size['height'])

            take_screenshot(
                driver, screen_name, top_left=(x1, y1), bottom_right=(x2, y2)
            )
        finally:
            file_paths.append(screen_name)
    return file_paths


def get_element_part_screenshot(element, img_content):
    im = Image.open(BytesIO(img_content))
    location = element.location
    size = element.size
    im = im.crop(
        (
            location['x'],
            location['y'],
            location['x'] + size['width'],
            location['y'] + size['height'],
        )
    )
    output = BytesIO()
    im.save(output, format='PNG')
    return output.getvalue()
