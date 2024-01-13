from typing import List, Union, Generator, Tuple
from collections import OrderedDict
from functools import lru_cache
from bs4 import BeautifulSoup
from json import load, dump
from random import sample
from pathlib import Path
import urllib.parse as url_parse
import logging
import re

from src.request_utils import get_html
from . import ArtworkParser, Post

logger = logging.getLogger("DanbooruParser")

class DanbooruParser(ArtworkParser):
    __data_file = Path(__file__).parent.joinpath("data/data.json")
    url = "https://danbooru.donmai.us"
    search_url = "https://danbooru.donmai.us/posts"

    def __init__(
        self, 
        tags: Union[List[str], None] = None,
        blacklist_tags: Union[List[str], None] = None,
    ) -> None:
        self.tags = tags if tags else []
        self.blacklist_tags = set(blacklist_tags) if blacklist_tags else set()
        self.file_data = self.__load_file_data()
    
    def scrape_posts(
        self,
        max_pages: int = 3
    ) -> Generator[Post, None, None]:
        # gathering new post urls
        new_posts_urls = self.gather_latest_posts_urls(
            max_pages=max_pages,
            min_post_id=self.file_data['last_post_id']
        )
        # we also sort posts by ids so all urls are chrolonogical
        new_posts_urls.sort(key=self.id_from_url)
        # parsing post urls
        posts: OrderedDict[int, List[Post]] = OrderedDict()
        for post_url in new_posts_urls:
            post, parent_id = self.parse_post_page(post_url)
            if self.blacklist_tags.intersection(post.tags):
                continue
            if parent_id in posts: posts[parent_id].append(post)
            else: posts[parent_id] = [post]
        # merging sibling posts
        merged_posts = [self.merge_posts(posts[p_id]) for p_id in posts.keys()]
        # updating max met post id
        if new_posts_urls:
            max_post_id = max(map(self.id_from_url, new_posts_urls))
            if max_post_id > self.file_data['last_post_id']:
                self.file_data['last_post_id'] = max_post_id
                self.__write_file_data()
        # parser interface requires the parser to be a generator
        for post in merged_posts:
            yield post

    @staticmethod
    def merge_posts(posts: List[Post]) -> Post:
        # max 10 images per post. Telegram limitation
        siblings = posts[:10]
        return Post(
            media_urls=tuple(p.media_urls[0] for p in siblings),
            author_name=siblings[0].author_name,
            source_link=siblings[0].source_link,
            # we say that post's tags are tags that are present in ALL siblings
            tags=tuple(set.intersection(*[set(p.tags) for p in siblings]))
        )

    def gather_latest_posts_urls(
        self,
        max_pages: int = 3,
        min_post_id: int = -1
    ) -> List[str]:
        new_posts_urls = []
        for tag in self.tags:
            posts_urls = self.gather_latest_posts_urls_by_tags(
                tags=tag,
                max_page=max_pages,
                min_post_id=min_post_id
            )
            for url in posts_urls:
                if not url in new_posts_urls:
                    new_posts_urls.append(url)
        return new_posts_urls

    @staticmethod
    def gather_latest_posts_urls_by_tags(
        tags: str,
        max_page: int = 3,
        min_post_id: int = -1
    ) -> List[str]:
        new_posts_urls = []
        for page in range(1, max_page + 1):
            url = DanbooruParser.add_query_arg_to_url(
                DanbooruParser.search_url, 
                {"page": page, "tags": tags}
            )
            posts_urls = DanbooruParser.parse_search_page(url)
            met_old_post = False
            for url in posts_urls:
                if DanbooruParser.id_from_url(url) <= min_post_id:
                    met_old_post = True
                else:
                    new_posts_urls.append(url)
            if met_old_post:
                break
        return new_posts_urls

    @staticmethod
    def parse_search_page(url: str) -> List[str]:
        html = get_html(url)
        bs = BeautifulSoup(html, features="html.parser")
        urls = bs.find_all("a", class_="post-preview-link")
        urls = map(lambda x: DanbooruParser.url + x.get('href'), urls)
        urls = map(DanbooruParser.strip_args_from_url, urls)
        return list(urls)

    @staticmethod
    @lru_cache(maxsize=200)
    def parse_post_page(url: str) -> Tuple[Post, Union[int, None]]:
        html = get_html(url)
        bs = BeautifulSoup(html, features="html.parser")
        return Post(
            media_urls = tuple([DanbooruParser.__retrieve_media_url(bs)]),
            author_name = DanbooruParser.__retrieve_author_name(bs),
            source_link = DanbooruParser.__retrieve_source_link(bs),
            tags = tuple(DanbooruParser.__retrieve_tags(bs))
        ), DanbooruParser.__retrieve_parent_id(bs)

    @staticmethod
    def __retrieve_parent_id(bs: BeautifulSoup) -> int:
        body = bs.find('body')
        # if its a child post (has a parent)
        parent_id = body.get('data-post-parent-id')
        if parent_id != 'null':
            return parent_id
        # else if parent_id is null
        # if it has no parent and it is not a parent
        return body.get('data-post-id')

    @staticmethod
    def __retrieve_media_url(bs: BeautifulSoup) -> Union[str, None]:
        img_url = bs.find("img", id="image")
        if img_url: return img_url.get('src')
        vid_url = bs.find("video", id="image")
        if vid_url: return vid_url.get('src')
        return None
    
    @staticmethod
    def __retrieve_author_name(bs: BeautifulSoup) -> Union[str, None]:
        ul = bs.find('ul', class_='artist-tag-list')
        if ul is None: return None
        name = ul.find('a', class_='search-tag').text
        return name.replace(' ', '_')
    
    @staticmethod
    def __retrieve_source_link(bs: BeautifulSoup) -> Union[str, None]:
        li = bs.find('li', id='post-info-source')
        if li is None: return None
        a = li.find('a')
        if a is None: return None
        return a.get('href')
    
    @staticmethod
    def __retrieve_tags(bs: BeautifulSoup) -> List[str]:
        tags = bs.find_all('a', class_='search-tag')
        return [ x.text for x in tags ]
    
    @staticmethod
    def strip_args_from_url(url: str) -> str:
        return url_parse.urljoin(url, url_parse.urlparse(url).path)

    @staticmethod
    def id_from_url(url: str) -> int:
        """Retrieve post id from it's url.

        Args:
            url (str): post's url

        Returns:
            int: id of the post
        """
        post_id = re.search(r'/(\d{1,10})\??', url).groups()[0]
        return int(post_id)
    
    @staticmethod 
    def add_query_arg_to_url(url: str, args: dict) -> str:
        url_parts = url_parse.urlparse(url)
        query = url_parse.parse_qs(url_parts.query, keep_blank_values=True)
        query.update(args)
        return url_parts._replace(query=url_parse.urlencode(query, doseq=True)).geturl()

    @classmethod
    def __check_data_file(cls) -> None:
        if not cls.__data_file.is_file():
            cls.__data_file.parent.mkdir(exist_ok=True, parents=True)
            cls.__data_file.touch()
            with open(cls.__data_file, 'w', encoding='utf-8') as f:
                dump({
                    'last_post_id': -1
                }, f, indent=4)

    @classmethod
    def __load_file_data(cls) -> dict:
        cls.__check_data_file()
        with open(cls.__data_file, 'r', encoding='utf-8') as f:
            data = load(f)
        return data
        
    def __write_file_data(self) -> None:
        self.__check_data_file()
        with open(self.__data_file, 'w', encoding='utf-8') as f:
            dump(self.file_data, f, indent=4)