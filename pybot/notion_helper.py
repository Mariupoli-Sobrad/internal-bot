import requests
import os
from dataclasses import dataclass
from typing import Dict, List, Any
from cachetools import cached, TTLCache
from enum import Enum
from collections import defaultdict


class ChannelType(Enum):
    CHANNEL = 1
    CHAT = 2


@dataclass
class Channel:
    # id: int
    url: str
    name: str
    icon: str | None
    type: ChannelType
    description: str | None
    tags: List[str]


TOKEN = os.getenv('NOTION_KEY')
PEOPLE_DB_ID = os.getenv('PEOPLE_DATABASE_ID')
CHANNELS_DB_ID = os.getenv('CHANNEL_DATABASE_ID')
TTL_SECONDS = int(os.getenv('TTL_SECONDS', 600))

headers = {
    "Authorization": "Bearer " + TOKEN,
    "Content-Type": "application/json",
    "Notion-Version": "2021-08-16"
}


@cached(cache=TTLCache(maxsize=1, ttl=TTL_SECONDS))
def __read_whole_database(database_id: str) -> List[Any]:
    results = []
    read_url = f"https://api.notion.com/v1/databases/{database_id}/query"

    page_results, next_cursor = __read_database_with_query(read_url, headers)
    results.extend(page_results)
    while next_cursor is not None:
        page_results, next_cursor = __read_database_at_cursor(read_url, headers, next_cursor)
        results.extend(page_results)

    return results


@cached(cache=TTLCache(maxsize=100, ttl=TTL_SECONDS))
def __read_database_by_property(database_id: str, property_name: str, field: str, property: str) -> List[Any]:
    read_url = f"https://api.notion.com/v1/databases/{database_id}/query"

    filter_query = {
        "filter": {
            "property": property_name,
            field: {
                "equals": property
            }
        }
    }

    results, _ = __read_database_with_query(read_url, headers, filter_query)
    return results


def __read_database_at_cursor(read_url, headers, cursor) -> (List[Any], str | None):
    query = {
        'start_cursor': cursor
    }

    return __read_database_with_query(read_url, headers, query)


def __read_database_with_query(read_url, headers, query=None) -> (List[Any], str | None):
    res = requests.post(read_url, headers=headers, json=query)
    data = res.json()

    return data['results'], data['next_cursor']


def __get_user_tags(user_info: Dict[Any, Any]) -> List[str]:
    props = user_info['properties']
    tags = list(map(lambda x: x['name'], props['Tags']['multi_select']))
    return tags


def __get_channels(results: List[Any]) -> List[Channel]:
    channels: List[Channel] = []

    for res in results:
        url = res['properties']['Link']['rich_text'][0]['href']
        icon_entry = res.get('icon')
        if icon_entry is not None:
            icon = icon_entry['emoji']
        else:
            icon = None
        name = res['properties']['Name']['title'][0]['text']['content']
        description_text = res['properties']['Description']['rich_text']
        channel_type = res['properties']['Format']['multi_select'][0]['name']
        tags = [tag['name'] for tag in res['properties']['Tags']['multi_select']]

        description = None
        if len(description_text) > 0:
            description = description_text[0]['text']['content']

        if channel_type == 'Chat':
            channels.append(Channel(url, name, icon, ChannelType.CHAT, description, tags))
        elif channel_type == 'Channel':
            channels.append(Channel(url, name, icon, ChannelType.CHANNEL, description, tags))

    return channels


def __get_channels_for_tag(channels: List[Channel]) -> Dict[str, List[Channel]]:
    result: Dict[str, List[Channel]] = defaultdict(list)

    for channel in channels:
        for tag in channel.tags:
            result[tag].append(channel)

    return result


def get_channels(username: str) -> List[Channel] | None:
    channel_data = __read_whole_database(CHANNELS_DB_ID)
    user_data = __read_database_by_property(database_id=PEOPLE_DB_ID,
                                            property_name="Telegram",
                                            field="url",
                                            property="@" + username)

    if len(user_data) == 0:
        return None

    channels = __get_channels(channel_data)
    tag_to_channels = __get_channels_for_tag(channels)

    user_tags = __get_user_tags(user_data[0])
    user_channels: List[Channel] = []
    for tag in user_tags:
        user_channels.extend(tag_to_channels[tag])

    return user_channels
