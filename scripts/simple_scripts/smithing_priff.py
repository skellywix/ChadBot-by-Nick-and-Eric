import pyautogui as pag
import functions as f
import time
import datetime
import cv2 as cv
import numpy as np
import world_hopper as wh
from pathlib import Path


TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "blast_furnace" / "templates"


# SETUP ----------------------------------------------------------------
def set_up():
    f.shift_camera_direction('south')
    pag.moveTo(1140 + f.p(0, 100), 500 + f.p(0, 100), f.r(0, 1))
    pag.scroll(-10000)
    pag.press('f2')


def bank_check():
    if not is_bank_open():
        raise RuntimeError("Bank is not open")
    if not tab_3():
        # print('Tab 3 not open!')
        f.move_click(755, 103)
    if not deposit_all_check():
        f.move_click(827, 824)


def function_test(func):
    while True:
        print(func())
        time.sleep(0.25)


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


def deposit_all_check():
    area = (839, 836, 10, 10)
    color = (67, 16, 15)
    return f.check_pixel_color_in_area(area, color, tolerance=5)


def tab_3():
    # current screenshot
    correct_tab = f.find(TEMPLATE_DIR / "tab_3.png", (749, 56, 100, 20), threshold=0.95)
    # print(correct_tab)
    if correct_tab:
        # print('Currently on tab 3!')
        return True
    else:
        # print('Not on tab 3!')
        return False


def at_anvil():
    if f.check_pixel_color_in_area((726, 303, 5, 5), (255, 152, 31), 5):
        return True
    else:
        return False


def at_furnace():
    area = (42, 894, 30, 5)
    color = (64, 48, 32)
    if f.check_pixel_color_in_area(area, color, tolerance=1):
        return True
    else:
        return False


def slot_empty(slot=28, inv_size=28):
    inv = f.create_inv(inv_size)
    slot_xy = list(inv.items())[(slot - 1)][1]
    # print(slot_xy)
    x, y = slot_xy[0] - 7, slot_xy[1] - 8
    img = f.take_screenshot(area=(x, y, 20, 20))
    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    if np.std(gray) < 2 or (gray.max() - gray.min()) < 5:
        return True  # found an empty slot
    return False  # no empty slots found
    # print(inv)


# MAIN LOGIC -------------------------
def wait_until(check_function, timeout=30, interval=0.25):
    start = time.time()
    while not check_function():
        if time.time() - start > timeout:
            print(f'Script ended at {datetime.datetime.now()}!')
            raise TimeoutError("Condition was not met in time.")
        time.sleep(interval)
    return True


def hop():
    pag.press('esc')
    wh.hop_world()
    set_up()
    pag.press('f2')
    f.move_click(919, 522)


def smith_mith_platebodies():
    f.move_click(935, 212)  # withdrawl mithril bar
    f.move_click(1180, 422)  # click anvil
    wait_until(at_anvil)
    f.move_click(753, 507)  # select platebody
    time.sleep(f.r(15, 17))  # wait
    f.move_click(657, 660)  # return to bank
    wait_until(is_bank_open)
    f.move_click(1745, 765)  # deposit platebodies


def smith_steel_platebodies():
    # about 133 inv/hour
    # ~27s per inv
    bank_check()
    f.move_click(839, 212)  # withdrawl addy bar
    f.move_click(1180, 422)  # click anvil
    wait_until(at_anvil)
    f.move_click(753, 507)  # select platebody
    time.sleep(f.r(15, 17))  # wait
    f.move_click(657, 660)  # return to bank
    wait_until(is_bank_open)
    f.move_click(1745, 765)  # deposit platebodies


def smith_addy_platebodies():
    f.move_click(985, 212)  # withdrawl addy bar
    f.move_click(1180, 422)  # click anvil
    wait_until(at_anvil)
    f.move_click(753, 507)  # select platebody
    time.sleep(f.r(15, 17))  # wait
    f.move_click(657, 660)  # return to bank
    wait_until(is_bank_open)
    f.move_click(1745, 765)  # deposit platebodies


def smith_rune_platelegs():
    f.move_click(840, 248)  # withdrawl rune bar
    f.move_click(1180, 422)  # click anvil
    wait_until(at_anvil)
    f.move_click(753, 399)  # select platelegs
    time.sleep(f.r(27, 28))  # wait
    f.move_click(657, 660)  # return to bank
    wait_until(is_bank_open)
    f.move_click(1745, 765)  # deposit items


def smith_addy_bolts():
    f.move_click(985, 212)  # withdrawal addy bar
    f.move_click(1180, 422)  # click anvil
    wait_until(at_anvil)
    f.move_click(982, 342)  # select bolts
    time.sleep(f.r(82, 85))  # wait
    f.move_click(657, 660)  # return to bank
    wait_until(is_bank_open)


def smith_cannonballs():
    #  average trip = 1 min 28.2 sec
    #  trips per hour ~40.4
    bank_check()
    f.move_click(839, 212)  # withdrawal steel bar
    f.move_click(1170, 340)  # click furnace
    wait_until(at_furnace)
    pag.press('space')  # select cannonballs
    time.sleep(f.r(60, 65))  # wait
    wait_until(slot_empty)  # Waits until cannonballs are done being made
    f.move_click(616, 736)  # return to bank
    wait_until(is_bank_open)


def main(setup=True):
    f.countdown(2)
    # Initialize script --------------
    print(f'Script started at {datetime.datetime.now()}')
    f.initialize_pag()
    start_time = time.time()  # Start timer for script
    if setup:
        set_up()

    # Main loop --------------
    # loops = round(130 * 4)
    loops = round((1910 - 100)/27) + 1
    # loops = 150
    print(f'Starting {loops} loops!')
    for n in range(1, loops):
        smith_rune_platelegs()
        if n == loops:
            hop()
        print(f'Inventory {n} done at {datetime.datetime.now()}')

    # End time --------------
    print(f'Script duration: {str(datetime.timedelta(seconds=time.time() - start_time))}')


if __name__ == "__main__":
    main(True)
