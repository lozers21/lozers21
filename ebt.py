import os
import sys
import time
import base64
import threading
import msvcrt
import textwrap
import winsound
import re
from datetime import datetime

os.system("cls")
os.system("title Chatapp")
os.system("")

CHAT_FILE = r"chat.txt"
LOCKDOWN_STRING = """

Logging service unavailable (error 0x15)

""".strip()

RULES = f"""
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
1. NO RACISM
2. NO SEXISM
3. All chats must follow the South Australian Law
4. The creators of this are not reponsible for any misuse
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
"""
MAX_MESSAGES = 2000
MAX_MSG_LEN  = 500
HISTORY_SHOW = 50
REFRESH_RATE = 0.5
WRAP_WIDTH   = 100
PREFIX       = "-"

GREEN  = "\033[32m"
BLUE   = "\033[34m"
GRAY   = "\033[90m"
YELLOW = "\033[33m"
RED    = "\033[31m"
CYAN   = "\033[36m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

running      = True
last_lines   = []
input_buffer = ""
username     = ""
console_lock = threading.Lock()
state_lock   = threading.Lock()

HELP_MENU = f"""
{PREFIX}help        -Returns this help menu
{PREFIX}tac         -Returns the T&C's
"""

def _beep():
    try:
        winsound.MessageBeep()
    except Exception:
        pass


def _timestamp():
    return datetime.now().strftime("%H:%M")


def _sanitise(text):
    text = re.sub(r'\x1b\[[0-9;]*m', '', text)
    text = re.sub(r'[\x00-\x1f\x7f]', '', text)
    return text.strip()


def _wrap(line):
    if not WRAP_WIDTH or len(line) <= WRAP_WIDTH:
        return line
    return textwrap.fill(line, width=WRAP_WIDTH, subsequent_indent="    ")


def intro():
    print(f"{BLUE}{BOLD}{'─' * 50}{RESET}")
    print(f"Anonymous chatapp")
    print(f"{BLUE}{BOLD}{'─' * 50}{RESET}\n")


def _ensure_file():
    try:
        directory = os.path.dirname(CHAT_FILE)
        if directory:
            os.makedirs(directory, exist_ok=True)
        if not os.path.exists(CHAT_FILE):
            with open(CHAT_FILE, "w", encoding="utf-8") as f:
                pass
    except Exception:
        pass


