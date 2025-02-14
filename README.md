# Artwork telegram crossposter
This crossposter parses art from various platforms (rn only from danbooru imageboard) and posts it to specified telegram channel. Working SFW example is [here](https://t.me/signalisarts) (it crossposts images related to the videogame 'Signalis').

## Basic usage
1. Clone the repo:
    
    `git clone https://github.com/unnoticed3845/art-crossposter`
2. Create `secret.env` file in the repo's root with the following contents:
    ```env
    TG_TOKEN=<your telegram bot's token>
    CHANNEL_ID=<your telegram channel's integer id>
    ```
3. Install dependencies: 

    `pip3 install -r requirements.txt`

4. (optional) run parser tests:

    `python3 -m unittest discover tests`

5. Run:

    `python3 main.py`

## Configuration
### Artwork tags
Parsers are configurable by tags that they parse. Existing Danbooru parser provides configuration by target tags, blacklisted tags and tags exceptions that allow some blacklisted tags. Each parser is supposed to be configurated separately, because of the fact that each platform has different tag names and tag system in general.

More platform parsers are planned to be added like Pixiv, X(Twitter), Gelbooru, etc.

To configure danbooru parser edit [config/danbooru_conf.json](./config/danbooru_conf.json) file.

### Parse schedule
`PostManager` class object orchestrates the whole crossposter. It calls parsers when needed, schedules posts, calls tg_bot module to post posts, calls dublicate_checker to check if image has already been posted before.

To configure danbooru parser edit [config/scheduler_conf.json](./config/scheduler_conf.json) file.

- Daily parse time is configured in `update_timestamps`. It is a `List[str]` with 24h formatted timestamps. Example: `['07:00', '23:30']`, in this case postmanager will call every parser twice a day at 7:00 and 23:30. 
- **First note!** Parsers are not multithreaded yet (they will be once we make at least two parsers).
- **Second note!** Please do not parse too frequently, be polite to the platform servers :), 1-2 times per day is more than enough imho.

### Http(s) request ratelimiting
In [.env](./.env) file you can configure 3 variables:
- USE_PROXY - proxy url or any non-valid value to disable proxy.
- REQUEST_DELAY - http(s) requests delay in seconds. All requests will be sent not sooner than REQUEST_DELAY seconds after the previous request. 

    **Note!** Please, be kind to platform servers and do not set low REQUEST_DELAY values. No need to spam with requests when parsing occurs happens couple times a day
- MAX_REQUEST_RETRIES - max request retries before throwing an exception and stopping the Crossposter

## Creating new parsers
To create a new parser: 
1. Inherit it from [`BaseParser`](./src/parsers/parser.py) (place your parser in src/parsers)
2. Implement `scrape_posts` generator method there with matching return typing
3. In [main.py](./main.py) create an object of your parser class and add it to post manager with `post_manager.add_parser(parser_obj)`
