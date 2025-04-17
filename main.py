import telegram as tg
import sys
import os
from src import bot, camera
import threading


def main():
    camera_thread = threading.Thread(target=camera.LiveCamera)
    camera_thread.start()
    bot.run_bot()

if __name__ == "__main__":
    main()