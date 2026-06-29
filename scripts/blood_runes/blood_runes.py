import functions as f
import pyautogui as pag
import time
import datetime
import world_hopper as wh


def setup():
    f.shift_camera_direction('north', up=True)
    pag.moveTo(1040 + f.p(0, 100), 500 + f.p(0, 100), f.r(0, 1))
    pag.scroll(-10000)


def chisel():
    f.move_click(1705, 766)
    f.move_click(1706, 802)
    time.sleep(f.r(65, 70))


def check_if_mining(t=5):
    elapsed_time = 0
    start_time = time.time()
    # print('Mining ...', end='')
    while elapsed_time < 120:
        if f.check_pixel_color_in_area((50, 50, 6, 6), (255, 0, 0), tolerance=t):
            # print('Not mining!')
            break
        elif f.check_pixel_color_in_area((50, 50, 6, 6), (0, 255, 0), tolerance=t):
            # print('.', end='')
            elapsed_time = time.time() - start_time
            time.sleep(4 + f.r(1, 2))
        else:
            print('No overlay found!')
            time.sleep(10)
            break


def check_inv():
    if pag.pixelMatchesColor(1829, 981, (62, 53, 41), tolerance=5):
        # print('Inventory not full!')
        return False
    else:
        # print('Inventory full!')
        return True


def venerate_essence(first_trip=True):
    if check_position() == 'green':
        swap_position()
    f.move_click(675, 350, wait_duration=f.r(7.5, 8.5))
    f.move_click(1150, 230, wait_duration=f.r(7.0, 8.0))
    f.move_click(450, 600, wait_duration=f.r(6.7, 7.7))
    f.move_click(270, 340, wait_duration=f.r(11, 12))
    if first_trip is True:
        print('First inventory done. Returning to mine.')
        f.move_click(1680, 650, wait_duration=f.r(7.0, 7.6))
        f.move_click(1335, 700, wait_duration=f.r(5.5, 6.5))
        f.move_click(1420, 500, wait_duration=f.r(8.5, 9.5))
        f.move_click(620, 955, wait_duration=f.r(5.88, 6.34))
        f.move_click(1245, 740, wait_duration=f.r(8.5, 9.5))
        chisel()
    else:
        print('Second inventory done. Continuing to altar.')
        f.move_click(200, 565, wait_duration=f.r(9.4, 10.4))
        f.move_click(177, 664, wait_duration=f.r(8.7, 9.7))
        f.move_click(177, 844, wait_duration=f.r(8.8, 9.6))
        f.move_click(1620, 865, wait_duration=f.r(7, 7.7))
        f.move_click(1840, 595, wait_duration=f.r(10, 11))
        f.move_click(1780, 665, wait_duration=f.r(8.6, 9.4))
        f.move_click(1250, 970, wait_duration=f.r(7, 8.0))
        f.move_click(1030, 1000, wait_duration=f.r(5.7, 6.7))
        f.move_click(330, 575, wait_duration=f.r(10, 11))  # Bind altar
        chisel()
        f.move_click(870, 480, wait_duration=f.r(4, 4.5))  # Bind altar 2nd time
        f.move_click(1275, 207, wait_duration=f.r(10.5, 11.5))
        f.move_click(1201, 267, wait_duration=f.r(9.5, 10.5))
        f.move_click(1240, 520, wait_duration=f.r(7.0, 8.0))  # Return to altar


def check_essence(position='red'):
    if position == 'red':
        north_essence = (1000, 450)
        south_essence = (1000, 850)
        order = [north_essence, south_essence]
    elif position == 'green':
        north_essence = (1000, 300)
        south_essence = (1010, 600)
        order = [south_essence, north_essence]
    c, far = False, False

    if f.find_option('chip.png', order[0], search_window=(150, 25, 300, 150), test=False):
        pag.move(f.p(-50, 50), -f.p(100, 200), f.r(0.2, 0.3))
        # print('Closest essence available!')
        c = True
    elif f.find_option('chip.png', order[1], search_window=(150, 25, 300, 150), test=False):
        pag.move(f.p(-50, 50), -f.p(100, 200), f.r(0.2, 0.3))
        # print('Other essence available!')
        far = True
    # print(n, s)
    return c, far


def check_position():
    attempt = 0
    pag.move(-f.r(300, 400), -f.r(300, 400), f.r())
    while attempt != 2:
        if f.check_pixel_color_in_area((954, 544, 10, 10), (255, 0, 0), tolerance=5):
            # print('On red tile.')
            return 'red'
        if f.check_pixel_color_in_area((954, 544, 10, 10), (0, 255, 0), tolerance=5):
            # print('On green tile.')
            return 'green'
        attempt += 1
        time.sleep(5)
    print('Unknown location')
    raise ValueError('Unknown location!')


def swap_position():
    position = check_position()
    if position == 'red':
        f.move_click(945, 738, wait_duration=f.r(5, 6))
    if position == 'green':
        f.move_click(945, 377, wait_duration=f.r(5, 6))


def mine_essence():
    position = check_position()
    c, far = check_essence(position)

    if position == 'red':
        if c is True:
            f.move_click(1000, 430)
            # print('Mining north side.')
        elif far is True:
            swap_position()
        else:
            time.sleep(f.r(5, 10))

    if position == 'green':
        if c is True:
            f.move_click(1000, 600)
            # print('Mining south side.')
        elif far is True:
            swap_position()
        else:
            time.sleep(f.r(5, 10))

    if position == 'end_script':
        raise ValueError('Unknown location!')


def mine_inv():
    full = check_inv()
    while full is False:
        mine_essence()
        check_if_mining()
        full = check_inv()


def main(set_up=True, fresh_start=True, time_cap=10):
    f.countdown(1)
    start_time = time.time()
    print(f'Script starting at: {datetime.datetime.now()}')
    if set_up:
        setup()

    for n in range(1, 100):
        if fresh_start and n == 1:
            mine_inv()
            venerate_essence()
        else:
            mine_inv()
            venerate_essence()
        mine_inv()
        venerate_essence(first_trip=False)

        print(f'Trip {n} done at {datetime.datetime.now()}')
        if time.time() - start_time > (time_cap * 3600):
            print(f'Time cap of {time_cap} hours reached')
            break

        if n % 15 == 0:
            pag.press('space')
            time.sleep(2)
            pag.press('space')
            wh.hop_world()
            pag.press('f2')

    print(f'Script ending at: {datetime.datetime.now()}')
    print(f'Script duration: {str(datetime.timedelta(seconds=time.time() - start_time))}')


if __name__ == "__main__":
    main(set_up=True, fresh_start=True, time_cap=11)
