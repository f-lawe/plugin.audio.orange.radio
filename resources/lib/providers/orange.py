"""."""

import json
from typing import Union

from requests.exceptions import RequestException

from lib.exceptions import AuthenticationRequired, StreamDataDecodeError
from lib.utils.kodi import build_addon_url, get_addon_setting, log, set_addon_setting
from lib.utils.request import request, request_json

_BROWSING_ENDPOINT = "https://api.radio.orange.com/api/browsing/radios/all/all/{country}/all"
_TOKEN_ENDPOINT = "https://radio.orange.com/token.php"
_STREAMS_ENDPOINT = "https://api.radio.orange.com/api/radios/{radio_id}/streams"


class OrangeProvider:
    """Orange Provider."""

    chunk_size = 2500

    def get_streams(self) -> list:
        """Get live streams."""
        country = get_addon_setting("orange.country")
        radios = self._request_chunks(_BROWSING_ENDPOINT.format(country=country))

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

    def get_live_stream_info(self, stream_id: str) -> dict:
        """Get live stream info."""
        streams = self._request_json(_STREAMS_ENDPOINT.format(radio_id=stream_id), default={"result": []})["result"]

        streams = [stream for stream in streams if stream["transport"] == "http"]

        if len(streams) == 0:
            raise StreamDataDecodeError()

        for stream in streams:
            if stream["transport"] == "http":
                return {"path": stream["url"], "mime_type": "audio/mpeg"}

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
