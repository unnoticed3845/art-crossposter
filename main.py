import logging
logging.basicConfig(format='[%(asctime)s] [%(levelname)s %(name)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)

from src.manager import PostManager
from src.parse import DanbooruParser, BlacklistedTag as BTag

logger = logging.getLogger(__name__)

def main():
    dp = DanbooruParser()
    post_manager = PostManager(
        update_timestamps=["16:23"],
        max_pages_to_parse=1
    )
    post_manager.add_parser(dp)
    post_manager.main_loop()

if __name__ == '__main__':
    main()
