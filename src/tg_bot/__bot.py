from requests.exceptions import ConnectionError
from dotenv import load_dotenv, find_dotenv
from random import randint
from typing import List, Union, Tuple
from time import sleep
from pytgbot.api_types.sendable.input_media import InputMediaPhoto, InputMediaVideo, InputMedia
import logging
import pytgbot
import os

from src.request_utils import add_query_arg_to_url, strip_args_from_url

logger = logging.getLogger("TelegramBot")

log_file = "log/bot.log"
os.makedirs(os.path.dirname(log_file), exist_ok=True)
fh = logging.FileHandler(log_file)
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)

load_dotenv(find_dotenv('secret.env', raise_error_if_not_found=True))

__bot = pytgbot.Bot(os.getenv('TG_TOKEN'))
__channel_id = os.getenv('CHANNEL_ID')

photo_formats = (".jpg", ".jpeg", ".png")
video_formats = (".mp4", ".mkv", ".gif")

def __send_photo(photo_url: str, caption: str) -> None:
    __bot.send_photo(
        __channel_id,
        photo=photo_url,
        caption=caption,
        parse_mode="MarkdownV2"
    )

def __send_video(video_url: str, caption: str) -> None:
    __bot.send_video(
        __channel_id,
        video=video_url,
        caption=caption,
        parse_mode="MarkdownV2"
    )

def __add_random_argument(url: str) -> str:
    # this ?random argument is needed bc of this:
    # https://stackoverflow.com/questions/49645510/telegram-bot-send-photo-by-url-returns-bad-request-wrong-file-identifier-http/62672868#62672868
    return add_query_arg_to_url(url, {'random': randint(0, 10_000)})

def send_single_media(media_url: str, caption: str, max_retries: int = 5) -> None:
    if media_url.endswith(photo_formats): handler = __send_photo
    elif media_url.endswith(video_formats): handler = __send_video
    else: 
        logger.error(f"send_single_media unsupported format: {media_url}")
        return
    
    for i in range(max_retries):
        try:
            handler(
                __add_random_argument(media_url),
                caption=caption
            )
            break
        except (pytgbot.exceptions.TgApiServerException, ConnectionError) as e:
            if i + 1 == max_retries:
                logger.error(f"send_single_media Exception: {e}\nmedia_url:{media_url}")
            else:
                sleep(2)

def __send_media_group(media_urls: List[str], caption: str, max_retries: int = 5) -> None:
    # converting everything in InputMedia objects since
    # it is only possible to set a caption through it with sendMediaGroup
    converted_media: List[InputMedia] = []
    successful_urls: List[str] = []
    for media_url in media_urls:
        if strip_args_from_url(media_url).endswith(photo_formats):
            converted_media.append(InputMediaPhoto(media_url))
            successful_urls.append(media_url)
        elif strip_args_from_url(media_url).endswith(video_formats):
            converted_media.append(InputMediaVideo(media_url))
            successful_urls.append(media_url)
        else:
            logger.error(f"__send_media_group unsupported format: {media_url}")     
    # checking if we have enough valid media
    if len(converted_media) == 0:
        logger.error(f"__send_media_group no valid media to send. Urls: {media_urls}")
        return
    elif len(converted_media) == 1:
        logger.error(f"__send_media_group has a single valid media to send. Urls: {media_urls}. Trying to send as a single media...")
        return send_single_media(successful_urls[0], caption, max_retries)
    # setting the caption
    converted_media[0].caption = caption
    converted_media[0].parse_mode = "MarkdownV2"

    __bot.send_media_group(
        __channel_id,
        media=converted_media
    )

def send_several_media(media: List[str], caption: str, max_retries: int = 5) -> None:
    for i in range(max_retries):
        try:
            __send_media_group(
                [ __add_random_argument(url) for url in media ],
                caption=caption,
                max_retries=max_retries
            )
            break
        except (pytgbot.exceptions.TgApiServerException, ConnectionError) as e:
            if i + 1 == max_retries:
                logger.error(f"send_several_media Exception: {e}\nmedia:{media}")
            else:
                sleep(2)

def send_media(media: Union[str, Tuple[str], List[str]], caption: str, max_retries: int = 5) -> None:
    if isinstance(media, (tuple, list)) and len(media) == 1:
        media = media[0]

    if isinstance(media, str):
        return send_single_media(media_url=media, 
                                 caption=caption, 
                                 max_retries=max_retries)
    elif isinstance(media, (tuple, list)):
        if not all(isinstance(x, str) for x in media):
            logger.error(f"All medias must be str. Got: {', '.join([f'{x} ({type(x)})' for x in media])}")
            return
        if not isinstance(media, list): media = list(media)
        return send_several_media(media=media,
                                  caption=caption,
                                  max_retries=max_retries)
    else:
        raise ValueError(f"List or str expected. Got {type(media)} ({media})")
