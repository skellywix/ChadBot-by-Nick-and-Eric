import world_hopper as wh
import functions as f
import pyautogui as pag
import cv2 as cv
import os
import numpy as np
import time
import datetime


TEMPLATE_FOLDER = "inv_items"

ITEM_ACTIONS = {"archer_helm": "alch",
                "berserker_helm": "alch",
                "cotton_seed_1": "ignore",
                "cotton_seed_2": "ignore",
                "cotton_seed_3": "ignore",
                "cotton_seed_4": "ignore",
                "empty_slot": "ignore",
                "farseer_helm": "alch",
                "fremmy_helm": "alch",
                "fremmy_salvage": "ignore",
                "ironwood_seed": "ignore",
                "lobster": "drop",
                "logs": "drop",
                "mahogany_plank": "alch",
                "mithril": "drop",
                "monkfish": "drop",
                "rosewood_seed_1": "ignore",
                "rosewood_seed_2": "ignore",
                "smashed_mirror": "destroy",
                "salmon": "drop",
                "troll_head": "drop",
                "tuna": "drop",
                "unknown_item": 'ignore',
                "warrior_helm": "alch",
                "umbral_frag": "drop"}


def generate_item_dict_skeleton():
    print("ITEM_ACTIONS = {")
    for fname in os.listdir(TEMPLATE_FOLDER):
        if fname.endswith(".png"):
            item_name = fname[:-4]  # remove .png
            print(f'    "{item_name}": "",')
    print("}")


def set_up():
    wh.world_tab('close')
    f.shift_camera_direction('west')
    pag.moveTo(900, 500, f.r())
    pag.scroll(-10000)
    f.move_click(1802, 1020)
    f.move_click(1830, 756)
    pag.moveTo(1782, 855, f.r())
    time.sleep(f.r(0.2, 0.3))
    pag.click()


def wait(wait_duration=5, area=(880, 300, 6, 6), rgb=(255, 152, 31)):
    start_time = time.time()
    elapsed_time = 0
    wait_duration += f.r()
    while elapsed_time < wait_duration:
        elapsed_time = time.time() - start_time
        if f.check_pixel_color_in_area(area, rgb, tolerance=1):
            break


def create_inv(n=20):
    inventory = f.create_inv_grid()
    inventory = dict(list(inventory.items())[:n])
    return inventory


def load_templates():
    templates = []

    for fname in os.listdir(TEMPLATE_FOLDER):
        if fname.endswith(".png"):
            path = os.path.join(TEMPLATE_FOLDER, fname)
            img = cv.imread(path, cv.IMREAD_GRAYSCALE)
            templates.append(img)

    return templates


def is_duplicate(img, templates, threshold=0.95):
    img_gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

    for templ in templates:
        if templ.shape != img_gray.shape:
            continue

        # When screenshot == template size, matchTemplate returns a single value
        res = cv.matchTemplate(img_gray, templ, cv.TM_CCOEFF_NORMED)

        if res >= threshold:
            return True

    return False


def save_template(img):
    img_gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    filename = f"item_{int(time.time())}.png"
    cv.imwrite(os.path.join(TEMPLATE_FOLDER, filename), img_gray)
    print(f"[NEW TEMPLATE SAVED] {filename}")


# noinspection PyArgumentList
def generate_inventory_templates(inventory_slots):
    templates = load_templates()
    # print(inventory_slots)

    for idx, slot in enumerate(inventory_slots):
        # print(f"Scanning slot {idx + 1}...")
        x = inventory_slots[slot][0] - 7
        y = inventory_slots[slot][1] - 8

        # Capture slot using your screenshot function
        img = f.take_screenshot(area=(x, y, 20, 20))

        # ---- EMPTY SLOT DETECTION (NEW CODE) ----
        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        if np.std(gray) < 2 or (gray.max() - gray.min()) < 5:
            # print(" -> empty slot, skipping")
            continue
        # -----------------------------------------

        if is_duplicate(img, templates):
            # print(" -> duplicate, skipping")
            continue

        save_template(img)

        # Reload list so further comparisons include newly saved item
        templates = load_templates()


def load_item_templates(folder="inv_items"):
    items = {}
    for fname in os.listdir(folder):
        if fname.endswith(".png"):
            name = fname[:-4]  # remove .png extension
            img = cv.imread(os.path.join(folder, fname), cv.IMREAD_GRAYSCALE)
            items[name] = img
    return items


