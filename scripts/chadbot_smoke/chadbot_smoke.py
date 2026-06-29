"""Safe smoke-test script for the ChadBot UI."""

import time


def main(iterations=10, interval=0.5):
    print("ChadBot smoke script started", flush=True)
    for index in range(1, iterations + 1):
        print(f"heartbeat {index}/{iterations}", flush=True)
        time.sleep(interval)
    print("ChadBot smoke script finished", flush=True)


if __name__ == "__main__":
    main()
