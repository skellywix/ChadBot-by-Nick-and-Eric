import pyautogui as pag
import functions as f
import digit_extractor as de
import world_hopper as wh
import datetime
import time
import cv2 as cv
import numpy as np


# SETUP ----------------------------------------------------------------
def set_up():
    f.shift_camera_direction('east')
    pag.moveTo(1140 + f.p(0, 100), 500 + f.p(0, 100), f.r(0, 1))
    pag.scroll(-10000)
    pag.press('f2')


def bank_check():
    if not is_bank_open():
        f.move_click(975, 534, wait_duration=f.r(0.75, 1.0))
    if not is_bank_open():
        raise RuntimeError("Bank cannot be opened")
    if not deposit_all_check():
        f.move_click(827, 824)


# TRUE/FALSE CHECKS ----------------------------------------------------------------
def is_bank_open():
    check_1 = f.check_pixel_color_in_area(search_region=(593, 59, 6, 6), target_color=(255, 152, 31), tolerance=5)
    check_2 = f.check_pixel_color_in_area(search_region=(1025, 827, 6, 6), target_color=(38, 250, 43), tolerance=5)
    if check_1 and check_2:
        # print('Bank is open!')
        return True
    else:
        # print('Bank is closed!')
        return False


def is_shop_open():
    check_1 = f.find('ore_seller.png', (772, 305, 120, 50), threshold=0.92)
    if check_1:
        # print('Shop is open!')
        return True
    else:
        # print('Shop is closed!')
        return False


def deposit_all_check():
    area = (839, 836, 10, 10)
    color = (67, 16, 15)
    return f.check_pixel_color_in_area(area, color, tolerance=5)


def on_tile(color):
    colors = {'green': (0, 255, 0), 'red': (255, 0, 0), 'blue': (0, 0, 255), 'purple': (255, 0, 255)}
    search_area = (953, 543, 10, 10)
    return f.check_pixel_color_in_area(search_area, colors[color], tolerance=1)


def full_inventory():
    inv = f.create_inv(28)
    for cx, cy in inv.values():
        x = cx - 7
        y = cy - 8
        img = f.take_screenshot(area=(x, y, 20, 20))
        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        if np.std(gray) < 2 or (gray.max() - gray.min()) < 5:
            return False  # found an empty slot
    return True  # no empty slots found


def run_on():
    run = f.find('templates/run_on.png', (1714, 140, 40, 40), threshold=0.95)
    # print(run)
    if run:
        return True
    else:
        return False


# MAIN LOGIC-------------------------------------------------
def wait_until(check_function, timeout=30, interval=0.25):
    start = time.time()
    while not check_function():
        if time.time() - start > timeout:
            print(f'Script ended at {datetime.datetime.now()}!')
            raise TimeoutError("Condition was not met in time.")
        time.sleep(interval)
    return True


def activate_run():
    if not run_on():
        f.move_click(1727, 150)
    else:
        pass


def switch_world():
    pag.press('esc')
    wait_until(lambda: not (is_shop_open()))
    wh.hop_world()
    time.sleep(f.r(1, 2))
    pag.press('f2')


def iron_count():
    ore_count = f.take_screenshot((726, 337, 30, 20))
    num = de.read_digits(ore_count)
    return num


def go_shop():
    f.move_click(543, 1026)
    wait_until(is_shop_open)


def deposit_bank():
    f.move_click(1173, 252)
    wait_until(is_bank_open)
    f.move_click(1746, 764)


def open_shop():
    timeout = 30
    start = time.time()
    while not time.time() - start > timeout:
        if on_tile('purple'):
            f.move_click(911, 528)
            time.sleep(f.r(1, 4))
            if is_shop_open():
                return None
    print(f'Script ended at {datetime.datetime.now()}!')
    raise TimeoutError("Could not buy full inventory in 5 minutes!.")


def buy_full_inv():
    timeout = 300
    start = time.time()
    while not full_inventory():
        if time.time() - start > timeout:
            print(f'Script ended at {datetime.datetime.now()}!')
            raise TimeoutError("Could not buy full inventory in 5 minutes!.")
        iron = iron_count()
        if iron is None or iron < 1:
            switch_world()
            open_shop()
        else:
            f.move_click(745, 358)
            time.sleep(f.r(0.1, 0.2))
            # print('Buying iron!')


def full_trip():
    activate_run()
    go_shop()
    buy_full_inv()
    deposit_bank()


def main(setup=True):
    # Initialize script --------------
    f.countdown(1)
    print(f'Script started at {datetime.datetime.now()}')
    f.initialize_pag()
    start_time = time.time()  # Start timer for script
    if setup:
        set_up()

    # Main loop --------------
    hops = 0
    for n in range(1, 1200):
        full_trip()
        print(f'Inventory {n} done at {datetime.datetime.now()}')

    # End time --------------
    print(f'Script duration: {str(datetime.timedelta(seconds=time.time() - start_time))}')


if __name__ == "__main__":
    main(True)
