import time
import functions as f
import pyautogui as pag
import os
import cv2 as cv
import numpy as np

project_dir = os.path.dirname(__file__)


def set_up():
    f.shift_camera_direction('north')
    pag.moveTo(1040 + f.p(0, 100), 500 + f.p(0, 100), f.r(0, 1))
    pag.scroll(-10000)


def start_course():
    f.move_right_click(1105, 501)
    climb = f.find('climb_option.png', (950, 450, 300, 300))
    f.move_click(climb[0], climb[1])
    time.sleep(5 + f.r())


def do_lap(collect=False):
    if not collect:
        f.play_actions('ardy_lap.json', project_dir)
        time.sleep(f.r(12, 15))
    else:
        f.play_actions('collect_ardy_lap.json', project_dir)
        time.sleep(f.r(12, 15))


def main(setup=True):
    f.countdown(2)
    f.initialize_pag()
    if setup:
        set_up()
    for n in range(1, 157):
        if n % 5 == 0:
            c = False
        else:
            c = True
        start_course()
        do_lap(c)
        print(f'Lap {n} done!')
        random_wait = f.p(1, 15)
        if random_wait == 12:
            sleep_time = f.p(20, 35)
            time.sleep(sleep_time)
            print(f'Taking a {sleep_time} second break.')


if __name__ == "__main__":
    main()