def _load():
    try:
        if not os.path.exists(CHAT_FILE):
            return []
        
        lines = []
        # Open in read mode with error ignoring for smooth parsing
        with open(CHAT_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    # Individual decoding shields against partial/corrupted writes
                    decoded = base64.b64decode(line.encode()).decode("utf-8")
                    if decoded.strip():
                        lines.append(decoded)
                except Exception:
                    if line == LOCKDOWN_STRING:
                        pass 
    except Exception:
        return []
    return lines


def _is_locked_down():
    try:
        if not os.path.exists(CHAT_FILE):
            return False
        with open(CHAT_FILE, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read().strip()
            return LOCKDOWN_STRING in content
    except Exception:
        return False


def _append(message, bypass_lockdown=False):
    if not bypass_lockdown and _is_locked_down():
        return

    encoded_msg = base64.b64encode(message.encode("utf-8")).decode("ascii")

    try:
        with open(CHAT_FILE, "a", encoding="utf-8") as f:
            f.write(encoded_msg + "\n")
    except Exception:
        pass


def _hide_prompt():
    width = len(input_buffer) + 2
    sys.stdout.write(f"\r{' ' * width}\r")
    sys.stdout.flush()


def _show_prompt():
    sys.stdout.write(f">{RESET}{input_buffer}")
    sys.stdout.flush()


def _print(line):
    with console_lock:
        _hide_prompt()
        sys.stdout.write(_wrap(line) + "\n")
        _show_prompt()


def _watcher():
    global last_lines

    while running:
        try:
            current = _load()

            with state_lock:
                old = last_lines
                old_len = len(old)

            if current != old:
                if old_len == 0:
                    for ln in current[-HISTORY_SHOW:]:
                        _print(ln)
                else:
                    new_msgs = current[old_len:]
                    if new_msgs:
                        _beep()
                        for ln in new_msgs:
                            _print(ln)

                with state_lock:
                    last_lines = current

        except Exception:
            pass

        time.sleep(REFRESH_RATE)
def main():
    global username, running, last_lines, input_buffer

    _ensure_file()

    while True:
        raw   = input("Enter username ").strip()
        clean = _sanitise(raw) or "Anonymous:"
        if len(clean) > 30:
            print("Username too long (max 30 chars). Try again.")
            continue
        username = clean
        os.system(f"title Chatapp - {username}")
        os.system('cls' if os.name == 'nt' else "clear")
        print("BEFORE CONTINUING, YOU MUST AGREE TO THE T&C's (Terms and conditions). \nPlease fully read the below before continuing")
        print(RULES)
        tac = input("Do you agree to the T&C's? (Y/N) >").lower()
        if tac.lower() == 'y':
            print(f"You can view the T&C's anytime with the command '{PREFIX}tac'")
            os.system('cls' if os.name == 'nt' else "clear")
            break
        else:
            sys.exit()

    print("\nConnecting...")
    time.sleep(0.4)

    intro()

    with state_lock:
        last_lines = _load()

    for ln in last_lines[-HISTORY_SHOW:]:
        print(_wrap(ln))

    ts = _timestamp()
    _append(f"{GREEN}[{ts}] [+] {username} joined. {RESET}", bypass_lockdown=True)

    print()

    threading.Thread(target=_watcher, daemon=True).start()

    with console_lock:
        _show_prompt()

    try:
        while running:
            if not msvcrt.kbhit():
                time.sleep(0.01)
                continue

            ch = msvcrt.getwch()

            if ch == "\r":
                msg = input_buffer.strip()
                input_buffer = ""

                with console_lock:
                    _hide_prompt()

                if msg:
                    if msg.lower() == f"{PREFIX}tac" or msg.lower() == f"{PREFIX}tac":
                        print(BLUE + "%" * 50, RED)
                        print(RULES)
                        print(BLUE + "%" * 50, RESET)
                        with console_lock:
                            _show_prompt()
                    elif msg.lower() == f'{PREFIX}help':
                        print(HELP_MENU)
                        with console_lock:
                            _show_prompt()
                    elif msg.lower() == f"{PREFIX}exit":
                        running = False
                        ts = _timestamp()
                        try:
                            _append(f"{GRAY}[{ts}] [-] {username} left.{RESET}", bypass_lockdown=True)
                            sys.exit()
                        except Exception:
                            pass
                    elif msg.startswith(PREFIX):
                        print(f"Unknown entry.\ndo '{PREFIX}help' for a list of commands!")
                        _show_prompt()
                    elif len(msg) > MAX_MSG_LEN:
                        _print(f"{RED}[SYSTEM] Message too long ({len(msg)}/{MAX_MSG_LEN} chars).{RESET}")
                    else:
                        if _is_locked_down():
                            _print(f"{RED}Administrator has blocked all user access, until cleared, you are no longer able to chat.{RESET}")
                        else:
                            ts = _timestamp()
                            _append(f"[{ts}] {username}: {msg}")
                else:
                    with console_lock:
                        _show_prompt()

            elif ch == "\b":
                if input_buffer:
                    input_buffer = input_buffer[:-1]
                    with console_lock:
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()

            elif ch in ("\x00", "\xe0"):
                msvcrt.getwch()

            elif ch == "\x03":
                raise KeyboardInterrupt

            else:
                if ord(ch) >= 32 and len(input_buffer) < MAX_MSG_LEN:
                    input_buffer += ch
                    with console_lock:
                        sys.stdout.write(ch)
                        sys.stdout.flush()

    except KeyboardInterrupt:
        pass

    finally:
        running = False
        ts = _timestamp()
        try:
            _append(f"{GRAY}[{ts}] [-] {username} left.{RESET}", bypass_lockdown=True)
        except Exception:
            pass
        print(f"\n{RED}Connection closed.{RESET}")


if __name__ == "__main__":
    main()
