import pyautogui as pag
import functions as f
import time
import os
import datetime
import cv2 as cv
import numpy as np


project_dir = os.path.dirname(__file__)


def set_up():
    f.shift_camera_direction(direction='west', up=True)


def check_inv():
    full = f.find_spots('inv_full_slot.png', threshold=0.95, area=(1800, 960, 70, 60))
    if full:
        full = False
        # print('Inventory not full!')
    else:
        full = True
        # print('Inventory full!')
    return full


def check_if_wc(t=5):
    elapsed_time = 0
    start_time = time.time()
    print('Destroying mother nature ...', end='')
    time.sleep(3 + f.r(1, 2))
    while elapsed_time < 240:
        if pag.pixelMatchesColor(24, 52, (255, 0, 0), tolerance=t):
            time.sleep(3 + f.r(1, 2))
            print(' Not chopping!')
            break
        elif pag.pixelMatchesColor(38, 58, (0, 255, 0), tolerance=t):
            print('.', end='')
            elapsed_time = time.time() - start_time
            time.sleep(4 + f.r(1, 2))
        else:
            print(' No overlay found!')
            time.sleep(10)
            break
    if elapsed_time >= 240:
        print('')


def identify_position(t=10):
    if check_pixel_color_in_area(search_region=(990, 547, 6, 6), target_color=(0, 255, 0), tolerance=5):
        print('On blue tile.')
        return 'blue'
    else:
        print('On green tile.')
        return 'green'


def swap_position(current_tile=None):
    if current_tile is None:
        current_tile = identify_position()
    if current_tile == 'blue':
        f.move_click(977, 532)
        time.sleep(f.r(2, 3))
    else:
        f.move_click(911, 534)
        time.sleep(f.r(2, 3))


def eradicate_nature():
    tree_available = check_pixel_color_in_area()
    if not tree_available:
        f.move_click(945, 483)
        pag.move(f.r(-100, 100), -f.r(30, 100), f.r())
        time.sleep(f.r(2, 4))
    else:
        swap_position()
        f.move_click(945, 483)
        pag.move(f.r(-100, 100), -f.r(30, 100), f.r())
        time.sleep(f.r(2, 4))


def check_pixel_color_in_area(search_region=(944, 484, 12, 4), target_color=(255, 255, 0), tolerance=5):
    """
    Checks if the target color exists within the specified area of the image.
    Args:
        search_region (tuple): Tuple containing (top left x coordinate, top left y coordinate, width, height) of
        the search area.
        target_color (tuple): BGR color tuple to check for (e.g., (0, 0, 255) for red).
        tolerance (int):
    Returns:
        bool: True if the color is found, False otherwise.
    """
    s = search_region
    x, y, w, h = s[0], s[1], s[2], s[3]
    pixel_match = False

    for p in range(x, (x + w + 1)):
        for p2 in range(y, (y + h + 1)):
            pixel_match = pag.pixelMatchesColor(p, p2, target_color, tolerance=tolerance)
            if pixel_match:
                break
        if pixel_match:
            break

    if pixel_match:
        return True
    else:
        return False


def bank_logs():
    position = identify_position()
    print(position)
    if position == 'blue':
        swap_position('blue')
    f.play_actions('bank_redwoods.json', project_dir)
    time.sleep(f.r(10, 15))


def main(setup=False):
    f.countdown(1)  # Countdown till code begins
    f.initialize_pag()  # Initialize failsafe
    start_time = time.time()  # Start timer for script

    if setup:
        set_up()

    for n in range(1, 30):  # Number of inventories to do
        full = check_inv()
        while full is False:
            eradicate_nature()
            check_if_wc()
            full = check_inv()
        bank_logs()
        print(f'Inventory {n} done at {datetime.datetime.now()}')
    print(f'Script duration: {str(datetime.timedelta(seconds=time.time() - start_time))}')


if __name__ == "__main__":
    main()