def identify_item(screenshot, templates, threshold=0.95):
    img_gray = cv.cvtColor(screenshot, cv.COLOR_BGR2GRAY)

    for name, templ in templates.items():
        if templ.shape != img_gray.shape:
            continue

        result = cv.matchTemplate(img_gray, templ, cv.TM_CCOEFF_NORMED)

        if result >= threshold:
            # 👇 extra logic here
            if name not in ITEM_ACTIONS:
                return "unknown_item"
            return name

    return "unknown_item"


def check_salvage():
    s1 = (746, 386)
    s2 = (1277, 888)
    if f.find_option('inspect.png', s1, search_window=(150, 25, 300, 150),
                     test=False, img_name='s1.png'):
        pag.move(f.p(-50, 50), -f.p(100, 200), f.r(0.2, 0.3))
        return True
    pag.move(f.p(10), -f.p(50, 100))
    if f.find_option('inspect.png', s2, search_window=(150, 25, 300, 150),
                     test=False, img_name='s2.png'):

        pag.move(f.p(-50, 50), -f.p(100, 200), f.r(0.2, 0.3))
        return True
    else:
        return False


def salvage():
    f.move_click(1118, 400)  # deploy hook
    while True:
        full = full_inventory()  # Check if inv is full and stop if it is
        if full:
            break
        if not check_salvage():  # Check if there is salvage and stop if there isn't
            break
        for n in range(1, 6):
            collected = extract_crystal('collect')
            if collected:
                f.move_click(1118, 400)  # redeploy hook
            if full_inventory():
                break
            time.sleep(f.r(4, 5))
        f.move_click(1118, 400)  # redeploy hook
    f.move_click(1051, 592)  # sort salvage
    sorting_wait()
    f.move_click(1747, 983)  # store seeds


# noinspection PyArgumentList
def scan_inventory(inventory_slots, templates):
    results = {}

    for slot_name, (cx, cy) in inventory_slots.items():
        x = cx - 7
        y = cy - 8

        # Capture slot screenshot
        img = f.take_screenshot(area=(x, y, 20, 20))

        # ---- EMPTY SLOT DETECTION (NEW CODE) ----
        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        if np.std(gray) < 2 or (gray.max() - gray.min()) < 5:
            results[slot_name] = "empty_slot"
            continue
        # -----------------------------------------

        # Identify actual item
        item_name = identify_item(img, templates)
        results[slot_name] = item_name

    return results


def full_inventory():

    temp = load_item_templates()
    inv = create_inv(20)

    items = scan_inventory(inv, temp)

    for slot, item_name in items.items():
        if item_name == "empty_slot":
            return False

    return True


def show_inv_scan(res):
    for number, r in enumerate(res):
        item = res[r]
        if (number + 1) % 4 != 0:
            print(f"{item:<20}", end="")
        else:
            print(f"{item:<20}")


def get_inventory_state(inv_slots, templates):
    global ITEM_ACTIONS
    items = scan_inventory(inv_slots, templates)
    state = {}

    for slot_name, item_name in items.items():
        cx, cy = inv_slots[slot_name]
        action = ITEM_ACTIONS[item_name]

        state[slot_name] = {
            "item": item_name,
            "action": action,
            "x": cx,
            "y": cy}

    return state


def group_inventory_actions(inv_state):
    groups = {
        "drop": [],
        "alch": [],
        "ignore": [],
        "destroy": [],
        "unknown": []
    }

    for slot, data in inv_state.items():
        action = data["action"]
        item   = data["item"]
        x      = data["x"]
        y      = data["y"]

        # Make a compact tuple for easy processing
        entry = (slot, item, x, y)

        # Ensure unexpected actions don’t break things
        groups.setdefault(action, [])

        groups[action].append(entry)

    return groups


def execute_grouped_actions(groups):
    # --- STEP 1: DROP EVERYTHING ---
    f.move_click(1769, 722, wait_duration=f.r(0.1, 0.2))
    pag.keyDown('shift')
    for slot, item, x, y in groups.get("drop", []):
        # print(f"Dropping {item} in {slot}")
        drop_items(x, y)
    pag.keyUp('shift')

    # --- STEP 2: ALCH EVERYTHING ---
    pag.press('f4')
    for slot, item, x, y in groups.get("alch", []):
        # print(f"Alching {item} in {slot}")
        if item == 'fremmy_helm':
            high_alch(x, y)
            pag.press('space')
            time.sleep(f.r(1, 2))
            pag.press('1')
            time.sleep(f.r(4, 5))
        else:
            high_alch(x, y)
    pag.press('f2')

    # --- STEP 3: DESTROY EVERYTHING  ---
    for slot, item, x, y in groups.get("destroy", []):
        print(x, y)
        f.move_right_click(x, y)
        f.move_click(x - 60, y + 58)
        time.sleep(f.r(2, 3))
        pag.press('1')

    # --- STEP 4: IGNORE EVERYTHING ELSE ---
    for slot, item, x, y in groups.get("none", []):
        print(f"Ignoring {item} in {slot}")

    for slot, item, x, y in groups.get("unknown", []):
        print(f"UNKNOWN ITEM in {slot}: {item} — review manually.")


