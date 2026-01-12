import os
import subprocess

LOG_FILE = "operator_chat.log"
POINTER_FILE = "log_pointer.txt"


def get_new_messages():
    if not os.path.exists(LOG_FILE):
        return []

    start_pos = 0
    if os.path.exists(POINTER_FILE):
        with open(POINTER_FILE, "r") as f:
            try:
                start_pos = int(f.read().strip())
            except:
                start_pos = 0

    with open(LOG_FILE, "r") as f:
        f.seek(start_pos)
        new_content = f.read()
        new_pos = f.tell()

    with open(POINTER_FILE, "w") as f:
        f.write(str(new_pos))

    return [line for line in new_content.split("\n") if line.strip()]


if __name__ == "__main__":
    messages = get_new_messages()
    for msg in messages:
        print(msg)
