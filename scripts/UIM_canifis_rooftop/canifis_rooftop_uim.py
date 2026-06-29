import time
import functions as f
import os
import pyautogui as pag
import cv2 as cv
import numpy as np


project_dir = os.path.dirname(__file__)


def reset_position():
    f.move_right_click(1584, 867)
    walk_option = f.find("walk_here_option.png", (1500, 800, 200, 200))
    f.move_click(walk_option[0], walk_option[1])
    time.sleep(8 + f.r())
    f.move_right_click(1300, 600)
    walk_again = f.find("walk_here_option.png", (1200, 550, 300, 300))
    f.move_click(walk_again[0], walk_again[1])
    time.sleep(6.5 + f.r())


def do_first_half_lap():
    f.play_actions('canifis_first_half.json', project_dir)


def do_second_half_lap():
    f.play_actions('canifis_second_half.json', project_dir)
    f.move_right_click(884, 447)
    walk_option = f.find("walk_here_option.png", (784, 427, 250, 300))
    f.move_click(walk_option[0], walk_option[1])
    time.sleep(4 + f.r())


def do_lap():
    do_first_half_lap()
    pag.moveTo(100 + f.p(), 100 + f.p())
    if f.check_pixel_color_in_area((910, 515, 60, 10), (255, 0, 0)):
        print("Obstacle failed!")
        if f.check_pixel_color_in_area((988, 516, 10, 30), (0, 0, 255)):
            print("Standing on wrong tile. Moving left!")
            f.move_click(913, 533)
            time.sleep(2 + f.r())
        reset_position()
    else:
        do_second_half_lap()


def collection_first():
    f.play_actions('canifis_collection_first.json', project_dir)


def collection_second():
    f.play_actions('canifis_collection_second.json', project_dir)
    f.move_right_click(884, 447)
    walk_option = f.find("walk_here_option.png", (784, 427, 250, 300))
    f.move_click(walk_option[0], walk_option[1])
    time.sleep(4 + f.r())


def do_collection_lap():
    collection_first()
    pag.moveTo(100 + f.p(), 100 + f.p())
    if f.check_pixel_color_in_area((955, 515, 10, 10), (255, 0, 0)):
        print("Obstacle failed! Resetting position.")
        reset_position()
    else:
        collection_second()


def main():
    for n in range(1, 198):
        if n % 5 == 0:
            do_collection_lap()
        else:
            do_lap()
        print(f"Lap {n} done!")


if __name__ == "__main__":
    main()
