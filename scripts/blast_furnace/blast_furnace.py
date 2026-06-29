import pyautogui as pag
import functions as f
import time
import os
import datetime

project_dir = os.path.dirname(__file__)

ore_locations = {"gold": [980, 248],
                "addy": [888, 285],
                "mithril": [934, 285],
                "silver": [984, 285],
                "iron": [888, 321],
                "coal": [937, 321],
                "rune": [984, 321]}


def set_up():
    f.shift_camera_direction('east')
    pag.moveTo(1140 + f.p(0, 100), 500 + f.p(0, 100), f.r(0, 1))
    pag.scroll(-10000)
    pag.press('f2')


def is_bank_open():
    check_1 = f.check_pixel_color_in_area(search_region=(593, 59, 6, 6), target_color=(255, 152, 31), tolerance=5)
    check_2 = f.check_pixel_color_in_area(search_region=(1025, 827, 6, 6), target_color=(38, 250, 43), tolerance=5)
    if check_1 and check_2:
        # print('Bank is open!')
        return True
    else:
        # print('Bank is closed!')
        return False


# f.take_screenshot((778, 57, 35, 18), save_img=True, img_name='tab_3.png')


def tab_3():
    # current screenshot
    correct_tab = f.find('templates/tab_3.png', (749, 56, 100, 20), threshold=0.95)
    # print(correct_tab)
    if correct_tab:
        # print('Currently on tab 3!')
        return True
    else:
        # print('Not on tab 3!')
        return False


def deposit_all_check():
    area = (839, 836, 10, 10)
    color = (67, 16, 15)
    return f.check_pixel_color_in_area(area, color, tolerance=5)


def bank_check():
    if not is_bank_open():
        if not on_tile('green'):
            raise RuntimeError('Not in correct position.')
        else:
            f.move_click(975, 534, wait_duration=f.r(0.75, 1.0))
    if not is_bank_open():
        raise RuntimeError("Bank cannot be opened")
    if not tab_3():
        # print('Tab 3 not open!')
        f.move_click(755, 103)
    if not deposit_all_check():
        f.move_click(827, 824)


def on_tile(color):
    colors = {'green': (0, 255, 0), 'red': (255, 0, 0), 'blue': (0, 0, 255)}
    search_area = (953, 543, 10, 10)
    if f.check_pixel_color_in_area(search_area, colors[color], tolerance=1):
        return True
    else:
        return False


def bars_ready(bars):
    area = (0, 0, 100, 150)
    threshold = .97
    if f.find(bars, area, threshold):
        return True
    else:
        return False


def test_bars_ready():
    while True:
        print(bars_ready('27_rune.png'))
        time.sleep(0.5)


# test_bars_ready()


def wait_until(check_function, timeout=30, interval=0.25):
    start = time.time()
    while not check_function():
        if time.time() - start > timeout:
            print(f'Script ended at {datetime.datetime.now()}!')
            raise TimeoutError("Condition was not met in time.")
        time.sleep(interval)
    return True


def withdraw(ore, get_coal=True):
    global ore_locations
    if get_coal:
        f.move_click(1703, 768, move_duration=f.r(0.25, 0.55), wait_duration=f.r(0.15, 0.3))  # fill coal bag
    f.move_click(*ore_locations[ore])  # withdraw specified ore


def take_bars():
    start_time = time.time()
    while True:
        xy = f.find_option('templates/take.png', (974, 526))
        # print(xy)
        if xy:
            f.move_click(*xy, move_duration=f.r(0.15, 0.30), wait_duration=f.r(0.1, 0.2))
            time.sleep(f.r(0.5, 0.75))
            pag.press('space')
            time.sleep(f.r())
            return True
        if time.time() - start_time > 15:
            raise TimeoutError("Could not find TAKE option")
        pag.move(f.p(100), f.p(-100, -50))
        time.sleep(f.r(0.2, 0.3))


def deposit_ores(bar_type, bank=True):
    # Starting from bank tile
    f.move_click(550, 691, move_duration=f.r(0.5, 0.8), wait_duration=f.r(0.5, 0.75))  # move and deposit to furnace
    pag.moveTo(1703 + f.p(), 768 + f.p(), f.r())
    wait_until(lambda: on_tile('blue'))
    pag.click()
    f.move_click(944, 506, move_duration=f.r(0.25, 0.75), wait_duration=f.r(0.5, 0.75))  # deposit coal to furnace
    if bank:
        f.move_click(1230, 408, move_duration=f.r(0.5, 1.0))  # return to bank
        wait_until(is_bank_open)
    else:
        f.move_click(1034, 610, move_duration=f.r(0.25, 0.75))
        wait_until(lambda: on_tile('red'))
        wait_until(lambda: bars_ready(bar_type))
        take_bars()
        f.move_click(1160, 328, move_duration=f.r(0.5, 0.75))  # go to bank
        pag.moveTo(1746 + f.p(), 764 + f.p(), f.r())
        wait_until(is_bank_open)
        pag.click()  # deposit bars


