import pyautogui as pag
import functions as f
import cv2 as cv
import sys
import numpy as np
import digit_extractor as de
from collections import deque
import json
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
EXTRACTOR_DIR = SCRIPT_DIR / "scripts" / "number_extraction"
VISITED_JSON = EXTRACTOR_DIR / "travel_log.json"
HIGH_LEVEL_WORLD_IMAGE = EXTRACTOR_DIR / "2350_total_world.png"

sys.path.append(str(EXTRACTOR_DIR.resolve()))


def world_tab(command):
    pag.moveTo(1350 + f.p(), 350 + f.p(), f.r())
    open_color = (220, 138, 0)
    color_location = (1890, 137)
    location = (1904, 139)
    pixel_match = pag.pixelMatchesColor(*color_location, open_color, tolerance=5)

    if command == 'open' and pixel_match:
        pass
        # print('World tab is already open.')

    if command == 'close' and pixel_match:
        # print('Closing world tab.')
        f.move_click(*location)

    if command == 'close' and not pixel_match:
        pass
        # print('World tab is already closed.')

    if command == 'open' and not pixel_match:
        # print('Opening world tab.')
        f.move_click(*location)


def scroll_world_tab(direction='down', x=600):
    # x=60 is about one world
    world_tab('open')
    pag.moveTo(1350 + f.p(5, 15), 350 + f.p(10, 20), f.r())
    bottom = pag.pixel(1885, 1033) == (77, 77, 77)
    pag.moveTo(1800 + f.p(0, 50), 300 + f.p(0, 50), f.r())
    if direction == 'down':
        if bottom:
            print('At the bottom of the list, scrolling back to the top.')
            pag.scroll(100000)
        pag.scroll(-x)
    if direction == 'up':
        pag.scroll(x)
    if direction == 'top':
        pag.scroll(100000)


def load_travel_log(maxlen=15, clean=False):
    if not VISITED_JSON.exists():
        VISITED_JSON.parent.mkdir(parents=True, exist_ok=True)
        VISITED_JSON.write_text('{"visited": []}', encoding='utf-8')
    with VISITED_JSON.open("r", encoding='utf-8') as f:
        data = json.load(f)
    travel_log = deque(data["visited"], maxlen=maxlen)
    if clean:
        travel_log = clean_old_visits(travel_log)
    return travel_log


def clean_old_visits(travel_log, max_age=86400):  # 24 hours
    cutoff = time.time() - max_age
    return deque(
        [entry for entry in travel_log if entry["timestamp"] > cutoff],
        maxlen=travel_log.maxlen)


def record_visit(travel_log, world_num):
    # Add visit entry
    travel_log.append({"world": world_num,
                       "timestamp": time.time()})

    # Save updated list to JSON
    with VISITED_JSON.open("w", encoding='utf-8') as f:
        json.dump({"visited": list(travel_log)}, f, indent=4)


def visited_recently(travel_log, world_num, cooldown=1200):
    """Return True if the world was visited within the cooldown window."""
    now = time.time()

    for entry in travel_log:
        if entry["world"] == world_num:
            if now - entry["timestamp"] < cooldown:
                return True  # too recent

    return False  # safe to visit


def create_world_list(length):
    #  Creates a list of xy coordinates, each marking the centerpoint location of each world in the world tab
    world_tab('open')
    pag.moveTo(1550 + f.p(), 350 + f.p(), f.r())

    x = 1852
    h = length - 50
    screenshot = pag.screenshot(region=(x, 50, 1, h))  # width=1
    col = np.array(screenshot)[:, :, :3]               # shape (h,1,3)
    col = col.reshape(h, 3)

    # Compare each pixel row to detect changes
    diffs = np.any(col[1:] != col[:-1], axis=1)
    change_indices = np.where(diffs)[0] + 1 + 50

    adjusted_worlds = []
    if len(change_indices) == 0:
        return adjusted_worlds
    last_y = change_indices[0]

    for y in change_indices[1:]:
        midpoint = int((last_y + y) / 2)
        adjusted_worlds.append((x, midpoint))
        last_y = y

    return adjusted_worlds


def check_world_number(world, debug=False):
    x = 1674
    xx = 28
    world_cords = (x, world[1] - 6)
    screenshot = f.take_screenshot((*world_cords, xx, 10), save_img=debug, img_name='wrld_num.png')
    w_num = de.read_digits(screenshot, number_type='w')
    return w_num


def check_world_population(world, debug=False):
    x = 1711
    xx = 28
    world_cords = (x, world[1] - 5)
    screenshot = f.take_screenshot((*world_cords, xx, 8), save_img=debug, img_name='world_pop.png')
    population = de.read_digits(screenshot, debug=debug)
    return population


