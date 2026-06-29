import time
import functions as f
import os
import random
import pyautogui as pag
import cv2 as cv
import numpy as np


project_dir = os.path.dirname(__file__)


def main():
    for n in range(1, 500):
        f.play_actions('cannonballs.json', project_dir)
        time.sleep(f.r(1, 2))
        print(f'Loop {n} done!')


if __name__ == "__main__":
    main()

# time.sleep(3)
# pag.keyDown('up', 5)
