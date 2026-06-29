import time
import functions as f
import pyautogui as pag
import os
import cv2 as cv
import numpy as np


def bloom():
    f.move_click(1826, 767)
    time.sleep(2 + f.r())
    f.move_click(1826, 767)
    time.sleep(0.25)


def move_collect(a, b, c, d):
    pag.keyDown('shiftleft')
    f.move_click(a, b, f.r(0.05, 0.15))
    pag.keyUp('shiftleft')
    time.sleep(0.9 + f.r(0.05, 0.10))
    f.move_click(c, d, f.r(0.05, 0.15))
    time.sleep(0.9 + f.r(0.05, 0.10))


def collect_shrooms():
    for n in range(1, 5):
        bloom()
        move_collect(975, 536, 941, 533)
        move_collect(944, 565, 941, 533)
        move_collect(878, 533, 941, 533)
        move_collect(943, 477, 941, 533)
        f.move_click(977, 564)
        time.sleep(1 + f.r())


def teleport(location):
    if location == 'Ver_Sinzhaza':
        f.move_click(1750, 766)
        time.sleep(3 + f.r())
        f.move_click(1154, 126)
        time.sleep(15 + f.r())
        f.move_click(1142, 597)
        time.sleep(5 + f.r())

    if location == 'crafting_guild':
        f.move_click(1704, 767)
        time.sleep(3 + f.r())

    if location == 'house':
        pag.press('f4')
        time.sleep(f.r())
        f.move_click(1715, 825)
        pag.press('f2')
        time.sleep(3 + f.r())
        f.move_click(850, 757)
        time.sleep(3 + f.r())


def bank():
    teleport('crafting_guild')
    f.move_click(1130, 737)
    time.sleep(4)
    f.move_click(1703, 802)
    time.sleep(f.r())
    pag.press('esc')
    time.sleep(f.r())


def main():
    f.countdown()
    f.initialize_pag()
    for n in range(1, 65):
        teleport('house')
        teleport('Ver_Sinzhaza')
        collect_shrooms()
        bank()
        print(f'Loop {n} done!')


if __name__ == "__main__":
    main()
