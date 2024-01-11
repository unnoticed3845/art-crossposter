import logging
logging.basicConfig(format='[%(asctime)s] %(levelname)s %(name)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.INFO)

from src.manager import PostManager
from src.parsers import DanbooruParser

logger = logging.getLogger(__name__)

def main():
    db = DanbooruParser(
        tags=[
            "bdsm", "shibari", "armbinder",
            "legbinder", "predicament_bondage",
        ],
        blacklist_tags=[
            "yaoi", "2boys", "male_focus",
            "muscular_male", "muscular",
            "clothed_female_nude_male",
            "cbt", "ball_busting", "crotch_kick"
        ],
    )
    post_manager = PostManager(
        update_timestamps=["07:00"]
    )
    post_manager.add_parser(db)
    post_manager.main_loop()

if __name__ == '__main__':
    main()
