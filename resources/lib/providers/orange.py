"""."""

import json
from typing import List, Union

from requests.exceptions import RequestException

from lib.exceptions import AuthenticationRequired, StreamDataDecodeError
from lib.utils.kodi import build_addon_url, get_addon_setting, log, set_addon_setting
from lib.utils.request import request, request_json

_TOKEN_ENDPOINT = "https://radio.orange.com/token.php"

_BROWSING_RADIO_ENDPOINT = "https://api.radio.orange.com/api/browsing/radios/all/all/{country}/all"
_BROWSING_PODCAST_ENDPOINT = "https://api.radio.orange.com/api/browsing/podcasts/all/all/{country}/all"

_RADIO_STREAMS_ENDPOINT = "https://api.radio.orange.com/api/radios/{stream_id}/streams"
_RADIO_PODCASTS_ENDPOINT = "https://api.radio.orange.com/api/radios/{radio_id}/podcasts"
_PODCAST_SHOWS_ENDPOINT = "https://api.radio.orange.com/api/podcasts/{podcast_id}/shows"
_SHOW_STREAMS_ENDPOINT = "https://api.radio.orange.com/api/shows/{stream_id}/streams"


class OrangeProvider:
    """Orange Provider."""

    chunk_size = 2000

    def get_live_stream_info(self, stream_id: str) -> dict:
        """Get live stream info."""
        return self._get_stream_info(_RADIO_STREAMS_ENDPOINT, stream_id)

    def get_podcast_stream_info(self, stream_id: str) -> dict:
        """Get podcast stream info."""
        return self._get_stream_info(_SHOW_STREAMS_ENDPOINT, stream_id)

    def get_streams(self) -> list:
        """Get live streams."""
        country = get_addon_setting("orange.country")
        radios = self._request_chunks(_BROWSING_RADIO_ENDPOINT.format(country=country))

        log(f"{len(radios)} radios found")

        return [
            {
                "id": radio["slug"],
                "name": radio["name"],
                "logo": radio["url_logo_large"],
                "stream": build_addon_url(f"/stream/live/{radio['slug']}"),
                "radio": True,
            }
            for radio in radios
        ]

    def get_epg(self) -> list:
        """Get EPG data."""
        return []

    def get_catchup_items(self, levels: List[str]) -> list:
        """Return a list of directory items for the specified levels."""
        depth = len(levels)

        if depth == 0:
            return self._get_podcast_radios()
        elif depth == 1:
            return self._get_podcasts(levels[0])
        elif depth == 2:
            return self._get_podcast_shows(levels[1])

    def _get_podcast_radios(self) -> list:
        """Load available podcast radios."""
        country = get_addon_setting("orange.country")
        podcasts = self._request_chunks(_BROWSING_PODCAST_ENDPOINT.format(country=country))
        radios = {"other": {"label": "Other", "thumb": None, "path": build_addon_url("/podcasts/other")}}

        for podcast in podcasts:
            if podcast["radio_permalink"]:
                radios[podcast["radio_permalink"].split("/")[-1]] = {
                    "label": podcast["radio_name"],
                    "thumb": podcast["radio_url_logo_large"],
                }

        return [
            {
                "is_folder": True,
                "label": radio["label"],
                "art": {"thumb": radio["thumb"]},
                "path": build_addon_url(f"/podcasts/{radio_id}"),
            }
            for radio_id, radio in radios.items()
        ]

    def _get_podcasts(self, radio_id: str) -> list:
        """Load available podcasts for the specified radio."""
        if radio_id == "other":
            return []

        podcasts = self._request_chunks(_RADIO_PODCASTS_ENDPOINT.format(radio_id=radio_id))

        return [
            {
                "is_folder": True,
                "label": podcast["name"],
                "art": {"thumb": podcast["url_logo_large"]},
                "path": build_addon_url(f"/podcasts/{radio_id}/{podcast['slug']}"),
            }
            for podcast in podcasts
        ]

    def _get_podcast_shows(self, podcast_id: str) -> list:
        """Load available shows for the specified podcast."""
        shows = self._request_chunks(_PODCAST_SHOWS_ENDPOINT.format(podcast_id=podcast_id))

        return [
            {
                "is_folder": False,
                "label": show["name"],
                "path": build_addon_url(f"/stream/podcast/{show['slug']}"),
                "art": {"thumb": show["podcast_url_logo_large"]},
                "info": {
                    "duration": show["duration"],
                },
            }
            for show in shows
        ]

    def _get_stream_info(self, stream_endpoint: str, stream_id: str) -> dict:
        """Load stream info from Orange."""
        streams = self._request_json(stream_endpoint.format(stream_id=stream_id), default={"result": []})["result"]

        streams = [stream for stream in streams if stream["transport"] == "http"]
        log(streams)

        if len(streams) == 0:
            raise StreamDataDecodeError()

        for stream in streams:
            if stream["transport"] == "http":
                return {"path": stream["url"], "mime_type": "video/mpeg"}

        raise StreamDataDecodeError()

    def _request_chunks(self, url: str) -> list:
        """."""
        pagination = "?size={size}&page={page}"
        page = 0
        count = 0
        result = []

        while count > len(result) or page == 0:
            page += 1
            chunk = self._request_json(url + pagination.format(size=self.chunk_size, page=page), default={"result": []})
            count = chunk.get("paginate", {}).get("count", 0)
            result.extend(chunk.get("result", []))

        return result

    def _request_json(self, url: str, default: Union[dict, list] = None) -> Union[dict, list]:
        """."""
        orange_session_data = get_addon_setting("orange.session_data", dict)
        access_token = orange_session_data.get("access_token")
        content = None

        if access_token is not None:
            content = request_json(url, headers={"Authorization": f"Bearer {access_token}"})

        if content is None:
            try:
                access_token = self._get_acces_token()
                set_addon_setting("orange.session_data", {"access_token": access_token})
            except RequestException as e:
                raise AuthenticationRequired("Cannot fetch access token") from e

            content = request_json(url, headers={"Authorization": f"Bearer {access_token}"})

        return content if content is not None else default

    def _get_acces_token(self) -> str:
        """Get access token."""
        res = request("GET", _TOKEN_ENDPOINT)
        content = json.loads(res.json())
        return content.get("access_token")
