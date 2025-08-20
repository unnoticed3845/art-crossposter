from dotenv import load_dotenv, find_dotenv
from secrets import token_hex
from time import time, sleep
from typing import Iterable
from functools import wraps
from pathlib import Path
import urllib.parse as url_parse
import requests
import logging
import os
import re

logger = logging.getLogger("RequestUtils")

################
#     INIT     #
################

load_dotenv(find_dotenv())
# USE_PROXY
USE_PROXY = os.getenv('USE_PROXY', '')
if not re.match(r'(\d{1,3}\.){3}\d{1,3}:\d{1,6}', USE_PROXY):
    logger.info(f"USE_PROXY={USE_PROXY} which is an invalid proxy. No proxy will be used.")
    USE_PROXY = None
else:
    logger.info(f"{USE_PROXY} proxy will be used")
# REQUEST_DELAY
REQUEST_DELAY = os.getenv('REQUEST_DELAY', '1')
if not REQUEST_DELAY.isdigit():
    REQUEST_DELAY = 1
else:
    REQUEST_DELAY = float(REQUEST_DELAY)
logger.info(f"REQUEST_DELAY={REQUEST_DELAY}")
# MAX_REQUEST_RETRIES
MAX_REQUEST_RETRIES = os.getenv('MAX_REQUEST_RETRIES', '5')
if not MAX_REQUEST_RETRIES.isdigit():
    MAX_REQUEST_RETRIES = 5
else:
    MAX_REQUEST_RETRIES = int(MAX_REQUEST_RETRIES)
logger.info(f"MAX_REQUEST_RETRIES={MAX_REQUEST_RETRIES}")

last_request = time()
headers = {
    'User-Agent': "python-requests",
    'Accept': 'text/html',
}

################
#  DECORATORS  #
################

def delayed(f):
    """Halts request until delay has passed globaly. NOT MULTITHREAD SAFE"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        global last_request
        now = time()
        if now - last_request < REQUEST_DELAY:
            to_sleep = REQUEST_DELAY - now + last_request
            logger.debug(f"Sleeping for {to_sleep:.2f} sec")
            sleep(to_sleep)
        ret = f(*args, **kwargs)
        last_request = time()
        return ret
    return wrapper

def retry(times, exceptions):
    """
    Credit: https://stackoverflow.com/questions/50246304/using-python-decorators-to-retry-request
    """
    def decorator(func):
        @wraps(func)
        def newfn(*args, **kwargs):
            attempt = 0
            while attempt < times:
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    logger.error(
                        'Exception thrown when attempting to run %s, attempt '
                        '%d of %d' % (func, attempt, times)
                    )
                    attempt += 1
                    sleep(10)
            return func(*args, **kwargs)
        return newfn
    return decorator

#################
#     UTILS     #
#################

def add_query_arg_to_url(url: str, args: dict) -> str:
    url_parts = url_parse.urlparse(url)
    query = url_parse.parse_qs(url_parts.query, keep_blank_values=True)
    query.update(args)
    return url_parts._replace(query=url_parse.urlencode(query, doseq=True)).geturl()

def strip_args_from_url(url: str) -> str:
    return url_parse.urljoin(url, url_parse.urlparse(url).path)

################
#   REQUESTS   #
################

@retry(MAX_REQUEST_RETRIES, requests.exceptions.ConnectionError)
@delayed
def get_html(url: str) -> str:
    logger.info(f"Getting {url}. Proxy: {USE_PROXY}")
    if USE_PROXY:
        r = requests.get(url, proxies={'https':USE_PROXY}, headers=headers)
    else:
        r = requests.get(url, headers=headers)
    return r.text

@retry(MAX_REQUEST_RETRIES, requests.exceptions.ConnectionError)
@delayed
def download_photo(photo_url: str, save_path: Path) -> None:   
    logger.debug(f"Dowloading {photo_url}. Proxy: {USE_PROXY}")
    if USE_PROXY:
        r = requests.get(photo_url, proxies={'https':USE_PROXY}, headers=headers)
    else:
        r = requests.get(photo_url, headers=headers)
    if not r.ok:
        raise ValueError(f"Cant download photo. code {r.status_code}; url {photo_url}")
    with open(save_path, 'wb') as handler:
        handler.write(r.content)
