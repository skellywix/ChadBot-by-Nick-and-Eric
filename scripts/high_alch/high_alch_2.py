import time
import functions as f
import pyautogui as pag
import pytesseract
import re
import cv2 as cv
import numpy as np
import digit_extractor as de


def scan_inventory(inventory_slots):
    results = {}
    for slot_name, (cx, cy) in inventory_slots.items():
        x = cx - 18
        y = cy - 20

        # Capture slot screenshot
        img = f.take_screenshot(area=(x, y, 33, 15), save_img=True, img_name=f'{slot_name}.png')

        # ---- EMPTY SLOT DETECTION (NEW CODE) ----
        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        if np.std(gray) < 2 or (gray.max() - gray.min()) < 5:
            results[slot_name] = "empty_slot"
            continue
        else:
            results[slot_name] = img
    return results


def quantify_inv(n=16):
    pag.press('f2')
    inv = f.create_inv(n)
    inv_numbers = scan_inventory(inv)
    # print(inv)
    quantities = {}
    for i in inv_numbers:
        slot = inv_numbers[i]
        if type(slot) == str:
            quantities[i] = slot
            # return slot
        else:
            quantity = de.read_digits(slot)
            quantities[i] = [quantity, inv[i]]
    return quantities


def high_alch(inventory, xy, quantity):
    pag.press('f4')
    alch_spell = (1719, 877)

    for n in range(1, quantity + 1):
        f.move_click(*alch_spell)
        time.sleep(f.r(0.40, 0.60))
        f.move_click(*xy)
        print('.', end='')
        time.sleep(f.r(4, 5))


def main(n=27):
    f.move_click(1727, 45, move_duration=f.r(0.1, 0.15), wait_duration=f.r(0.1, 0.15))  # Click onto game screen
    inventory = quantify_inv(n)
    for slot, (count, (x, y)) in inventory.items():
        print(slot)
        print(count)
        print(x, y)
        print(f'High alching "{slot}" {count} times', end='')
        high_alch(inventory, slot, count)
        print()

if __name__ == "__main__":
    main(3)