def check_world_type(world):
    x = 1674
    p2p_color = (210, 193, 53)
    current_world_color = (66, 227, 17)
    if f.check_pixel_color_in_area((x, world[1], 20, 1), current_world_color):
        world_type = 'current'
    elif f.check_pixel_color_in_area((x, world[1], 20, 1), p2p_color):
        world_type = 'p2p'
    else:
        world_type = 'f2p'
    return world_type


def check_activity(world, debug=False):
    x = 1753
    y = world[1]
    screenshot = f.take_screenshot(area=(x, y-5, 24, 8))
    screenshot = de.preprocess(screenshot)

    png = cv.imread(str(HIGH_LEVEL_WORLD_IMAGE))
    if png is None:
        raise FileNotFoundError(f"Image not found or unreadable: {HIGH_LEVEL_WORLD_IMAGE}")
    png = de.preprocess(png)

    if np.array_equal(png, screenshot):
        # print('High lvl world')
        return 'bad world'

    allowed_colors = np.array([(255, 255, 255), (44, 44, 44), (40, 40, 40)])
    scr = pag.screenshot(region=(x, y-5, 15, 11))
    if debug:
        scr.save('activity_screenshot.png')
    scr = np.array(scr)
    matches_any = np.any(
        np.all(scr[:, :, None] == allowed_colors, axis=3), axis=2)

    illegal_mask = ~matches_any  # shape (8,15), True where illegal
    # True if any illegal pixel exists
    has_illegal = np.any(illegal_mask)
    return "bad world" if has_illegal else "good world"


def check_ping(world, debug=False):
    x = 1858
    xx = 20
    world_cords = (x, world[1] - 5)
    screenshot = f.take_screenshot((*world_cords, xx, 8), save_img=debug, img_name='ping.png')
    ping = de.read_digits(screenshot)
    return ping


def display_world_info(worlds, debug=False):
    if type(worlds) != list:
        worlds = [worlds]
    for w in worlds:
        if check_world_type(w) == 'current':
            continue
        world_num = check_world_number(w, debug)
        print(f'World number {world_num}')
        pop = check_world_population(w, debug)
        print(f'World population: {pop}')
        world_type = check_world_type(w)
        print(f'World type: {world_type}')
        world_activity = check_activity(w, debug)
        print(f'World activity: {world_activity}')
        world_ping = check_ping(w, debug)
        print(f'World ping: {world_ping}')
        print()


# display_world_info(create_world_list(200), debug=False)


def extract_world_data(world, debug=False):
    w_type = check_world_type(world)
    if w_type == 'current':
        return 69, 1000000, 'current', 'atrocious', 9001
    w_num = check_world_number(world, debug)
    pop = check_world_population(world, debug)
    w_act = check_activity(world, debug)
    w_ping = check_ping(world, debug)
    return w_num, pop, w_type, w_act, w_ping


def suitable_world(world, travel_log):
    w_num, pop, w_type, w_act, w_ping = extract_world_data(world)

    # 1. Only accept p2p worlds
    if w_type is None or w_type != 'p2p':
        return False
    # 2. Only accept "good world" activity
    if w_act is None or w_act != 'good world':
        return False
    # 3. Population filter
    if pop is None or pop > 1900:
        return False
    # 4. Ping filter
    if w_ping is None or w_ping > 125:
        return False
    # 5. Travel log cooldown (20 min)
    if visited_recently(travel_log, w_num, cooldown=1200):
        return False

    return True


# wl = gen_world_list(500)
# display_world_info(wl)


def hop_world(hop_counter=0):
    # Loads travel log, open world tab and scrolls to top, starts timer and sets chosen world to none
    travel_log = load_travel_log(clean=True)
    print('Opening travel log!')
    if hop_counter < 1:
        scroll_world_tab('top')
    start_time = time.time()
    elapsed_time = 0
    chosen_world = None

    print('Choosing world ...', end='')
    while chosen_world is None:

        elapsed_time = time.time() - start_time
        if elapsed_time > 600:
            print("Timeout: no suitable world found.")
            return None

        world_list = create_world_list(600)
        for w in world_list:
            print('.', end='')
            if suitable_world(w, travel_log):
                print()
                print()
                w_num, *_ = extract_world_data(w)
                display_world_info(w)
                record_visit(travel_log, w_num)
                f.move_click(*w, double_click=True)
                chosen_world = w_num

                hop_start_time = time.time()
                hop_timer = 0
                while True:
                    hopped = check_world_type(w)
                    if hopped == 'current':
                        break
                    hop_timer = time.time() - hop_start_time
                    if hop_timer > 30:
                        break

                print(f"Hopped to world {w_num}")
                time.sleep(f.r(1, 2))
                world_tab('close')
                hop_counter += 1
                return hop_counter

        scroll_world_tab('down', 1000)
