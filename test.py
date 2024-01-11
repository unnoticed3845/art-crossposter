import logging
logging.basicConfig(level=logging.DEBUG)

from src.dublicate_checker import DublicateChecker

dc = DublicateChecker()

print(dc.photo_exists("https://cdn.donmai.us/sample/85/4f/__aqua_kingdom_hearts_drawn_by_nsfw_bb__sample-854f650ac828bbe15c757c64bf6f52ce.jpg"))
