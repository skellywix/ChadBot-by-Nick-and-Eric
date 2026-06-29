import cv2 as cv
import pyautogui as pag
import functions as f
import time
import datetime

capes_built = 0


def build():
    global capes_built
    f.move_right_click(944, 403)
    build_option = f.find_spots('build_option.png', threshold=0.90,
                                area=(844, 403, 200, 150))
    if build_option is None:
        pag.move(f.r(-100, 100), -f.r(10, 100), f.r())
        time.sleep(f.r(2, 2.5))
        print('Build option not found.')
    else:
        build_option = build_option[0]
        option = cv.imread('build_option.png', cv.IMREAD_UNCHANGED)
        needle_w = round(option.shape[1] / 2)
        needle_h = round(option.shape[0] / 2)
        build_option = (build_option[0] + needle_w + 944 - 100,
                        build_option[1] + needle_h + 403)
        # print(pickpocket_option)
        pag.moveTo(build_option[0] + f.p(2), build_option[1] + f.p(2), f.r(0.14, 0.31))
        pag.click()
        time.sleep(f.r(0.7, 1.3))
        pag.press('4')
        time.sleep(f.r(2.1, 2.9))
        capes_built += 1


def remove():
    f.move_right_click(944, 403)
    remove_option = f.find_spots('remove_option.png', threshold=0.88,
                                 area=(844, 403, 200, 150))
    if remove_option is None:
        pag.move(f.r(-100, 100), -f.r(10, 100), f.r())
        time.sleep(f.r(2, 2.5))
        print('Remove option not found.')
    else:
        remove_option = remove_option[0]
        option = cv.imread('remove_option.png', cv.IMREAD_UNCHANGED)
        needle_w = round(option.shape[1] / 2)
        needle_h = round(option.shape[0] / 2)
        remove_option = (remove_option[0] + needle_w + 944 - 100,
                         remove_option[1] + needle_h + 403)
        # print(pickpocket_option)
        pag.moveTo(remove_option[0] + f.p(2), remove_option[1] + f.p(2), f.r(0.14, 0.31))
        pag.click()
        time.sleep(f.r(0.7, 1.5))
        pag.press('1')
        time.sleep(f.r(1.1, 1.5))


def check_if_payment_needed():
    pay_request = f.find_spots('payment_request.png', threshold=0.95,
                               area=(300, 930, 60, 30))
    if pay_request is None:  # If no payment request is detected function will return False
        return False
    else:
        return True


def pay_servant():
    print('payment requested')
    pag.press('space')
    time.sleep(f.r(2, 3))
    pag.press('1')
    time.sleep(f.r(2, 3))
    pag.press('space')
    time.sleep(f.r(2, 3))
    pag.press('space')
    time.sleep(f.r(2, 3))
    pag.press('f2')


def call_servant():
    pag.press('f5')
    f.move_click(1788, 937, wait_duration=f.r(1, 2))
    pag.click()  # Call servant
    time.sleep(f.r(3, 5))

    # Determine if the servant is requesting payment
    pay_request = check_if_payment_needed()
    if pay_request is False:
        pag.press('1')
        time.sleep(f.r(9, 12))
        pag.press('f2')
        pay_request = check_if_payment_needed()  # Check if payment is requested again
        if pay_request:
            pay_servant()
    else:
        pay_servant()
        pag.press('1')
        time.sleep(f.r(9, 12))
        pag.press('f2')


def main():
    f.countdown(3)
    f.initialize_pag()
    start_time = time.time()
    print(f'Script starting at: {datetime.datetime.now()}')

    for inv in range(1, 7):
        for n in range(1, 9):
            build()
            remove()
        call_servant()

    print(f'Script duration: {str(datetime.timedelta(seconds=time.time() - start_time))}')
    print(f'Total mythical capes built: {capes_built}')


if __name__ == "__main__":
    main()
