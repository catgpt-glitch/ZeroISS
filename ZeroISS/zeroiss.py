#!/usr/bin/env python3
import configparser
import csv
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

BASE_DIR = Path.home() / "ZeroISS"
CONFIG_FILE = BASE_DIR / "config.ini"
SCHEDULE_FILE = BASE_DIR / "schedule.csv"

rtl_process = None


def load_config():
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_FILE)
    return cfg


def ask(prompt, default=""):
    val = input(f"{prompt} [{default}] : ").strip()
    return default if val == "" else val


def sh(cmd):
    return subprocess.run(
        cmd, shell=True, text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    ).stdout.strip()


def stop_rtl():
    global rtl_process
    if rtl_process and rtl_process.poll() is None:
        os.killpg(os.getpgid(rtl_process.pid), signal.SIGTERM)
        try:
            rtl_process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(rtl_process.pid), signal.SIGKILL)
            rtl_process.wait()
    rtl_process = None


def start_monitor(freq, gain, ppm):
    global rtl_process
    stop_rtl()

    cmd = (
        "/usr/local/bin/rtl_fm -f {freq} -M fm -s 48k -r 48k -E deemp "
        f"-g {gain} -p {ppm} - | "
        f"cvlc - --demux=rawaud "
        f"--rawaud-channels 1 "
        f"--rawaud-samplerate 48000 "
        f"--sout '#transcode{{acodec=mp3,ab=64,channels=1,samplerate=48000}}:"
        f"http{{mux=mp3,dst=:4687/aaa.mp3}}' "
        f"vlc://quit"
    )

    rtl_process = subprocess.Popen(
        cmd,
        shell=True,
        preexec_fn=os.setsid
    )
    print(f"[MONITOR] started at {freq} Hz")
    print("Stream: http://<ZeroISS-IP>:4687/aaa.mp3")


def load_schedule():
    rows = []
    with open(SCHEDULE_FILE, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            first = row[0].strip()
            if first.startswith("#"):
                continue
            try:
                ts = int(first)
                freq = int(row[1].strip())
                rows.append((ts, freq))
            except (ValueError, IndexError):
                continue
    rows.sort()
    return rows


def record_pass(gain, ppm, rec_dir):
    global rtl_process

    schedule = load_schedule()
    if not schedule:
        print("schedule.csv is empty or invalid")
        return

    rec_dir = Path(rec_dir)
    rec_dir.mkdir(parents=True, exist_ok=True)

    out_file = rec_dir / f"ISS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    current_freq = None

    print(f"[REC] output -> {out_file}")

    try:
        while True:
            now = int(time.time())

            next_freq = None
            for ts, freq in schedule:
                if ts <= now:
                    next_freq = freq
                else:
                    break

            if next_freq is None:
                time.sleep(0.5)
                continue

            if now > schedule[-1][0]:
                print("[REC] finished")
                break

            if next_freq != current_freq:
                stop_rtl()

                cmd = (
                    f"rtl_fm -f {next_freq} -M fm -s 48k -r 48k -E deemp "
                    f"-g {gain} -p {ppm} - | "
                    f"ffmpeg -loglevel error -y "
                    f"-f s16le -ar 48000 -ac 1 -i - "
                    f"'{out_file}'"
                )

                rtl_process = subprocess.Popen(
                    cmd,
                    shell=True,
                    preexec_fn=os.setsid
                )
                current_freq = next_freq
                print(f"[REC] tuned -> {next_freq}")

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n[REC] interrupted")

    finally:
        stop_rtl()


def cron_apply():
    """
    ZeroISS用cronを上書きする最小版
    """
    python_bin = sys.executable
    zeroiss_py = BASE_DIR / "zeroiss.py"

    marker_start = "# >>> ZeroISS >>>"
    marker_end = "# <<< ZeroISS <<<"

    # 例: 毎日 03:00 に pass計算
    block = f"""{marker_start}
07 19 10 3 * {python_bin} {zeroiss_py} --record >> {BASE_DIR}/zeroiss.log 2>&1
{marker_end}
"""

    current = sh("crontab -l 2>/dev/null")
    lines = current.splitlines()

    new_lines = []
    inside = False
    for line in lines:
        if line.strip() == marker_start:
            inside = True
            continue
        if line.strip() == marker_end:
            inside = False
            continue
        if not inside:
            new_lines.append(line)

    new_lines.append(block.strip())
    tmp = BASE_DIR / ".cron.tmp"
    tmp.write_text("\n".join(new_lines) + "\n")

    os.system(f"crontab {tmp}")
    tmp.unlink(missing_ok=True)
    print("[CRON] applied")


def calc_pass_placeholder():
    """
    たたき台:
    今は手動CSVを置く前提。
    次にここへ TLE計算を入れる。
    """
    print("[CALC] placeholder")
    print("Next step: auto-generate schedule.csv from ISS TLE")


def menu():
    print("""
===== ZeroISS =====
1) ISS pass Calculation🚀
2) cron Schedule (Overwrite)
3) Live Monitor
4) Automatic Recording Test
Q) Quit
""")


def main():
    cfg = load_config()

    gain = cfg.get("radio", "gain", fallback="20")
    ppm = cfg.get("radio", "ppm", fallback="0")
    base_freq = cfg.get("radio", "base_freq", fallback="145800000")
    rec_dir = cfg.get("record", "dir", fallback=str(BASE_DIR / "records"))

    if len(sys.argv) > 1:
        if sys.argv[1] == "--calc":
                calc_pass_placeholder()
                return

        elif sys.argv[1] == "--record":
                record_pass(gain, ppm, rec_dir)
                return


    while True:
        menu()
        sel = input("> ").strip().lower()


        if sel == "1":
            calc_pass_placeholder()

        elif sel == "2":
            cron_apply()

        elif sel == "3":
            freq = ask("Monitor freq (Hz)", base_freq)
            start_monitor(freq, gain, ppm)
            input("Press Enter to stop monitor...")
            stop_rtl()

        elif sel == "4":
            record_pass(gain, ppm, rec_dir)

        elif sel == "q":
            stop_rtl()
            break


if __name__ == "__main__":
    main()
  

