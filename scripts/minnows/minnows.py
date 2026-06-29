import time
import functions as f
import pyautogui as pag
import cv2 as cv
import numpy as np
import datetime

# script works at about 50% zoom

needle = cv.imread('minnow.png', cv.IMREAD_UNCHANGED)
character_location = (945, 540)
capture_region = (580, 380, 770, 370)


def find_spots(threshold=0.50):
    pag.screenshot('minnow_spots.png', region=capture_region)
    global needle
    haystack = cv.imread('minnow_spots.png', cv.IMREAD_UNCHANGED)
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


def visualize(t=0.50):
    results = create_rectangles(find_spots(t))
    draw_rectangles('minnow_spots.png', results)
    draw_markers('minnow_spots.png', results)


def find_click_spots(rectangles):
    global capture_region
    click_points = []
    for (x, y, w, h) in rectangles:
        center = ((x + capture_region[0] + int(w/2)), y + capture_region[1] + int(h/2))
        click_points.append(center)
    return click_points


def calculate_distance(click_points):
    global character_location
    distances = []
    for (x, y) in click_points:
        total_distance = abs(x - character_location[0]) + abs((y - character_location[1]) * 1.25)
        distances.append(total_distance)
    min_index = np.argmin(np.array(distances))
    # print(min_index)
    closest_point = click_points[min_index]
    closest_point = (closest_point[0] + f.p(7), closest_point[1] + f.p(7))
    print(closest_point)
    return closest_point


def start_fishing():
    for attempt in range(1, 11):
        results = find_spots(.45)
        results = create_rectangles(results)
        results = find_click_spots(results)
        if results:
            print(results)
            pag.moveTo(*calculate_distance(results), f.r(.05, 0.10))
            time.sleep(f.r(0.1, 0.2))
            pag.click()
            pag.moveTo(1000 + f.p(20), 900 + f.p(20), f.r(.25, .35))
            time.sleep(f.r(2, 2.5))
            return
        else:
            time.sleep(f.r(2, 3))
    raise RuntimeError(f"Failed to find fishing spot after 10 attempts")


def check_if_fishing(t=5):
    elapsed_time = 0
    start_time = time.time()
    print('Fishing ...', end='')
    while elapsed_time < 15:
        if pag.pixelMatchesColor(55, 55, (255, 0, 0), tolerance=t):
            print('Not fishing!')
            time.sleep(f.r(1, 1.25))
            break
        elif pag.pixelMatchesColor(50, 55, (0, 255, 0), tolerance=t):
            print('.', end='')
            elapsed_time = time.time() - start_time
            time.sleep(f.r(0.2, 0.3))
        else:
            print('No overlay found!')
            time.sleep(3)


def move_click(x, y, move_duration=f.r(), wait_duration=f.r()):
    pag.moveTo(x, y, move_duration)
    pag.click()
    time.sleep(wait_duration)


def set_up():
    f.shift_camera_direction('north', up=True)
    move_click(1800 + f.p(), 1020 + f.p())
    move_click(1830 + f.p(), 756 + f.p())
    move_click(1782, 855)
    move_click(1698 + f.p(), 856 + f.p())
    pag.press('f2')


def main(setup=False):
    start_time = time.time()
    print(f'Starting script at {datetime.datetime.now()}')
    f.countdown()
    f.initialize_pag()
    if setup:
        set_up()
    loops = 0
    while loops < 1600:
        start_fishing()
        check_if_fishing()
        loops += 1
    print(f'Script duration: {str(datetime.timedelta(seconds=time.time() - start_time))}')


if __name__ == "__main__":
    main(True)
# visualize()

# set_up()
