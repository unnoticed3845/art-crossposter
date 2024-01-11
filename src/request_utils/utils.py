from dotenv import load_dotenv, find_dotenv
from time import time, sleep
import urllib.parse as url_parse
import requests
import logging
import os
import re

logger = logging.getLogger(__name__)

load_dotenv(find_dotenv())
# USE_PROXY
USE_PROXY = os.getenv('USE_PROXY')
if not re.match(r'(\d{1,3}\.){3}\d{1,3}:\d{1,6}', USE_PROXY):
    logger.info(f"USE_PROXY={USE_PROXY} which is an invalid proxy. No proxy will be used.")
    USE_PROXY = None
else:
    logger.info(f"{USE_PROXY} proxy will be used")
# REQUEST_DELAY
REQUEST_DELAY = os.getenv('REQUEST_DELAY', 1)
if not REQUEST_DELAY.isdigit():
    REQUEST_DELAY = 1
else:
    REQUEST_DELAY = float(REQUEST_DELAY)
logger.info(f"REQUEST_DELAY={REQUEST_DELAY}")
# MAX_PROXY_RETRIES
MAX_PROXY_RETRIES = os.getenv('MAX_PROXY_RETRIES', 5)
if not MAX_PROXY_RETRIES.isdigit():
    MAX_PROXY_RETRIES = 5
else:
    MAX_PROXY_RETRIES = int(MAX_PROXY_RETRIES)
logger.info(f"MAX_PROXY_RETRIES={MAX_PROXY_RETRIES}")

last_request = time()
headers = {
    'User-Agent': "python-requests/2.31.0; Please contact me if you want me to ratelimit my parser; telegram: https://t.me/affenmilchmann",
    'Accept': 'text/html',
}

def add_query_arg_to_url(url: str, args: dict) -> str:
    url_parts = url_parse.urlparse(url)
    query = url_parse.parse_qs(url_parts.query, keep_blank_values=True)
    query.update(args)
    return url_parts._replace(query=url_parse.urlencode(query, doseq=True)).geturl()

def strip_args_from_url(url: str) -> str:
    return url_parse.urljoin(url, url_parse.urlparse(url).path)

def get_html(url: str, __depth = 0):
    global last_request
    now = time()
    if now - last_request < REQUEST_DELAY:
        logger.debug(f"Sleeping for {REQUEST_DELAY - now + last_request:.2f} sec")
        sleep(REQUEST_DELAY - now + last_request)
    logger.info(f"Getting {url}. Proxy: {USE_PROXY}")
    try:
        if USE_PROXY:
            r = requests.get(url, proxies={'https':USE_PROXY}, headers=headers)
        else:
            r = requests.get(url, headers=headers)
    except requests.exceptions.ConnectionError as e:
        logger.debug(f"Got ConnectionError. {MAX_PROXY_RETRIES - __depth} more tries left")
        if __depth < MAX_PROXY_RETRIES:
            sleep(10)
            return get_html(url, __depth + 1)
        raise

    last_request = time()
    return r.text
