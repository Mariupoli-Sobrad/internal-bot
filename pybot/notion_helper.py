import requests
import os
from dataclasses import dataclass
from typing import Dict, List
from cachetools import cached, TTLCache

@dataclass
class Channel:
    id: int
    url: str
    name: str


TOKEN = os.getenv('NOTION_KEY')
PEOPLE_DB_ID = os.getenv('PEOPLE_DATABASE_ID')
CHANNELS_DB_ID = os.getenv('CHANNEL_DATABASE_ID')
TTL_SECONDS = int(os.getenv('TTL_SECONDS', 600))


@cached(cache=TTLCache(maxsize=2, ttl=TTL_SECONDS))
def __read_database(database_id):
    # TODO: add pagination support: https://www.reddit.com/r/Notion/comments/pcro6l/comment/hee0v6l/
    headers = {
        "Authorization": "Bearer " + TOKEN,
        "Content-Type": "application/json",
        "Notion-Version": "2021-08-16"
    }

    read_url = f"https://api.notion.com/v1/databases/{database_id}/query"

    res = requests.request("POST", read_url, headers=headers)
    data = res.json()

    return data


def __get_users(data) -> Dict[str, List[str]]:
    users: Dict[str, List[str]] = {}

    for res in data['results']:
        props = res['properties']
        username = props['Telegram']['url']
        tags = [x['id'] for x in props['Tags']['relation']]

        users[username] = tags

    return users


def __get_channels(data) -> Dict[str, Channel]:
    channels: Dict[str, Channel] = {}

    for res in data['results']:
        url = res['properties']['Invite link']['url']
        id = res['properties']['id']['number']
        name = res['properties']['Name']['title'][0]['text']['content']

        channels[res['id']] = Channel(id, url, name)

    return channels


def get_channels(username: str) -> List[Channel]:
    user_data = __read_database(PEOPLE_DB_ID)
    channel_data = __read_database(CHANNELS_DB_ID)

    users = __get_users(user_data)
    channels = __get_channels(channel_data)

    user_channels = users.get("@" + username)
    if user_channels is None:
        return []

    return [channels[channel_entry_id] for channel_entry_id in user_channels]




