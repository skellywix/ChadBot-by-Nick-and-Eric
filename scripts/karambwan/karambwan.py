import functions as f
import pyautogui as pag
import time
import datetime


def setup():
    f.shift_camera_direction('north', up=True)
    pag.moveTo(1040 + f.p(0, 100), 500 + f.p(0, 100), f.r(0, 1))
    pag.scroll(-10000)


def bank():
    f.move_click(1800, 722)
    tp = f.find_option('teleport.png', xy=(1725, 804))
    f.move_click(*tp, wait_duration=f.r(5, 6))
    pag.press('f2')
    f.move_click(1128, 737, wait_duration=f.r(5, 6))
    f.move_click(1746, 767, wait_duration=f.r(1, 2))
    f.move_click(1828, 983, wait_duration=f.r(1, 1.5))
    pag.press('esc')
    f.move_click(1704, 767, wait_duration=f.r(5, 6))
    f.move_click(965, 900, wait_duration=f.r(9, 10))
    f.move_click(915, 371, wait_duration=f.r(4, 5))


def check_if_fishing(t=5):
    elapsed_time = 0
    start_time = time.time()
    print('Fishing ...', end='')
    while elapsed_time < 120:
        if f.check_pixel_color_in_area((63, 90, 5, 5), (255, 0, 0), tolerance=t) or \
                f.check_pixel_color_in_area((63, 54, 5, 5), (255, 0, 0), tolerance=t):
            time.sleep(4 + f.r(1, 2))
            print('Not fishing!')
            break
        elif f.check_pixel_color_in_area((63, 90, 5, 5), (0, 255, 0), tolerance=t) or \
                f.check_pixel_color_in_area((63, 54, 5, 5), (0, 255, 0), tolerance=t):
            print('.', end='')
            elapsed_time = time.time() - start_time
            time.sleep(4 + f.r(1, 2))
        else:
            print('No overlay found!')
            time.sleep(10)
            break


def fish():
    f.move_click(944, 505)


def check_inv():
    if pag.pixelMatchesColor(1829, 981, (62, 53, 41), tolerance=5):
        print('Inventory not full!')
        return False
    else:
        print('Inventory full!')
        return True


def main(set_up=True):
    f.countdown(1)
    if set_up:
        setup()
    fish_caught = 0
    start_time = time.time()
    print(f'Script starting at: {datetime.datetime.now()}')
    for n in range(1, 22):
        full = check_inv()
        while full is False:
            check_if_fishing()
            full = check_inv()
            fish()
        if full:
            bank()
        fish_caught += 52
        print(f'Inventory {n} done at {datetime.datetime.now()}')
    print(f'Script duration: {str(datetime.timedelta(seconds=time.time() - start_time))}')
    print(f'Total fish caught: {fish_caught}')


if __name__ == "__main__":
    main()
