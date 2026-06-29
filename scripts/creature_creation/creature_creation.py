import time
import functions as f
import pyautogui as pag
import os
import cv2 as cv
import numpy as np


project_dir = os.path.dirname(__file__)


def teleport(location):
    if location == 'house':
        pag.press('f4')
        time.sleep(f.r())
        f.move_click(1715, 825)
        pag.press('f2')
        time.sleep(3 + f.r())
        f.move_click(850, 757)
        time.sleep(3 + f.r())
        f.move_click(1033, 678)
        time.sleep(6 + f.r())
    if location == 'crafting_guild':
        f.move_click(1704, 767)
        time.sleep(3 + f.r())


def kill_collect():
    f.move_click(879, 490)
    time.sleep(2)
    f.move_click(910, 700)
    time.sleep(5)
    f.move_click(1030, 378)
    time.sleep(4)
    f.move_click(975, 534)
    time.sleep(2)
    f.move_click(913, 533)
    time.sleep(2)
    pag.press('f1')
    f.move_click(1780, 917)
    time.sleep(15)
    f.move_click(1780, 917)
    pag.press('f2')
    time.sleep(0.5)
    f.move_right_click(944, 595)
    option = f.find('take_option.png')
    f.move_click(*option)
    time.sleep(3)
    f.move_click(912, 505)
    time.sleep(2)


def bank():
    teleport('crafting_guild')
    f.move_click(1130, 737)
    time.sleep(4)
    f.move_click(647, 717)
    time.sleep(f.r())
    f.move_click(696, 717)
    time.sleep(f.r())
    f.move_click(1830, 765)
    time.sleep(f.r())
    pag.press('esc')


# main()

def slaughter():
    print(f'Kills: ', end='')
    for n in range(1, 13):
        kill_collect()
        print(f'{n}', end='')
        if n != 12:
            print(', ', end='')
        else:
            print('.')


def main():
    f.countdown()
    f.initialize_pag()
    for n in range(1, 64):
        bank()
        teleport('house')
        f.play_actions('unicow.json', project_dir)
        slaughter()
        print(f'Trip {n} done!')


if __name__ == "__main__":
    main()
