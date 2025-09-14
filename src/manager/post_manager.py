from typing import List, Set, Tuple, Dict, Any
from json import dump, load
from random import randint
from pprint import pformat
from pathlib import Path
import datetime as dt
import logging
import pytgbot
import json
import time
import os

from src.dublicate_checker import DublicateChecker
from src.parse import BaseParser, Post
from src.request_utils import strip_args_from_url
from src.config import log_dir, config_dir, data_dir
import src.tg_bot as tg_bot

logger = logging.getLogger("PostManager")
log_file = log_dir.joinpath("postmanager.log")
fh = logging.FileHandler(log_file)
fh.setLevel(logging.DEBUG)
ff = logging.Formatter('[%(asctime)s] %(levelname)s %(message)s', '%Y-%m-%d %H:%M:%S')
fh.setFormatter(ff)
logger.addHandler(fh)

class PostManager:
    time_format = '%Y-%m-%d %H:%M'

    def __init__(
        self, 
        config_file: str = 'scheduler_conf.json',
        schedule_file: str = 'schedule.json'
    ) -> None:
        with open(config_dir.joinpath(config_file), 'r', encoding = 'utf-8') as f:
            self.config = load(f)
        # initializing
        self.__update_time = [self.form_today_timestamp(t) 
                              for t in self.config['update_time']]
        # skipping past update times so they are only triggered tomorrow
        cur_time = dt.datetime.now()
        for i in range(len(self.__update_time)):
            if self.__update_time[i] < cur_time:
                self.__update_time[i] += dt.timedelta(days=1)

        self.do_run = True
        self.__check_interval = self.config['check_interval']

        self.__parsers: List[BaseParser] = []
        self.post_schedule: Set[Tuple[dt.datetime, Post]] = set()
        self.__schedule_file = data_dir.joinpath(schedule_file)
        self.__load_schedule_data()

        self.dub_checker = DublicateChecker()

        logger.info(f"Initialization done.\n{str(self)}")

    def main_loop(self) -> None:
        if len(self.__parsers) == 0:
            raise Exception('PostManager has no parsers added. Use PostManager.add_parser() to add parsers.')
        while self.do_run:
            logger.debug(f"Checking if something to do...")
            self.__check_post_schedule()
            self.__check_update_schedule()
            time.sleep(self.__check_interval)

    def add_parser(self, parser: BaseParser) -> None:
        if not isinstance(parser, BaseParser):
            raise ValueError('parser must be inherited from BaseParser')
        self.__parsers.append(parser)

    def __check_update_schedule(self) -> None:
        if self.__is_time_for_update():
            logger.info(f"Updating!")
            new_posts = self.gather_new_posts()
            logger.info("Gathered {p} posts with {i} images in total".format(
                p=len(new_posts),
                i=sum(len(p.media_urls) for p in new_posts) if new_posts else 0
            ))
            self.__schedule_posts(new_posts)

    def gather_new_posts(self) -> List[Post]:
        posts: List[Post] = []
        for parser in self.__parsers:
            posts.extend(parser.scrape_posts())
        return posts

    def __check_post_schedule(self) -> None:
        logger.debug(f"Checking post schedule...")
        cur_time = dt.datetime.now()
        failed: Set[Tuple[dt.datetime, Post]] = set()
        posted: Set[Tuple[dt.datetime, Post]] = set()
        for post_time, post in self.post_schedule:
            if post_time < cur_time:
                logger.info(f"Posting {post}")
                try:
                    tg_bot.send_media(
                        media = post.media_urls,
                        caption = post.form_caption()
                    )
                    posted.add((post_time, post))
                except pytgbot.exceptions.TgApiServerException:
                    logger.warning(f'Failed to post {post}')
                    failed.add((post_time, post))
        if len(failed) > 0:
            logger.warning(f'Failed to post {len(failed)} posts. Rescheduling them')
            self.post_schedule.difference_update(failed)
            self.__schedule_posts([x[1] for x in failed])
        if len(posted) > 0:
            logger.info(f'Posted {len(posted)} posts')
            self.post_schedule.difference_update(posted)
        if len(failed) > 0 or len(posted) > 0:
            self.__save_schedule_data()
    
    @staticmethod
    def __random_ordered_timestamps(
        n: int,
        delta: dt.timedelta
    ) -> List[dt.datetime]:
        now = dt.datetime.now()
        def random_timestamp() -> dt.datetime:
            return now + dt.timedelta(seconds=randint(0, delta.seconds))
        return sorted(random_timestamp() for _ in range(n))

    def __schedule_posts(self, posts: List[Post]) -> None:
        if len(posts) == 0: return
        till_update = self.get_time_till_next_update()
        # I do not want to post anything past 23:59
        max_post_time = dt.datetime.combine(dt.date.today(), dt.time(23, 59))
        till_max_post_time = max_post_time - dt.datetime.now()
        # Generating posting time for each post and sorting it to keep original post order
        post_timestamps = self.__random_ordered_timestamps(
            n=len(posts),
            delta=min(till_update, till_max_post_time)
        )
        new_post_count, new_img_count = 0, 0
        for post, timestamp in zip(posts, post_timestamps):
            post = self.filter_dublicates(post)
            if len(post.media_urls) == 0:
                continue
            self.post_schedule.add((
                timestamp,
                post
            ))
            new_post_count += 1
            new_img_count += len(post.media_urls)
            logger.info(f"Post {post} scheduled at {timestamp.strftime(self.time_format)}")
        logger.info(f"Scheduled {new_post_count} new posts with {new_img_count} images in total")
        self.__save_schedule_data()

    def filter_dublicates(self, post: Post) -> Post:
        dublicates = []
        new_hashes: List[Tuple[str, str]] = []
        # calculating hashes and checking if exists
        for url in post.media_urls:
            stripped_url = strip_args_from_url(url)
            if not stripped_url.endswith(self.dub_checker.allowed_formats):
                continue
            photo_hash = self.dub_checker.get_hash_from_url(url)
            if self.dub_checker.hash_exists(photo_hash):
                logger.info(f"Got dublicate. Hash: {photo_hash}; Url: {url}")
                dublicates.append(url)
            else:
                logger.info(f"Not a dublicate. Hash: {photo_hash}; Url: {url}")
                new_hashes.append((url, photo_hash))
        # adding new hashes to the db
        for url, photo_hash in new_hashes:
            self.dub_checker.add_hash(photo_hash, url)
        # appending filtered posts
        if len(dublicates) == 0:
            return post
        else:
            return Post(
                media_urls=tuple(url for url in post.media_urls if not url in dublicates),
                author_name=post.author_name,
                source_link=post.source_link,
                tags=post.tags
            )
        
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
        logger.debug(f"Saved {len(schedule_list)} posts to {self.__schedule_file}")

    def __repr__(self) -> str:
        scheduled_posts = [(t.strftime(self.time_format), str(p)) for (t, p) in self.post_schedule]
        scheduled_posts.sort(key=lambda x: x[0])
        scheduled_posts = [f"({t}, {p})" for (t, p) in scheduled_posts]
        update_time = [x.strftime(self.time_format) for x in self.__update_time]
        return "Update time:\n" + \
               pformat(update_time) + '\n' + \
               "Scheduled posts:\n" + \
               '\n'.join([x for x in scheduled_posts])
