import argparse
import cv2 as cv
import time
from functions import WindowCapture, Vision


def capture_runelite(search_image):
    wincap = WindowCapture()
    vision_limestone = Vision(search_image)

    loop_time = time.time()

    while True:

        # get an updated image of the game
        screenshot = wincap.get_screenshot()

        # display the processed image
        points = vision_limestone.find(screenshot, 0.45, 'rectangles')
        # points = vision_gunsnbottle.find(screenshot, 0.7, 'points')

        # debug the loop rate
        print('FPS {}'.format(1 / (time.time() - loop_time)))
        loop_time = time.time()

        # press 'q' with the output window focused to exit.
        # waits 1 ms every loop to process key presses
        if cv.waitKey(1) == ord('q'):
            cv.destroyAllWindows()
            break

    print('Done.')


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run live template matching against the RuneLite window.")
    parser.add_argument(
        "template",
        help="Template image to locate. Relative paths are resolved from the script folder, current folder, or repo root.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    capture_runelite(args.template)
