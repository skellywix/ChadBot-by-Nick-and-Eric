import cv2 as cv
import pyautogui as pag
import functions as f
import time
import os
import datetime


project_dir = os.path.dirname(__file__)
pickpocket_count = 0


def set_up():
    pass


def find_farmer():
    # Searches and finds farmer in a certain area and returns coordinates
    mf_coordinates = f.find('master_farmer.png', (500, 100, 1000, 800))
    return mf_coordinates


def pickpocket_farmer(coordinates):
    global pickpocket_count
    pag.moveTo(coordinates[0], coordinates[1], f.r(0.036, 0.054))
    pag.rightClick()
    pickpocket_option = f.find_spots('pickpocket_option.png', threshold=0.88,
                                     area=(coordinates[0]-100, coordinates[1], 200, 150))
    if pickpocket_option is None:
        pag.move(f.r(-100, 100), -f.r(10, 100), f.r())
        time.sleep(f.r(1, 1.5))
    else:
        pickpocket_count += 1
        pickpocket_option = pickpocket_option[0]
        option = cv.imread('pickpocket_option.png', cv.IMREAD_UNCHANGED)
        needle_w = round(option.shape[1] / 2)
        needle_h = round(option.shape[0] / 2)
        pickpocket_option = (pickpocket_option[0] + needle_w + coordinates[0]-100,
                             pickpocket_option[1] + needle_h + coordinates[1])
        # print(pickpocket_option)
        pag.moveTo(pickpocket_option[0] + f.p(2), pickpocket_option[1] + f.p(2), f.r(0.036, 0.054))
        pag.click()
        time.sleep(f.r(2, 2.5))


def run_his_pockets_dry():
    # time_elapsed = 0
    # time_start = time.time()
    # while time_elapsed < 600:
    coordinates = find_farmer()
    pickpocket_farmer(coordinates)
    # time_elapsed = time.time() - time_start


def check_inv():
    full = f.find_spots('inv_full_slot.png', threshold=0.96, area=(1800, 960, 70, 60))
    if full:
        full = False
    else:
        full = True
        print('Inventory full!')
    return full


def bank_seeds():
    f.play_actions('bank_seeds_pt1.json', project_dir)
    f.move_right_click(1725, 801, r1=f.p(1), r2=f.p(1))
    f.move_click(1686, 860, r1=f.p(1), r2=f.p(1))
    time.sleep(f.r(2, 4))
    pag.press('f2')
    f.move_click(930, 50)
    time.sleep(f.r(5, 10))


def main(setup=False):
    f.countdown(3)
    f.initialize_pag()
    start_time = time.time()
    print(f'Script starting at: {datetime.datetime.now()}')
    if setup:
        set_up()
    for g in range(1, 8):  # Inventories to do
        full = False
        while not full:
            for n in range(1, 6):
                run_his_pockets_dry()
            full = check_inv()
        bank_seeds()
        print(f'Inventory {g} done at {datetime.datetime.now()}')
    print(f'Script duration: {str(datetime.timedelta(seconds=time.time() - start_time))}')
    print(f'Total pickpockets: {pickpocket_count}')


if __name__ == "__main__":
    main()
