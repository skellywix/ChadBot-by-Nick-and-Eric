import time
import functions as f
import pyautogui as pag
import os
import cv2 as cv
import numpy as np

mark_counter = 0


def set_up():
    f.shift_camera_direction('south')
    pag.moveTo(1040 + f.p(0, 100), 500 + f.p(0, 100), f.r(0, 1))
    pag.scroll(-10000)


def wait_for(image, c=0.98):
    script_dir = os.path.dirname(__file__)
    img = os.path.join(script_dir, image)
    while True:
        try:
            pag.locateOnScreen(img, confidence=c)
            print(f' now!')
            break
        except pag.ImageNotFoundException:
            print('.', end='')
            time.sleep(0.25)


def check_for_mark(x, c=0.60):
    global mark_counter
    if x == '1':
        try:
            script_dir = os.path.dirname(__file__)
            img = os.path.join(script_dir, 'mark_one.png')
            pag.locateOnScreen(img, confidence=c)
            mark_counter += 1
            print(f'Mark {mark_counter} found!')
            return True
        except pag.ImageNotFoundException:
            return False

    if x == '2':
        mrk1 = pag.pixelMatchesColor(897, 511, (243, 0, 0), tolerance=25)
        mrk2 = pag.pixelMatchesColor(929, 484, (255, 0, 0), tolerance=25)
        if mrk1 or mrk2:
            mark_counter += 1
            print(f'Mark {mark_counter} found!')
            return True
        else:
            return False

    if x == '3':
        mrk1 = pag.pixelMatchesColor(864, 468, (255, 0, 0), tolerance=25)
        mrk2 = pag.pixelMatchesColor(898, 444, (246, 0, 0), tolerance=25)
        if mrk1 or mrk2:
            mark_counter += 1
            print(f'Mark {mark_counter} found!')
            return True
        else:
            return False


def complete_lap():
    f.move_click(940, 520)
    time.sleep(3)
    if check_for_mark('1'):
        f.move_click(1008, 498)
        time.sleep(2 + f.r(0.25, 1))
        f.move_click(973, 397)
        time.sleep(4.5 + f.r(0, 1))
    else:
        f.move_click(1030 + f.p(0, 15), 360 + f.p(0, 15))
        time.sleep(5 + f.r(0, 1))
    f.move_click(912, 288)
    time.sleep(f.r(8.5, 9.5))

    if check_for_mark('2'):
        f.move_click(913, 476)
        time.sleep(2 + f.r(0.25, 1))
        f.move_click(911, 563)
        time.sleep(3 + f.r(0.25, 1))
        f.move_click(893 + f.p(0, 30), 643 + f.p(0, 15))
        time.sleep(11 + f.r(0.25, 1))
    else:
        f.move_click(829 + f.p(0, 30), 616 + f.p(0, 15))
        time.sleep(11 + f.r(0.25, 1))

    if check_for_mark('3', .85):
        f.move_click(883, 439)
        time.sleep(3 + f.r(0, 1))
        f.move_click(912, 560)
        time.sleep(2 + f.r(0, 1))
        f.move_click(896, 646)
        time.sleep(4 + f.r(0, 1))
    else:
        f.move_click(796 + f.p(0, 15), 581 + f.p(0, 15))
        time.sleep(4.5 + f.r(0.25, 1))
    f.move_click(799, 737)
    time.sleep(f.r(10, 11))
    f.move_click(988 + f.p(0, 15), 730 + f.p(0, 15))
    time.sleep(f.r(5.9, 7))
    f.move_click(1752, 580)
    time.sleep(f.r(10.30, 11.5))


def main():
    f.countdown()
    f.initialize_pag()
    for n in range(1, 225):
        complete_lap()
        print(f'Lap {n} done!')


if __name__ == "__main__":
    main()

# p = pag.pixel(864, 468)
# print(p)


