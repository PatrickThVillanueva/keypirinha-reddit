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
    """
    View popular subreddits, or search for particular subreddits or users.
    """
    
    ITEMCAT_RESULT = kp.ItemCategory.USER_BASE + 1
    # ITEMCAT_OPEN_BROWSER = kp.ItemCategory.USER_BASE + 2

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

    DEFAULT_SETTING_LISTING = "hot"
    USER_SETTING_LISTING = DEFAULT_SETTING_LISTING
    LISTING_SETTINGS = ["hot", "best", "new", "rising"]

    def __init__(self):
        super().__init__()

    def _load_settings(self):
        settings = self.load_settings()
        self.USER_SETTING_FAST_LOAD = settings.get_bool(
            "fast_load", "main",
            self.DEFAULT_SETTING_FAST_LOAD
        )

        self.USER_SETTING_LISTING = settings.get(
            "listing", "main",
            self.DEFAULT_SETTING_LISTING
        ).lower()

        if (self.USER_SETTING_LISTING not in LISTING_SETTINGS):
            self.USER_SETTING_LISTING = self.DEFAULT_SETTING_LISTING
        pass

    def _load_favorites(self):
        items = []
        opener = kpnet.build_urllib_opener()
        sections = self.load_settings().sections()
        for config_section in sections:
            if not config_section.lower().startswith("r/"):
                continue

            subreddit_name = config_section[len("r/"):]
            params = urllib.parse.urlencode({
                "q": subreddit_name,
                "limit": 1,
                "include_over_18": True
            })
            request = urllib.request.Request("{}?{}".format(self.URL_SEARCH_SUBREDDITS, params))
            request.add_header("User-Agent", "Mozilla/5.0")
            with urllib.request.urlopen(request) as response:
                data = json.loads(response.read())
            cur = data['data']['children'][0]['data']
            if (cur['icon_img'] is not None and cur['icon_img'] != ''):
                file_name = "{}{}.jpg".format(subreddit_name, cur['display_name'])
                icon_source = "{}/{}".format(self.CACHE, file_name)
                cache_icon = os.path.join(self.PREVIEW_PATH, file_name)
                with opener.open(cur['icon_img']) as resp, open(cache_icon, 'w+b') as fp:
                    fp.write(resp.read())

                items.append(self.create_item(
                    category=kp.ItemCategory.KEYWORD,
                    label="r/ {}".format(subreddit_name),
                    short_desc=html.unescape(cur['title']),
                    target=self.TARGET_FAVORITE + "/"+ subreddit_name,
                    icon_handle=self.load_icon(icon_source),
                    args_hint=kp.ItemArgsHint.REQUIRED,
                    hit_hint=kp.ItemHitHint.NOARGS))

            else:
                items.append(self.create_item(
                    category=kp.ItemCategory.KEYWORD,
                    label="r/ {}".format(subreddit_name),
                    short_desc=html.unescape(cur['title']),
                    target=self.TARGET_FAVORITE + "/"+ subreddit_name,
                    icon_handle=self.load_icon(self.logo),
                    args_hint=kp.ItemArgsHint.REQUIRED,
                    hit_hint=kp.ItemHitHint.NOARGS))

        return items

    def _popular_suggestions(self):
        request = urllib.request.Request(self.URL_POPULAR_SUBREDDITS)
        request.add_header("User-Agent", "Mozilla/5.0")
        opener = kpnet.build_urllib_opener()
        with urllib.request.urlopen(request) as response:
            data = json.loads(response.read())

        suggestions = []
        elements = data['data']['children']
        for e in range(len(elements)):
            cur = elements[e]['data']
            if (cur['icon_img'] is not None and cur['icon_img'] != ''):
                file_name = "{}{}.jpg".format(e, cur['display_name'])
                icon_source = "{}/{}".format(self.CACHE, file_name)
                cache_icon = os.path.join(self.PREVIEW_PATH, file_name)
                with opener.open(cur['icon_img']) as resp, open(cache_icon, 'w+b') as fp:
                    fp.write(resp.read())

                suggestions.append(self.create_item(
                        category=self.ITEMCAT_RESULT,
                        label=cur['display_name_prefixed'],
                        short_desc=html.unescape(cur['title']),
                        target='https://www.reddit.com'+(cur['url']),
                        icon_handle=self.load_icon(icon_source),
                        args_hint=kp.ItemArgsHint.FORBIDDEN,
                        hit_hint=kp.ItemHitHint.IGNORE))
            else:
                suggestions.append(self.create_item(
                        category=self.ITEMCAT_RESULT,
                        label=cur['display_name_prefixed'],
                        short_desc=html.unescape(cur['title']),
                        target='https://www.reddit.com'+(cur['url']),
                        icon_handle=self.load_icon(self.logo),
                        args_hint=kp.ItemArgsHint.FORBIDDEN,
                        hit_hint=kp.ItemHitHint.IGNORE))

        self.local_popular = suggestions
        pass

    def on_start(self):
        self.logo = 'res://%s/%s'%(self.package_full_name(),'reddit.png')
        self.CACHE = "cache://" + self.package_full_name()
        self.PREVIEW_PATH = self.get_package_cache_path(create=True)
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
        self._load_settings()
        self._load_favorites()
        pass

    def on_catalog(self):
        settings = self.load_settings()
        favorites = self._load_favorites()
        catalog = []

        catalog.append(self.create_item(
            category=kp.ItemCategory.KEYWORD,
            label="r/ Popular",
            short_desc="Show list of popular subreddits",
            target=self.TARGET_POPULAR,
            icon_handle=self.load_icon(self.logo),
            args_hint=kp.ItemArgsHint.REQUIRED,
            hit_hint=kp.ItemHitHint.NOARGS))

        for favorite in favorites:
            catalog.append(favorite)

        catalog.append(self.create_item(
            category=kp.ItemCategory.KEYWORD,
            label="r/ ",
            short_desc="Search subreddits",
            target=self.TARGET_SEARCH_SUBREDDIT,
            icon_handle=self.load_icon(self.logo),
            args_hint=kp.ItemArgsHint.REQUIRED,
            hit_hint=kp.ItemHitHint.NOARGS))

        self.set_catalog(catalog)
        self._load_settings()
        pass

    def on_suggest(self, user_input, items_chain):
        if not items_chain or items_chain[-1].category() != kp.ItemCategory.KEYWORD:
            return

        if self.should_terminate(0.25):
            return

        if (items_chain[-1].target() == self.TARGET_POPULAR):
            self.set_suggestions(self.local_popular, kp.Match.ANY, kp.Sort.NONE)
        elif (self.TARGET_FAVORITE in items_chain[-1].target()):
            suggestions = []
            name = items_chain[-1].target()[len(self.TARGET_FAVORITE + "/"):]
            request = urllib.request.Request("{}".format(self.URL_POPULAR_IN.format(name = name, listing = self.USER_SETTING_LISTING)))
            request.add_header("User-Agent", "Mozilla/5.0")
            with urllib.request.urlopen(request) as response:
                data = json.loads(response.read())
            elements = data['data']['children']

            for e in range(len(elements)):
                cur = elements[e]['data']
                suggestions.append(self.create_item(
                        category=self.ITEMCAT_RESULT,
                        label=cur['title'],
                        short_desc=html.unescape(cur['selftext']),
                        target=cur['url'],
                        args_hint=kp.ItemArgsHint.FORBIDDEN,
                        hit_hint=kp.ItemHitHint.IGNORE))
            
            self.set_suggestions(suggestions, kp.Match.ANY, kp.Sort.NONE)
        else:
            elements = []
            suggestions = []
            params = urllib.parse.urlencode({
                "q": user_input,
                "limit": 25,
                "include_over_18": True
            })
            request = urllib.request.Request("{}?{}".format(self.URL_SEARCH_SUBREDDITS, params))
            request.add_header("User-Agent", "Mozilla/5.0")
            with urllib.request.urlopen(request) as response:
                data = json.loads(response.read())
            elements = data['data']['children']
            opener = kpnet.build_urllib_opener()

            for e in range(len(elements)):
                cur = elements[e]['data']

                if (not self.USER_SETTING_FAST_LOAD and cur['icon_img'] is not None and cur['icon_img'] != ''):
                    file_name = "{}{}.jpg".format(e, cur['display_name'])
                    icon_source = "{}/{}".format(self.CACHE, file_name)
                    cache_icon = os.path.join(self.PREVIEW_PATH, file_name)

                    if (not os.path.exists(cache_icon)):
                        with opener.open(cur['icon_img']) as resp, open(cache_icon, 'w+b') as fp:
                            fp.write(resp.read())

                    suggestions.append(self.create_item(
                            category=self.ITEMCAT_RESULT,
                            label=cur['display_name_prefixed'],
                            short_desc=html.unescape(cur['title']),
                            target='https://www.reddit.com'+(cur['url']),
                            icon_handle=self.load_icon(icon_source),
                            args_hint=kp.ItemArgsHint.FORBIDDEN,
                            hit_hint=kp.ItemHitHint.IGNORE))
                else:
                    suggestions.append(self.create_item(
                            category=self.ITEMCAT_RESULT,
                            label=cur['display_name_prefixed'],
                            short_desc=html.unescape(cur['title']),
                            target='https://www.reddit.com'+(cur['url']),
                            icon_handle=self.load_icon(self.logo),
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

    def on_activated(self):
        pass

    def on_deactivated(self):
        pass

    def on_events(self, flags):
        pass
