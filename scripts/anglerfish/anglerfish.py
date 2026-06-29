import time
import functions as f
import pyautogui as pag
import cv2 as cv
import numpy as np
import datetime
from pathlib import Path

# functions are designed to work at 25% zoom
SCRIPT_DIR = Path(__file__).resolve().parent

needle = cv.imread('fish2.png', cv.IMREAD_UNCHANGED)
reset_tile = cv.imread('reset_tile.png', cv.IMREAD_UNCHANGED)
character_location = (945, 540)
fish_caught = 0


def move_click(x, y, move_duration=f.r(), wait_duration=f.r()):
    pag.moveTo(x, y, move_duration)
    pag.click()
    time.sleep(wait_duration)


def set_up():
    f.shift_camera_direction('north', up=True)
    move_click(1800 + f.p(), 1020 + f.p())
    move_click(1830 + f.p(), 756 + f.p())
    move_click(1757, 855)
    move_click(1698 + f.p(), 856 + f.p())
    pag.press('f2')


def find_spots(threshold=0.60):
    pag.screenshot('fish_spots.png', region=(0, 0, 1650, 1000))
    global needle
    haystack = cv.imread('fish_spots.png', cv.IMREAD_UNCHANGED)
    result = cv.matchTemplate(haystack, needle, cv.TM_CCOEFF_NORMED)
    locations = np.where(result > threshold)
    locations = list(zip(*locations[::-1]))
    return locations


def create_rectangles(coordinates, group_threshold=1, eps=0.50):
    global needle
    rectangles = []
    for loc in coordinates:
        rect = [int(loc[0]), int(loc[1]), needle.shape[1], needle.shape[0]]
        rectangles.append(rect)
        rectangles.append(rect)
    rectangles, weights = cv.groupRectangles(rectangles, group_threshold, eps)
    return rectangles


def draw_rectangles(haystack, locations):
    global needle
    image1 = cv.imread(haystack, cv.IMREAD_UNCHANGED)
    if len(locations):
        line_color = (0, 0, 255)
        line_type = cv.LINE_4

        for (x, y, w, h) in locations:
            top_left = (x, y)
            bottom_right = (x + w, y + h)
            cv.rectangle(image1, top_left, bottom_right, line_color, line_type)
        cv.imshow('Matches', image1)
        cv.waitKey()
    else:
        print('No matches :(')


def draw_markers(haystack, rectangles):
    img = cv.imread(haystack, cv.IMREAD_UNCHANGED)
    marker_color = (255, 0, 255)
    marker_type = cv.MARKER_CROSS
    for (x, y, w, h) in rectangles:
        center = ((x + int(w/2)), y + int(h/2))
        cv.drawMarker(img, center, marker_color, marker_type)
    cv.imshow('Matches', img)
    cv.waitKey()


def find_click_spots(rectangles):
    click_points = []
    for (x, y, w, h) in rectangles:
        center = ((x + int(w/2)), y + int(h/2))
        click_points.append(center)
    return click_points


def calculate_distance(click_points):
    global character_location
    distances = []
    for (x, y) in click_points:
        total_distance = abs(x - character_location[0]) + abs(y - character_location[1])
        distances.append(total_distance)
    min_index = np.argmin(np.array(distances))
    # print(min_index)
    closest_point = click_points[min_index]
    return closest_point


def bank_fish(filename):
    global reset_tile
    global fish_caught
    pag.screenshot('fish_spots.png', region=(0, 0, 1650, 1000))
    haystack = cv.imread('fish_spots.png', cv.IMREAD_UNCHANGED)
    result = cv.matchTemplate(haystack, reset_tile, cv.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv.minMaxLoc(result)
    tile_w = int(reset_tile.shape[0] / 2)
    tile_h = int(reset_tile.shape[1] / 2)
    esl = (max_loc[0] + tile_w, max_loc[1] + tile_h)
    # print(esl)
    pag.moveTo(esl[0], esl[1], f.r())
    time.sleep(f.r(0, 0.10))
    pag.click()
    time.sleep(5 + f.r(1, 2))
    f.play_actions(f'{filename}.json', new_path=SCRIPT_DIR)
    time.sleep(6 + f.r(1, 2))
    fish_caught += 45


def check_if_fishing(t=5):
    elapsed_time = 0
    start_time = time.time()
    print('Fishing ...', end='')
    while elapsed_time < 120:
        if f.check_pixel_color_in_area((55, 55, 5, 5), (255, 0, 0), tolerance=t):
            print('Not fishing!')
            break
        elif f.check_pixel_color_in_area((55, 55, 5, 5), (0, 255, 0), tolerance=t):
            print('.', end='')
            elapsed_time = time.time() - start_time
            time.sleep(4 + f.r(1, 2))
        else:
            print('No overlay found!')
            time.sleep(10)
            break


def check_inv():
    if pag.pixelMatchesColor(1829, 981, (62, 53, 41), tolerance=5):
        print('Inventory not full!')
        return False
    else:
        print('Inventory full!')
        return True


def start_fishing():
    results = find_spots(.50)
    results = create_rectangles(results)
    results = find_click_spots(results)
    pag.moveTo(*calculate_distance(results), f.r())
    time.sleep(f.r(0.1, 0.2))
    pag.click()
    pag.move(f.p(100), f.p(-200, -100), f.r())
    time.sleep(5 + f.r(1, 2))


# results = create_rectangles(find_spots())
# draw_rectangles('fish_spots.png', results)
# draw_markers('fish_spots.png', results)
# check_if_fishing(55, 55, (255, 0, 0))
# check_inv()
# bank_fish()


def main(setup=False):
    f.countdown(1)
    f.initialize_pag()
    start_time = time.time()
    print(f'Script starting at: {datetime.datetime.now()}')
    if setup:
        set_up()
    for n in range(1, 17):
        full = check_inv()
        while full is False:
            start_fishing()
            check_if_fishing()
            full = check_inv()
        if full:
            bank_fish('bank_fish')
        print(f'Inventory {n} done at {datetime.datetime.now()}')
    print(f'Script duration: {str(datetime.timedelta(seconds=time.time() - start_time))}')
    print(f'Total fish caught: {fish_caught}')


# bank_fish('bank_fish')
if __name__ == "__main__":
    main(True)

# bank_fish('bank_fish')
