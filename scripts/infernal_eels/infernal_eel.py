import time
import functions as f
import pyautogui as pag
import cv2 as cv
import numpy as np

# functions are designed to work at 25% zoom

needle = cv.imread('infernal_eel.png', cv.IMREAD_UNCHANGED)
character_location = (945, 540)


def set_up():
    f.shift_camera_direction('north', up=True)
    f.move_click(1800 + f.p(), 1020 + f.p())
    f.move_click(1830 + f.p(), 756 + f.p())
    pag.moveTo(1736, 855)
    pag.click(1763, 855)
    f.move_click(1698 + f.p(), 856 + f.p())
    pag.press('f2')


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


def find_spots(threshold=0.50):
    global needle
    attempt_count = 0
    while True:
        pag.screenshot('infernal_eel_spots.png', region=(0, 0, 1650, 1000))
        haystack = cv.imread('infernal_eel_spots.png', cv.IMREAD_UNCHANGED)
        result = cv.matchTemplate(haystack, needle, cv.TM_CCOEFF_NORMED)
        locations = np.where(result > threshold)
        locations = list(zip(*locations[::-1]))
        if locations:
            return locations
        attempt_count += 1
        if attempt_count > 10:
            locations = 'end_script'
            return locations
        print(f'Failed to locate fishing spot {attempt_count} time(s). Waiting 15 seconds to retry.')
        time.sleep(15)


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


def start_fishing(x=0.35):
    results = find_spots(x)
    if results == 'end_script':
        return 'end_script'
    results = create_rectangles(results)
    results = find_click_spots(results)
    pag.moveTo(*calculate_distance(results), f.r())
    time.sleep(f.r(0.1, 0.2))
    pag.click()
    time.sleep(5 + f.r(1, 2))
    pag.move(f.p(100, 300), -f.p(100, 300), f.r())


def check_if_fishing(t=5):
    elapsed_time = 0
    start_time = time.time()
    print('Fishing ...', end='')
    while elapsed_time < 120:
        if pag.pixelMatchesColor(55, 55, (255, 0, 0), tolerance=t):
            print('Not fishing!')
            break
        elif pag.pixelMatchesColor(50, 55, (0, 255, 0), tolerance=t):
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


def hammer_eels():
    f.move_click(1827, 766)
    eel = f.find('eel_inventory.png', (1650, 701, 250, 300))
    f.move_click(*eel)
    time.sleep(41 + f.r(1, 3))


def main(setup=False):
    f.countdown()
    f.initialize_pag()
    if setup:
        set_up()
    for n in range(1, 56):
        full = check_inv()
        while full is False:
            status_check = start_fishing(.45)
            if status_check == 'end_script':
                break
            check_if_fishing()
            full = check_inv()
        if full:
            hammer_eels()
        if status_check == 'end_script':
            print('Could not find fishing locations. Ending script.')
            break
        print(f'Loop {n} done.')
    print('Done!')


if __name__ == "__main__":
    main(True)