def drop_items(x, y):
    f.move_click(x, y, wait_duration=f.r(0.01, 0.05), move_duration=f.r(0.02, 0.06))


def high_alch(x, y):
    f.move_click(1695, 878)
    time.sleep(f.r(0.40, 0.60))
    f.move_click(x, y)
    time.sleep(f.r(4, 5))


def sort_salvage():
    f.move_click(1158, 487)  # Open cargo
    wait(4)
    f.move_click(620, 384)  # Withdraw salvage
    pag.press('esc')  # Close cargo
    time.sleep(f.r(0.1, 0.3))
    f.move_click(1050, 591)  # Sort salvage
    sorting_wait()
    f.move_click(1745, 980, move_duration=f.r(0.2, 0.3), wait_duration=f.r(0.12, 0.24))  # Store seeds in seed box


def process_inv(n=19):
    inv = create_inv(n)
    generate_inventory_templates(inv)
    temp = load_item_templates()
    # inv_result = scan_inventory(inv, temp)
    # show_inv_scan(inv_result)
    abcd = get_inventory_state(inv, temp)
    for n in abcd:
        pass
        # print(n, abcd[n])
    g = group_inventory_actions(abcd)
    execute_grouped_actions(g)


def sorting_wait():
    start_time = time.time()
    templates = load_item_templates()

    # Initial wait before checking (your random delay)
    time.sleep(f.r(30, 35))

    while True:
        elapsed = time.time() - start_time
        if elapsed > 45:
            print("Timeout reached.")
            break

        salvage_inv = create_inv(20)
        inv_res = get_inventory_state(salvage_inv, templates)

        salvage_found = False  # reset each loop

        # Scan entire inventory for salvage
        for slot in inv_res:
            item = inv_res[slot]['item']
            # print(item)
            if item == 'fremmy_salvage':
                salvage_found = True
                break  # found salvage → no need to check other slots

        if salvage_found:
            # print("Salvage still present → waiting and rechecking...")
            time.sleep(0.5)
        else:
            # print("No salvage left → sorting complete.")
            break


def hop_for_salvage(hops):
    hop = check_salvage()  # if salvage is available will return as true
    start_time = time.time()
    elapsed = 0
    if not hop:  # if no salvage is found this gets executed
        while not check_salvage():
            hops = wh.hop_world(hops)
            elapsed = time.time() - start_time
            print(f'Time searching for world: {elapsed}')
            if elapsed > 300:
                hops = 'end_script'
                break
        f.move_click(1044, 527)  # moves to center spot yellow tile
        print('Available salvage found')
        pag.press('f2')
        extract_crystal('activate')
    return hops


def extract_crystal(action='collect'):
    charging_color = (24, 34, 38)
    crystal = not f.check_pixel_color_in_area((855, 440, 5, 5), charging_color, tolerance=3)
    if action == 'activate':
        f.move_click(846, 456, wait_duration=f.r(4, 5))  # Activate crystal
    if action == 'collect':
        if crystal is True:
            print('Crystal is available! Collecting it ...')
            f.move_click(846, 456, wait_duration=f.r(5, 6))  # Extract crystal
    return crystal


def main(setup=True):
    f.countdown(3)
    start_time = time.time()  # Start timer for script
    print(f'Starting script at {datetime.datetime.now()}')
    if setup:
        set_up()
        pag.press('f2')
    hop_counter = 0
    extract_crystal('activate')
    for n in range(1, 20):  # Number of loops
        hop_counter = hop_for_salvage(hop_counter)  # Checks if salvage is available and
        if hop_counter == 'end_script':
            print('Failed to find a world with salvage. Ending script.')
            break
        salvage()
        extract_crystal('collect')
        process_inv()
        extract_crystal('collect')
        if n % 2 == 0:
            sort_salvage()
            process_inv()
            extract_crystal('collect')
        print(f'Inventory {n} done at {datetime.datetime.now()}')
        print()

    print(f'Script duration: {str(datetime.timedelta(seconds=time.time() - start_time))}')


# process_inv()
if __name__ == "__main__":
    main(True)
