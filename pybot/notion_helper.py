import requests
import os
from dataclasses import dataclass
from typing import Dict, List, Union


@dataclass
class Channel:
    id: int
    url: str
    name: str


TOKEN = os.getenv('NOTION_KEY')
PEOPLE_DB_ID = os.getenv('PEOPLE_DATABASE_ID')
CHANNELS_DB_ID = os.getenv('CHANNEL_DATABASE_ID')

HEADERS = {
    "Authorization": "Bearer " + TOKEN,
    "Content-Type": "application/json",
    "Notion-Version": "2021-08-16"
}


def __read_database(database_id, headers):
    read_url = f"https://api.notion.com/v1/databases/{database_id}/query"

    res = requests.request("POST", read_url, headers=headers)
    data = res.json()

    return data


def __get_users(data) -> Dict[str, List[str]]:
    users: Dict[str, List[str]] = {}

    for res in data['results']:
        props = res['properties']
        username = props['Telegram']['url']
        tags = list(map(lambda x: x['id'], props['Tags']['relation']))

        users[username] = tags

    return users


def __get_channels(data) -> Dict[str, Channel] :
    channels: Dict[str, Channel] = {}

    for res in data['results']:
        url = res['properties']['Invite link']['url']
        id = res['properties']['id']['number']
        name = res['properties']['Name']['title'][0]['text']['content']

        channels[res['id']] = Channel(id, url, name)

    return channels


def get_channels(username: str) -> Union[List[Channel], None]:
    user_data = __read_database(PEOPLE_DB_ID, HEADERS)
    channel_data = __read_database(CHANNELS_DB_ID, HEADERS)

    users = __get_users(user_data)
    channels = __get_channels(channel_data)

    user_channels = users.get("@" + username)
    if user_channels is None:
        return None

    return list(map(lambda channel_entry_id: channels[channel_entry_id], user_channels))




