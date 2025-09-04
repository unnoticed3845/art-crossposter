from typing import (
    List, Union, Generator, 
    Tuple, Set, Iterable
)
from collections import OrderedDict
from functools import lru_cache
from bs4 import BeautifulSoup
from json import load, dump
from pathlib import Path
import urllib.parse as url_parse
import logging
import re

from src.request_utils import get_html
from . import Post, BaseParser

logger = logging.getLogger("DanbooruParser")

class BlacklistedTag:
    def __init__(self, tag: str, exception_tags: Iterable[str] = None) -> None:
        if not isinstance(tag, str):
            raise ValueError(f"tag must be str, got {tag}({type(tag)})")
        self.tag = tag
        self.exception_tags = frozenset(exception_tags) if exception_tags else frozenset()

    @classmethod
    def fromstr(cls, tag: str):
        return cls(tag=tag)
    @classmethod
    def fromjsonlist(cls, json_list: list):
        return cls(tag=json_list[0], exception_tags=json_list[1])
    @classmethod
    def fromauto(cls, tag: list | str):
        if isinstance(tag, str):
            return cls.fromstr(tag)
        if isinstance(tag, list):
            return cls.fromjsonlist(tag)
        return NotImplemented

    def check(self, tags: Set[str]) -> bool:
        if not self.tag in tags: return True
        exception_tag_present = bool(tags.intersection(self.exception_tags))
        return exception_tag_present
    
    def __eq__(self, __value: str) -> bool:
        if isinstance(__value, str):
            return self.tag == __value
        return NotImplemented
    def __hash__(self) -> int:
        return hash(self.tag)
    def __repr__(self) -> str:
        return str(self)
    def __str__(self) -> str:
        return f"{self.tag}{list(self.exception_tags)}"

class DanbooruParser(BaseParser):
    url = "https://danbooru.donmai.us"
    search_url = "https://danbooru.donmai.us/posts"
    _default_data = {
        'last_post_id': -1
    }

    def __init__(
        self,
        config_file: str = "danbooru_conf.json",
        data_file: str = "danbooru_data.json"
    ) -> None:
        super().__init__(config_file = config_file,
                         data_file = data_file,
                         default_data = self._default_data)
        # max_pages
        self.max_pages = self.config['max_pages']
        if not isinstance(self.max_pages, int) or self.max_pages < 1:
            raise ValueError(f"Invalid max_pages value")
        # tags
        if not 'tags' in self.config:
            raise ValueError(f"Config must contain 'tags' array: {self.config_file_path}")
        if self.config['tags']:
            self.tags = self.config['tags']
        else:
            raise ValueError(f"Config contained no tags: {self.config_file_path}")
        # blacklisted_tags
        if 'blacklisted_tags' in self.config and self.config['blacklisted_tags']:
            self.blacklisted_tags = [BlacklistedTag.fromauto(tag) 
                                    for tag in self.config['blacklisted_tags']]
        else:
            self.blacklisted_tags = []
        logger.debug(self.tags)
        logger.debug(self.blacklisted_tags)
        logger.debug(self.file_data)
        logger.info('Initialization done')
    
    def scrape_posts(
        self, max_posts_total: Union[int, None] = None
    ) -> Generator[Post, None, None]:
        # gathering new post urls
        new_posts_urls = self.gather_latest_posts_urls(
            min_post_id=self.file_data['last_post_id']
        )
        # we also sort posts by ids so all urls are chrolonogical
        new_posts_urls.sort(key=self.id_from_url)
        if isinstance(max_posts_total, int):
            new_posts_urls = new_posts_urls[:max_posts_total]
        logger.info(f"Gathered {len(new_posts_urls)} post urls")
        # parsing post urls
        posts: OrderedDict[int, List[Post]] = OrderedDict()
        for post_url in new_posts_urls:
            post, parent_id = self.parse_post_page(post_url)
            if self.is_post_blacklisted(post):
                logger.info(f"Post is blacklisted: {post}")
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
                self.save_data()
        # parser interface requires the parser to be a generator
        for post in merged_posts:
            # if at least one valid url
            if len([url for url in post.media_urls if url]):
                yield post

    def is_post_blacklisted(self, post: Post) -> bool:
        tags = set(post.tags)
        for bl_tag in self.blacklisted_tags:
            if not bl_tag.check(tags):
                return True
        return False

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
        self, min_post_id: int = -1
    ) -> List[str]:
        new_posts_urls = []
        for tag in self.tags:
            posts_urls = self.gather_latest_posts_urls_by_tags(
                tags=tag,
                min_post_id=min_post_id
            )
            for url in posts_urls:
                if not url in new_posts_urls:
                    new_posts_urls.append(url)
        return new_posts_urls

    def gather_latest_posts_urls_by_tags(
        self, tags: str, min_post_id: int = -1
    ) -> List[str]:
        new_posts_urls = []
        for page in range(1, self.max_pages + 1):
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
        def has_tag_name(bs_tag):
            return bs_tag.name == 'li' and bs_tag.has_attr('data-tag-name')
        tag_box = bs.find('section', id='tag-list')
        tags = tag_box.find_all(has_tag_name)
        
        return [ x['data-tag-name'] for x in tags ]
    
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
