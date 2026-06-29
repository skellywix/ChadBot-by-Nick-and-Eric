import pyautogui as pag
import functions as f
import time
import os
import datetime


project_dir = os.path.dirname(__file__)


def set_up():
    f.shift_camera_direction('north')
    pag.moveTo(1040 + f.p(0, 100), 500 + f.p(0, 100), f.r(0, 1))
    pag.scroll(-10000)


def check_if_mining(t=5):
    elapsed_time = 0
    start_time = time.time()
    print('Mining ...', end='')
    while elapsed_time < 120:
        if pag.pixelMatchesColor(40, 121, (255, 0, 0), tolerance=t):
            print('Not mining!')
            break
        elif pag.pixelMatchesColor(52, 120, (0, 255, 0), tolerance=t):
            print('.', end='')
            elapsed_time = time.time() - start_time
            time.sleep(4 + f.r(1, 2))
        else:
            print('No overlay found!')
            time.sleep(10)
            break


def identify_position(t=10):
    blue_tile = f.check_pixel_color_in_area(search_region=(943, 546, 6, 6), target_color=(0, 0, 255), tolerance=5)
    green_tile = f.check_pixel_color_in_area(search_region=(943, 547, 6, 6), target_color=(0, 255, 0), tolerance=5)
    if blue_tile:
        return 'blue'
    if green_tile:
        return 'green'
    else:
        raise Exception('Not on green or blue tile. Stopping script!')


def swap_position(current_tile=None):
    if current_tile is None:
        current_tile = identify_position()
    if current_tile == 'blue':
        f.move_click(977, 532)
        time.sleep(f.r(2, 3))
    else:
        f.move_click(911, 534)
        time.sleep(f.r(2, 3))


def mine():
    pag.moveTo(500 + f.p(), 300 + f.p(), f.r())
    mining_tile = identify_position()
    if mining_tile != 'blue' and mining_tile != 'green':
        raise Exception('Not on green or blue tile. Stopping script!')
    ore_available = not(f.check_pixel_color_in_area(search_region=(940, 474, 6, 6),
                                                    target_color=(255, 255, 0), tolerance=5))
    if ore_available:
        f.move_click(945, 483)
        pag.move(f.r(-100, 100), -f.r(150, 200), f.r())
        time.sleep(f.r(2, 4))
    if not ore_available:
        swap_position()
        f.move_click(945, 483)
        pag.move(f.r(-100, 100), -f.r(150, 200), f.r())
        time.sleep(f.r(2, 4))


def check_inv():
    full = f.find_spots('inv_full_slot.png', threshold=0.95, area=(1800, 960, 70, 60))
    if full:
        full = False
        print('Inventory not full!')
    else:
        full = True
        print('Inventory full!')
    # hopper_full = pag.pixel(41, 70) == (255, 0, 0)
    # if hopper_full:
    #     print('Hopper is full')
    #     full = True

    return full


def deposit_in_hopper(n):
    position = identify_position()
    if position == 'green':
        swap_position('green')

    f.move_click(1051, 740)
    time.sleep(f.r(6, 7))
    if n % 4 != 0:
        small_fix = check_strut_from_upper()
        if small_fix:
            collect_ores()
            repair_struts()
            f.move_click(1076, 185, wait_duration=f.r(8.5, 9))
            f.move_click(862, 320)
            time.sleep(f.r(5, 6))  # returns to mining position after fixing struts
        else:
            f.move_click(887, 366)
            time.sleep(f.r(5, 6))
    if n % 4 == 0:
        collect_ores()


def check_struts():
    north_strut = (734, 301)
    south_strut = (704, 446)

    n = f.find_option('hammer.png', xy=north_strut, t=0.95, test=True, img_name='north_strut.png')
    print('North strut is broken') if n is not None else print('North strut is not broken')

    s = f.find_option('hammer.png', xy=south_strut, t=0.95, test=True, img_name='south_strut.png')
    print('South strut is broken') if s is not None else print('South strut not is broken')

    # t = f.find_option('hammer.png', xy=(1000, 1000), t=0.95, test=True, img_name='test.png')
    # print('test strut broken') if t is not None else print('test strut not broken')
    if n is not None or s is not None:
        print('Struts are broken')
        return True

    else:
        print('No struts are broken')
        return False


def check_strut_from_upper():
    n = f.find_option('hammer.png', xy=(550, 814), t=0.95, test=True, img_name='north_strut.png')
    print('North strut is broken') if n is not None else print('North strut is not broken')
    if n is not None:
        return True
    pag.move(f.r(-100, 100), f.r(-150, -250))
    time.sleep(f.r(8, 10))
    n1 = f.find_option('hammer.png', xy=(550,814), t=0.95, test=True, img_name='north_strut.png')
    print('North strut is broken') if n is not None else print('North strut is not broken')
    pag.move(f.r(-100, 100), f.r(-150, -250))
    if n1 is not None:
        print('Struts are broken')
        return True

    else:
        print('No struts are broken')
        return False


def repair_struts():
    pag.moveTo(1 + f.r(100, 200), 1 + f.r(100, 200), f.r())
    time.sleep(f.r(0.10, 0.20))
    f.move_click(680, 456)
    time.sleep(f.r(6, 7))
    # moved into strut fix position

    s = f.find_option('hammer.png', xy=(986, 527), t=0.95)
    if s is not None:
        s_strut = 'broken'
        f.move_click(*s)
        pag.move(f.r(-100, 100), f.r(-150, -250), f.r())
        while s_strut == 'broken':
            # print('Repairing south strut')
            time.sleep(f.r(3, 4))
            s_strut = f.find_option('hammer.png', xy=(986, 527), t=0.95)
            pag.move(f.r(-100, 100), f.r(-150, -250), f.r())
            if s_strut is not None:
                s_strut = 'broken'

    time.sleep(f.r(6, 7))
    f.move_click(945, 373)
    time.sleep(f.r(4, 5))
    # moved into strut fix position

    n = f.find_option('hammer.png', xy=(986, 527), t=0.95)
    if n is not None:
        n_strut = 'broken'
        f.move_click(*n)
        pag.move(f.r(-100, 100), f.r(-150, -250), f.r())
        while n_strut == 'broken':
            # print('Repairing south strut')
            time.sleep(f.r(3, 4))
            n_strut = f.find_option('hammer.png', xy=(986, 527), t=0.95)
            pag.move(f.r(-100, 100), f.r(-150, -250), f.r())
            if n_strut is not None:
                n_strut = 'broken'

    # return to strut check tile
    f.move_click(1300, 865)
    time.sleep(f.r(8, 9))


def bank_ores():
    f.play_actions('bank_ores.json', project_dir)
    time.sleep(f.r(4, 5))


def collect_ores():
    f.move_click(980, 629)  # Climb down ladder
    time.sleep(f.r(6, 7))
    f.move_click(731, 1010)  # Walk down
    time.sleep(f.r(8, 9))


def main(setup=True):
    f.initialize_pag()
    start_time = time.time()  # Start timer for script
    # f.countdown(1)
    if setup:
        set_up()
        pag.press('f2')

    for n in range(1, 45):  # Number of inventories to do
        full = check_inv()
        while full is False:
            mine()
            check_if_mining()
            full = check_inv()
        deposit_in_hopper(n)
        if n % 4 == 0:
            fix = check_struts()
            if fix:
                repair_struts()
            bank_ores()
        print(f'Inventory {n} done at {datetime.datetime.now()}')
        print()

    print(f'Script duration: {str(datetime.timedelta(seconds=time.time() - start_time))}')


if __name__ == "__main__":
    main(True)

