from typing import List, Set, Tuple, Dict, Any
from json import dump, load
from random import randint
from pprint import pformat
from pathlib import Path
import datetime as dt
import logging
import time
import os

from src.parsers import ArtworkParser, Post
import src.tg_bot as tg_bot

logger = logging.getLogger("PostManager")
log_file = "log/postmanager.log"
os.makedirs(os.path.dirname(log_file), exist_ok=True)
fh = logging.FileHandler(log_file)
fh.setLevel(logging.DEBUG)
ff = logging.Formatter('[%(asctime)s] %(levelname)s %(message)s')
fh.setFormatter(ff)
logger.addHandler(fh)

class PostManager:
    __schedule_file = Path(__file__).parent.joinpath('data/schedule.json')
    time_format = '%Y-%m-%d %H:%M'

    def __init__(
        self,
        update_timestamps: List[str] = ["07:00"],
        check_interval: int = 60,
        max_pages_to_parse: int = 3
    ) -> None:
        # initializing
        self.__update_time = [ self.form_today_timestamp(t) for t in update_timestamps ]
        # skipping past update times so they are only triggered tomorrow
        cur_time = dt.datetime.now()
        for i in range(len(self.__update_time)):
            if self.__update_time[i] < cur_time:
                self.__update_time[i] += dt.timedelta(days=1)

        self.do_run = True
        self.__check_interval = check_interval
        self.__max_pages = max_pages_to_parse

        self.__parsers: List[ArtworkParser] = []
        self.post_schedule: Set[Tuple[dt.datetime, Post]] = set()
        self.__load_schedule_data()

        logger.info(f"Initialization done.\n{str(self)}")

    def main_loop(self) -> None:
        if len(self.__parsers) == 0:
            raise Exception('PostManager has no parsers added. Use PostManager.add_parser() to add parsers.')
        while self.do_run:
            logger.debug(f"Checking if something to do...")
            self.__check_schedule()
            if self.__is_time_for_update():
                logger.info(f"Updating!")
                new_posts = self.gather_new_posts()
                logger.info("Gathered {p} posts with {i} images in total".format(
                    p=len(new_posts),
                    i=sum(len(p.media_urls) for p in new_posts) if new_posts else 0
                ))
                self.__schedule_posts(new_posts)
            time.sleep(self.__check_interval)

    def add_parser(self, parser: ArtworkParser) -> None:
        if not isinstance(parser, ArtworkParser):
            raise ValueError('parser must be inherited from ArtworkParser')
        self.__parsers.append(parser)

    def gather_new_posts(self) -> List[Post]:
        posts = []
        for parser in self.__parsers:
            posts.extend(parser.scrape_posts(self.__max_pages))
        return posts
    
    def __check_schedule(self) -> None:
        logger.debug(f"Checking post schedule...")
        cur_time = dt.datetime.now()
        posted = set()
        for post_time, post in self.post_schedule:
            if post_time < cur_time:
                logger.info(f"Posting {post}")
                tg_bot.send_media(
                    media = post.media_urls,
                    caption = post.form_caption()
                )
                posted.add((post_time, post))
        if len(posted) == 0:
            logger.debug(f"No posts to be posted.")
        else:
            self.post_schedule.difference_update(posted)
            self.__save_schedule_data()
    
    def __schedule_posts(self, posts: List[Post]) -> None:
        if len(posts) == 0: return
        till_update = self.get_time_till_next_update()
        # I do not want to post anything past 23:59
        max_post_time = dt.datetime.combine(dt.date.today(), dt.time(23, 59))
        till_max_post_time = max_post_time - dt.datetime.now()
        schedule_upper_limit = min(till_update, till_max_post_time)
        for post in posts:
            post_time = dt.datetime.now() + \
                        dt.timedelta(seconds=randint(0, schedule_upper_limit.seconds))
            self.post_schedule.add((
                post_time,
                post
            ))
            logger.debug(f"Post {post} scheduled at {post_time}")
        self.__save_schedule_data()
        
    def __is_time_for_update(self) -> bool:
        logger.debug(f"Checking if its update time...")
        cur_time = dt.datetime.now()
        for i in range(len(self.__update_time)):
            if self.__update_time[i] < cur_time:
                # this way it will trigger next time only on the next day
                self.__update_time[i] += dt.timedelta(days=1)
                return True
        logger.debug(f"It is not time for update now.")
        return False

    def get_time_till_next_update(self) -> dt.timedelta:
        cur_time = dt.datetime.now()
        min_next_time = cur_time + dt.timedelta(days=1)
        for timestamp in self.__update_time:
            if cur_time < timestamp < min_next_time:
                min_next_time = timestamp
        return min_next_time - cur_time

    @staticmethod
    def form_today_timestamp(time: str) -> dt.datetime:
        time = dt.time.fromisoformat(time)
        date = dt.date.today()
        return dt.datetime.combine(date, time)

    def __load_schedule_data(self) -> None:
        if not self.__schedule_file.is_file():
            self.post_schedule = set()
            return
        
        with open(self.__schedule_file, 'r', encoding='utf-8') as f:
            schedule_list: List[Dict[str, Any]] = load(f)
        
        for i in range(len(schedule_list)):
            schedule_list[i] = (
                dt.datetime.strptime(schedule_list[i]['timestamp'], self.time_format),
                Post(
                    media_urls=tuple(schedule_list[i]['post']['media_urls']),
                    author_name=schedule_list[i]['post']['author_name'],
                    source_link=schedule_list[i]['post']['source_link'],
                    tags=tuple(schedule_list[i]['post']['tags'])
                )
            )
        self.post_schedule = set(schedule_list)
        logger.info(f"Loaded {len(self.post_schedule)} posts from {self.__schedule_file}")
        
    def __save_schedule_data(self) -> None:
        if not self.__schedule_file.is_file():
            self.__schedule_file.parent.mkdir(exist_ok=True, parents=True)
            self.__schedule_file.touch()
        schedule_list = list(self.post_schedule)
        for i in range(len(schedule_list)):
            timestamp, post = schedule_list[i][0], schedule_list[i][1]
            schedule_list[i] = {
                'timestamp': timestamp.strftime(self.time_format),
                'post': {
                    'media_urls': list(post.media_urls),
                    'author_name': post.author_name,
                    'source_link': post.source_link,
                    'tags': list(post.tags)
                }
            }
        with open(self.__schedule_file, 'w', encoding='utf-8') as f:
            dump(schedule_list, f, indent=4)
        logger.info(f"Saved {len(schedule_list)} posts to {self.__schedule_file}")

    def __repr__(self) -> str:
        scheduled_posts = [(t.strftime(self.time_format), a) for (t, a) in self.post_schedule]
        scheduled_posts.sort(key=lambda x: x[0])
        update_time = [x.strftime(self.time_format) for x in self.__update_time]
        return "Update time:\n" + \
               pformat(update_time) + '\n' + \
               "Scheduled posts:\n" + \
               pformat(scheduled_posts)