def deposit_special(bar_type, bank=False):
    f.move_click(550, 691, move_duration=f.r(0.5, 0.8), wait_duration=f.r(0.5, 0.75))  # move and deposit to furnace
    wait_until(lambda: on_tile('blue'))
    if bank:
        f.move_click(1230, 408, move_duration=f.r(0.5, 1.0))  # return to bank
        wait_until(is_bank_open)
    else:
        f.move_click(1034, 610, move_duration=f.r(0.25, 0.75))
        wait_until(lambda: on_tile('red'))
        wait_until(lambda: bars_ready(bar_type))
        f.move_click(1706, 766)  # Equip ice gauntlets
        take_bars()
        f.move_click(1706, 766)  # Re-equip goldsmith gauntlets
        f.move_click(1160, 328, move_duration=f.r(0.5, 0.75))  # go to bank
        pag.moveTo(1746 + f.p(), 764 + f.p(), f.r())
        wait_until(is_bank_open)
        pag.click()  # deposit bars


def drink_stam(goldsmith=False):
    f.move_click(917, 104)
    f.move_click(791, 326)
    pag.press('esc')
    f.move_click(1746, 771)
    bank_check()
    f.move_click(1003, 825)  # Deposit all
    if goldsmith:
        f.move_click(681, 823)
        f.move_click(840, 141)
        f.move_click(828, 823)
    else:
        f.move_click(695, 143)


def make_steel_bars(n):
    # stamina dose required after first 6 trips, ran out of stamina on 5th trip after a dose. Dose every 5 trips
    bank_check()
    withdraw('iron')
    deposit_ores('templates/27_steel.png', bank=False)
    if n % 10 == 0:
        drink_stam()


def make_addy_bars(n):
    # stamina dose required after first 6 trips, ran out of stamina on 5th trip after a dose. Dose every 5 trips
    bank_check()
    withdraw('coal')
    deposit_ores('templates/27_addy.png')
    withdraw('addy')
    deposit_ores('templates/27_addy.png', bank=False)
    if n % 5 == 0:
        drink_stam()


def make_rune_bars(n):
    # Dose every 2 trips
    bank_check()
    withdraw('coal')
    deposit_ores('templates/27_rune.png')
    withdraw('coal')
    deposit_ores('templates/27_rune.png')
    withdraw('rune')
    deposit_ores('templates/27_rune.png', bank=False)
    withdraw('coal')
    deposit_ores('templates/27_rune.png')
    withdraw('rune')
    deposit_ores('templates/27_rune.png', bank=False)
    if n % 2 == 0:
        drink_stam()


def make_mith_bars(n):
    # stamina dose required after first 6 trips, ran out of stamina on 5th trip after a dose. Dose every 5 trips
    bank_check()
    withdraw('coal')
    deposit_ores('templates/27_mith.png')
    withdraw('mithril')
    deposit_ores('templates/27_mith.png', bank=False)
    withdraw('mithril')
    deposit_ores('templates/27_mith.png', bank=False)
    if n % 3 == 0:
        drink_stam()


def make_gold_bars(n):
    #  Dose every 12 trips
    bank_check()
    withdraw('gold', get_coal=False)
    deposit_special('templates/27_gold.png')
    if n % 10 == 0:
        drink_stam(goldsmith=True)


def make_silver_bars(n):
    #  Dose every 12 trips
    bank_check()
    withdraw('silver', get_coal=False)
    deposit_special('templates/27_silver.png')
    if n % 10 == 0:
        drink_stam(goldsmith=True)


def main(setup=True):
    f.countdown(1)
    # Initialize script --------------
    print(f'Script started at {datetime.datetime.now()}')
    f.initialize_pag()
    start_time = time.time()  # Start timer for script
    if setup:
        set_up()

    # Main loop --------------
    # ~144 loops per hour
    # loops = round(144 * 3)
    loops = round((25000-100)/27) + 1
    print(f'Starting {loops} loops!')
    for n in range(1, loops):
        make_steel_bars(n)
        print(f'Inventory {n} done at {datetime.datetime.now()}')

    # End time --------------
    print(f'Script duration: {str(datetime.timedelta(seconds=time.time() - start_time))}')


if __name__ == "__main__":
    main(True)
