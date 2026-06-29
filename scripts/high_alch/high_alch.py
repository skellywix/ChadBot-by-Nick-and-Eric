import time
import functions as f
import pyautogui as pag
import os
import pytesseract
import re

project_dir = os.path.dirname(__file__)


def create_grid(tl=(1683, 746), br=(1851, 998), rows=7, columns=4):
    grid = {}
    x = int((br[0] - tl[0]) / columns)
    y = int((br[1] - tl[1]) / rows)
    count = 0
    for row in range(tl[1], br[1], y):
        for column in range(tl[0], br[0], x):
            count += 1
            grid[f'Slot {count}'] = int(round(column + y/2)), int(round(row + x/2))
    return grid


def display_dict(dic):
    for entry in dic:
        print(entry, ':', dic[entry])


def test_grid(grid):
    for slot in grid:
        a, b = grid[slot][0], grid[slot][1]
        pag.moveTo(a, b)
        time.sleep(0.20)


def high_alch(inventory, slot, quantity):
    pag.press('f4')
    for n in range(1, quantity + 1):
        f.move_click(1695, 878)
        time.sleep(f.r(0.40, 0.60))
        f.move_click(inventory[slot][0], inventory[slot][1])
        print('.', end='')
        time.sleep(f.r(4, 5))


def quantify_inv(inv_dic, resize_factor=3):
    numbers = list()
    for slot in inv_dic:
        slot_cords = (inv_dic[slot][0] - 12, inv_dic[slot][1] - 18)
        screenshot = f.take_screenshot((*slot_cords, 19, 10), save_img=False)
        screenshot = f.isolate_exact_yellow(screenshot)
        screenshot = f.to_pil_and_resize(screenshot, x=resize_factor, y=resize_factor)
        # screenshot.save(f'{slot}.png')
        text = pytesseract.image_to_string(screenshot, config='--psm 7')
        num = re.findall(r'\d+', text)
        num = 0 if num == [] else num[0]
        # print(f'Number {num} found in {slot}')
        num = 0 if num == '' else int(num)
        numbers.append(num)
    return numbers


def main(inventory, quantities):
    f.move_click(1727, 45)
    print(quantities)
    for slot, quant in zip(inventory, quantities):
        print(f'High alching "{slot}" {quant} times', end='')
        high_alch(inventory, slot, quant)
        print()


if __name__ == "__main__":
    # inventory is about 168 pixels wide and 252 pixels tall
    inv = create_grid(tl=(1683, 746), br=(1851, 998), rows=7, columns=4)
    number_of_alchemy = quantify_inv(inv)[0:24]
    print(number_of_alchemy)
    main(inv, number_of_alchemy)
