# Keypirinha launcher (keypirinha.com)

from datetime import datetime
import keypirinha as kp
import keypirinha_util as kpu
import keypirinha_net as kpnet
import json
import urllib
import os
import subprocess
import html

class reddit(kp.Plugin):
    ITEMCAT_RESULT = kp.ItemCategory.USER_BASE + 1

    ACTION_OPEN_URL = "open_url"
    ACTION_COPY_URL = "copy_url"

    TARGET_POPULAR = "top_popular"
    TARGET_FAVORITE = "favorite"
    TARGET_SEARCH_SUBREDDIT = "search_subreddit"
    TARGET_POPULAR_IN_SUBREDDIT = "popular_in_subreddit"

    URL_POPULAR_SUBREDDITS = 'https://www.reddit.com/subreddits/popular.json'
    URL_SEARCH_SUBREDDITS = 'https://www.reddit.com/subreddits/search.json'
    URL_POPULAR_IN = 'https://www.reddit.com/r/{name}/{listing}.json'

    DEFAULT_SETTING_FAST_LOAD = False
    USER_SETTING_FAST_LOAD = DEFAULT_SETTING_FAST_LOAD

    DEFAULT_SETTING_NSWF = False
    USER_SETTING_NSWF = DEFAULT_SETTING_NSWF

    DEFAULT_SETTING_LISTING = "hot"
    USER_SETTING_LISTING = DEFAULT_SETTING_LISTING
    LISTING_SETTINGS = ["hot", "best", "new", "rising"]

    last_update = None

    def __init__(self):
        super().__init__()

    def _load_settings(self):
        settings = self.load_settings()
        self.USER_SETTING_FAST_LOAD = settings.get_bool(
            "fast_load", "main",
            self.DEFAULT_SETTING_FAST_LOAD
        )

        self.USER_SETTING_NSWF = settings.get_bool(
            "show_nswf", "main",
            self.DEFAULT_SETTING_NSWF
        )

        self.USER_SETTING_LISTING = settings.get_enum("listing", "main", fallback=self.DEFAULT_SETTING_LISTING, enum=self.LISTING_SETTINGS).lower()
        if (self.USER_SETTING_LISTING not in self.LISTING_SETTINGS):
            self.USER_SETTING_LISTING = self.DEFAULT_SETTING_LISTING

        self.info("Fast Load: " + str(self.USER_SETTING_FAST_LOAD))
        self.info("Show NSWF: " + str(self.USER_SETTING_NSWF))
        self.info("Listing Setting: " + str(self.USER_SETTING_LISTING))
        pass

    def _load_favorites(self):
        items = []
        sections = self.load_settings().sections()
        for config_section in sections:
            if config_section.startswith("#") or not config_section.lower().startswith("r/"):
                continue

            subreddit_name = config_section[len("r/"):]
            self.info("Favorite added: " + subreddit_name)
            data = self.reddit_request(self.URL_SEARCH_SUBREDDITS, subreddit_name, 1)
            cur = data['data']['children'][0]['data']
            icon = self.subreddit_icon_or_default(cur, True)
            items.append(self.create_item(
                category=kp.ItemCategory.KEYWORD,
                label="r/{}".format(subreddit_name),
                short_desc=html.unescape(cur['title']),
                target=self.TARGET_FAVORITE + "/"+ subreddit_name,
                icon_handle=icon,
                args_hint=kp.ItemArgsHint.REQUIRED,
                hit_hint=kp.ItemHitHint.NOARGS))
        return items

    def _popular_suggestions(self):
        suggestions = []
        data = self.reddit_request(self.URL_POPULAR_SUBREDDITS, '', 25)
        elements = data['data']['children']
        for e in range(len(elements)):
            cur = elements[e]['data']
            icon = self.subreddit_icon_or_default(cur, True)
            suggestions.append(self.create_item(
                    category=self.ITEMCAT_RESULT,
                    label=cur['display_name_prefixed'],
                    short_desc=html.unescape(cur['title']),
                    target='https://www.reddit.com'+(cur['url']),
                    icon_handle=icon,
                    args_hint=kp.ItemArgsHint.FORBIDDEN,
                    hit_hint=kp.ItemHitHint.IGNORE))
        self.local_popular = suggestions
        self.last_update = datetime.now()
        self.info("Popular loaded")
        pass

    def on_start(self):
        self.logo = 'res://%s/%s'%(self.package_full_name(),'reddit.png')
        self.CACHE = "cache://" + self.package_full_name()
        self.PREVIEW_PATH = self.get_package_cache_path(create=True)
        self.opener = kpnet.build_urllib_opener()

        actions = [
            self.create_action(
                name=self.ACTION_OPEN_URL,
                label="Read",
                short_desc="Opens the subreddit in a browser"
            ),
            self.create_action(
                name=self.ACTION_COPY_URL,
                label="Copy",
                short_desc="Copy the URL of subreddit into clipboard"
            )]
        self.set_actions(self.ITEMCAT_RESULT, actions)
        self._popular_suggestions()
        pass

    def on_catalog(self):
        catalog = []
        self._load_settings()
        self._popular_suggestions()
        self.set_catalog(catalog)
        catalog.append(self.create_item(
            category=kp.ItemCategory.KEYWORD,
            label="r/Popular",
            short_desc="Show list of popular subreddits",
            target=self.TARGET_POPULAR,
            icon_handle=self.load_icon(self.logo),
            args_hint=kp.ItemArgsHint.REQUIRED,
            hit_hint=kp.ItemHitHint.NOARGS))

        for favorite in self._load_favorites():
            catalog.append(favorite)

        catalog.append(self.create_item(
            category=kp.ItemCategory.KEYWORD,
            label="r/",
            short_desc="Search subreddits",
            target=self.TARGET_SEARCH_SUBREDDIT,
            icon_handle=self.load_icon(self.logo),
            args_hint=kp.ItemArgsHint.REQUIRED,
            hit_hint=kp.ItemHitHint.NOARGS))

        self.set_catalog(catalog)
        pass

    def on_suggest(self, user_input, items_chain):
        time_diff = datetime.now() - self.last_update
        if (time_diff.total_seconds() >= 86400):
            self._popular_suggestions()

        if not items_chain or items_chain[-1].category() != kp.ItemCategory.KEYWORD:
            return

        if self.should_terminate(0.25):
            return

        if (items_chain[-1].target() == self.TARGET_POPULAR):
            self.set_suggestions(self.local_popular, kp.Match.ANY, kp.Sort.NONE)
        elif (self.TARGET_FAVORITE in items_chain[-1].target()):
            suggestions = []
            name = items_chain[-1].target()[len(self.TARGET_FAVORITE + "/"):]
            data = self.reddit_request(self.URL_POPULAR_IN.format(name = name, listing = self.USER_SETTING_LISTING), '', 25)
            elements = data['data']['children']

            for e in range(len(elements)):
                cur = elements[e]['data']
                suggestions.append(self.create_item(
                        category=self.ITEMCAT_RESULT,
                        label=cur['title'],
                        short_desc=html.unescape(cur['selftext']),
                        icon_handle=self.subreddit_icon_by_name(name),
                        target='https://www.reddit.com'+(cur['permalink']),
                        args_hint=kp.ItemArgsHint.FORBIDDEN,
                        hit_hint=kp.ItemHitHint.IGNORE))
            
            self.set_suggestions(suggestions, kp.Match.ANY, kp.Sort.NONE)
        else: #searching for subreddits
            if (len(user_input) == 0):
                return

            suggestions = []
            data = self.reddit_request(self.URL_SEARCH_SUBREDDITS, user_input, 25)
            elements = data['data']['children']
            
            for e in range(len(elements)):
                cur = elements[e]['data']
                icon = self.subreddit_icon_or_default(cur, False)
                suggestions.append(self.create_item(
                    category=self.ITEMCAT_RESULT,
                    label=cur['display_name_prefixed'],
                    short_desc=html.unescape(cur['title']),
                    target='https://www.reddit.com'+(cur['url']),
                    icon_handle=icon,
                    args_hint=kp.ItemArgsHint.FORBIDDEN,
                    hit_hint=kp.ItemHitHint.IGNORE))
                
            self.set_suggestions(suggestions, kp.Match.ANY, kp.Sort.NONE)
        pass

    def on_execute(self, item, action):
        if (action is None or (action is not None and action.name() == self.ACTION_OPEN_URL)):
            kpu.web_browser_command(
                url = item.target(),
                execute = True
            )
        else:
            kpu.set_clipboard(item.target())
        pass

    def reddit_request(self, url, input, limit):
        request = urllib.request.Request(url)
        if (input is not None and input != ''):
            params = urllib.parse.urlencode({
                "q": input,
                "limit": limit,
                "include_over_18": self.USER_SETTING_NSWF
            })
            request = urllib.request.Request("{}?{}".format(url, params))

        request.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(request) as response:
            data = json.loads(response.read())

        return data

    def subreddit_icon_or_default(self, cur, favorites_list):
        if ((favorites_list or not self.USER_SETTING_FAST_LOAD) and cur['icon_img'] is not None and cur['icon_img'] != ''):
            file_name = "{}.jpg".format(cur['display_name'])
            icon_source = "{}/{}".format(self.CACHE, file_name)
            cache_icon = os.path.join(self.PREVIEW_PATH, file_name)
            if (not os.path.exists(cache_icon)):
                with self.opener.open(cur['icon_img']) as resp, open(cache_icon, 'w+b') as fp:
                    fp.write(resp.read())

            return self.load_icon(icon_source)

        return self.load_icon(self.logo)

    def subreddit_icon_by_name(self, name):
        file_name = "{}.jpg".format(name)
        icon_source = "{}/{}".format(self.CACHE, file_name)
        cache_icon = os.path.join(self.PREVIEW_PATH, file_name)
        if (not os.path.exists(cache_icon)):
            return self.load_icon(self.logo)
        return self.load_icon(icon_source)