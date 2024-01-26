import logging
logging.basicConfig(format='[%(asctime)s] %(levelname)s %(name)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)

from src.manager import PostManager
from src.parsers import DanbooruParser, BlacklistedTag as BTag

logger = logging.getLogger(__name__)

def main():
    male_exc_tags = ['crossdressing', '1girl', '2girls', '3girls', '4girls']
    dp = DanbooruParser(
        tags=[
            "bdsm", "shibari", "armbinder",
            "legbinder", "predicament_bondage",
        ],
        blacklist_tags=[
            BTag("yaoi"), 
            BTag("pee"), BTag("peeing"), BTag("peeing_self"),
            BTag("cbt"), BTag("ball_busting"), BTag("crotch_kick"),
            BTag("1boy", male_exc_tags), BTag("2boys", male_exc_tags), 
            BTag("clothed_female_nude_male", male_exc_tags),
            BTag("male_focus", male_exc_tags),
            BTag("muscular_male", male_exc_tags),
            BTag("muscular", male_exc_tags),
        ],
    )
    post_manager = PostManager(
        update_timestamps=["07:00"],
        max_pages_to_parse=5
    )
    post_manager.add_parser(dp)
    post_manager.main_loop()

if __name__ == '__main__':
    main()
