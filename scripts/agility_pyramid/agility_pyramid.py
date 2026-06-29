import cv2 as cv
import pyautogui as pag
import time
import os
import functions as f

# Done at 0% zoom
project_dir = os.path.dirname(__file__)


def wait_for(image, c=0.98):
    script_dir = os.path.dirname(__file__)
    img = os.path.join(script_dir, image)
    print('Waiting ', end='')
    while True:
        try:
            pag.locateOnScreen(img, confidence=c)
            print(f' now!')
            break
        except pag.ImageNotFoundException:
            print('.', end='')
            time.sleep(0.25)


def check_position(x, y, rgb, t=5):
    if pag.pixelMatchesColor(x, y, rgb, tolerance=t):
        pass
    else:
        pag.moveTo(972 + f.p(-4, 4), 535 + f.p(-4, 4), f.r(0.25, 0.75))
        pag.click()
        time.sleep(1.5 + f.r(0, 1))


def locate_simon():
    timer = time.time()
    pag.screenshot('s1.png', region=(640, 470, 400, 330))
    simon_area = cv.imread('s1.png', cv.IMREAD_UNCHANGED)
    simon = cv.imread('simon_templeton.png', cv.IMREAD_UNCHANGED)
    result = cv.matchTemplate(simon_area, simon, cv.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv.minMaxLoc(result)

    simon_w = simon.shape[1] / 2
    simon_h = simon.shape[0] / 2

    simon_location = (max_loc[0] + 640 + simon_w, max_loc[1] + 470 + simon_h)
    # print(simon_location)
    # print(time.time() - timer)
    return simon_location


def trade_with_simon():
    pag.moveTo(811 + f.p(-4, 4), 555 + f.p(-4, 4), f.r(0.25, 0.75))
    pag.click()
    time.sleep(6 + f.r(0.5, 0.9))

    start_time = time.time()
    elapsed_time = 0
    print('Searching for simon ', end='')

    while elapsed_time < 20:
        simon_movement = [locate_simon(), locate_simon()]
        if simon_movement[-1] == simon_movement[-2]:
            pag.moveTo(simon_movement[-1])
            pag.click()
            print('simon found!')
            # print(simon_movement)
            break
        elapsed_time = time.time() - start_time
        print('.', end='')
    if elapsed_time > 20:
        print('Could not locate simon.')
        # print(elapsed_time)
    else:
        time.sleep(6 + f.r(0.5, 0.9))
        pag.press('space')
        time.sleep(2 + f.r(0, 1))
        pag.press('1')
        time.sleep(2 + f.r(0, 1))
        print('Finished trading!')


def locate_start():
    pag.screenshot('s2.png', region=(0, 0, 1920, 1080))
    start_area = cv.imread('s2.png', cv.IMREAD_UNCHANGED)
    start_tile = cv.imread('start_tile.png', cv.IMREAD_UNCHANGED)
    result = cv.matchTemplate(start_area, start_tile, cv.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv.minMaxLoc(result)
    estimated_start_loc = (max_loc[0], max_loc[1] - 20)
    return estimated_start_loc


def reset_position():
    pag.moveTo(locate_start())
    pag.click()
    time.sleep(5)
    pag.moveTo(974 + f.p(-4, 4), 536 + f.p(-4, 4), f.r(0.25, 0.75))
    pag.click()
    time.sleep(7)
    pag.moveTo(1037 + f.p(-4, 4), 506 + f.p(-4, 4), f.r(0.25, 0.75))
    pag.click()
    time.sleep(5)


def main():
    f.countdown(3)
    f.initialize_pag()
    for n in range(1, 61):
        f.play_actions('agility_pyramid_pt1.json', project_dir)
        time.sleep(4)
        wait_for('pyramid_block_1.png', c=0.97)

        f.play_actions('agility_pyramid_pt2.json', project_dir)
        time.sleep(4)
        wait_for('pyramid_block_2.png', c=0.95)

        f.play_actions('agility_pyramid_pt3.json', project_dir)
        time.sleep(6)
        check_position(1140, 440, (255, 0, 0), 5)

        f.play_actions('agility_pyramid_pt4.json', project_dir)
        time.sleep(4)
        check_position(954, 506, (0, 255, 0), 5)

        f.play_actions('agility_pyramid_pt5.json', project_dir)
        time.sleep(7)
        print(f'Lap {n} done!')

        if n % 3 == 0:
            trade_with_simon()
            reset_position()
        if n % 15 == 0:
            f.play_actions('fill_water.json', project_dir)
            time.sleep(5)


if __name__ == "__main__":
    main()

# trade_with_simon()
# reset_position()

# f.play_actions('fill_water.json', project_dir)
