import time
import functions as f
import os


project_dir = os.path.dirname(__file__)


def start_course():
    f.move_click(941, 522, r1=f.p(6), r2=f.p(6))
    time.sleep(5.5 + f.r(1, 2))


def do_obstacle_1():
    f.move_click(672, 455, r1=f.p(5), r2=f.p(8))
    time.sleep(7.5 + f.r(0.6, 2))


def collect_obstacle_1():
    f.move_click(885, 478, r1=f.p(5), r2=f.p(5))
    time.sleep(2.5 + f.r(0.2, 0.5))
    f.move_click(722, 509, r1=f.p(5), r2=f.p(8))
    time.sleep(7.0 + f.r(0.6, 2))


def do_obstacle_2():
    f.move_click(835, 700, r1=f.p(4), r2=f.p(4))
    time.sleep(10 + f.r(1.1, 2.3))


def collect_obstacle_2():
    f.move_click(815, 566, r1=f.p(5), r2=f.p(5))
    time.sleep(3 + f.r(0.2, 0.5))
    f.move_click(850, 535, r1=f.p(5), r2=f.p(5))
    time.sleep(3.4 + f.r(0.2, 0.5))
    f.move_click(1080, 665, r1=f.p(5), r2=f.p(5))
    time.sleep(11.0 + f.r(1.2, 2))


def do_obstacle_3():
    f.move_click(1023, 661, r1=f.p(9), r2=f.p(3))
    time.sleep(6 + f.r(1.1, 2.3))


def collect_obstacle_3():
    f.move_click(1007, 506, r1=f.p(5), r2=f.p(5))
    time.sleep(3 + f.r(0.2, 0.5))
    f.move_click(940, 700, r1=f.p(7), r2=f.p(5))
    time.sleep(6.0 + f.r(1.2, 2.2))


def do_obstacle_4():
    f.move_click(646, 626, r1=f.p(10), r2=f.p(5))
    time.sleep(6.5 + f.r(1, 1.75))


def do_obstacle_5():
    f.move_click(980, 600, r1=f.p(4), r2=f.p(10))
    time.sleep(5.5 + f.r(1.2, 2.3))


def collect_obstacle_5():
    f.move_click(818, 535, r1=f.p(5), r2=f.p(5))
    time.sleep(3.5 + f.r(0.5, 1.1))
    f.move_click(1107, 540, r1=f.p(4), r2=f.p(6))
    time.sleep(6.0 + f.r(1.2, 2.2))


def reset_position():
    #  f.move_click(1418, 351, r1=f.p(4), r2=f.p(4))
    #  time.sleep(10.5 + f.r(1.4, 2.7))
    f.move_right_click(1444, 76)
    walk_option = f.find("walk_here_option.png", (1244, 26, 400, 400))
    f.move_click(walk_option[0], walk_option[1])
    time.sleep(15 + f.r(0.9, 2.3))


def do_lap():
    start_course()
    do_obstacle_1()
    if not check_if_failed_gap():
        do_obstacle_2()
        if not check_if_failed_tightrope():
            do_obstacle_3()
            do_obstacle_4()
            do_obstacle_5()
            reset_position()


def do_collection_lap():
    start_course()
    collect_obstacle_1()
    if not check_if_failed_gap():
        collect_obstacle_2()
        if not check_if_failed_tightrope():
            collect_obstacle_3()
            do_obstacle_4()
            collect_obstacle_5()
            reset_position()


def check_if_failed_tightrope():
    if f.check_pixel_color_in_area((924, 540, 45, 10), (255, 0, 0)):
        print('Tightrope failed! Resetting position.')
        f.move_right_click(1475, 411)
        walk_option = f.find("walk_here_option.png", (1275, 210, 400, 400))
        f.move_click(walk_option[0], walk_option[1])
        time.sleep(9.8 + f.r(1.2, 2.3))
        return True
    else:
        return False


def check_if_failed_gap():
    if f.check_pixel_color_in_area((923, 545, 45, 10), (255, 0, 0)):
        print('Gap failed! Resetting position.')
        f.move_right_click(1438, 707)
        walk_option = f.find("walk_here_option.png", (1238, 507, 400, 400))
        f.move_click(walk_option[0], walk_option[1])
        time.sleep(9.8 + f.r(1.2, 2.3))
        return True
    else:
        return False


def main():
    for n in range(1, 92):
        if n % 5 == 0:
            do_collection_lap()
        else:
            do_lap()
        print(f"Lap {n} done!")


if __name__ == "__main__":
    main()
