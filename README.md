# Karpathy Latest Tweets

Simple Python program to fetch Andrej Karpathy's latest X/Twitter posts via an **RSS/Atom feed** (default: [RSSHub](https://github.com/DIYgod/RSSHub) `twitter/user/:id`). No Twitter API keys are required.

If the default instance is slow or blocked, pass your own feed URL, for example `--feed-url https://YOUR_RSSHUB/twitter/user/karpathy`.

## Setup

```powershell
cd karpathy-latest-tweets
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```powershell
python get_latest_tweets.py --limit 5
```

Optional:

```powershell
python get_latest_tweets.py --username karpathy --limit 10 --save-json output.json
python get_latest_tweets.py --feed-url "https://rsshub.app/twitter/user/karpathy" --limit 5
```

The script prints items to the terminal and saves JSON output. Like/repost counts are not in typical RSS feeds and are omitted (`null` in JSON).
