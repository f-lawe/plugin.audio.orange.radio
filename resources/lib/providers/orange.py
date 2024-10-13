"""."""

import json

import xbmc
from requests.exceptions import RequestException

from lib.exceptions import AuthenticationRequired, StreamDataDecodeError
from lib.utils.kodi import build_addon_url, log
from lib.utils.request import request, request_json

_BROWSING_ENDPOINT = "https://api.radio.orange.com/api/browsing/radios/all/all/{country}/all?size={size}"
_TOKEN_ENDPOINT = "https://radio.orange.com/token.php"
_STREAMS_ENDPOINT = "https://api.radio.orange.com/api/radios/{radio_id}/streams"


class OrangeProvider:
    """Orange Provider."""

    browsing_chunk_size = 10000

    def get_streams(self) -> list:
        """Get live streams."""
        try:
            access_token = self._get_acces_token()
        except RequestException:
            log("Cannot retreive access token", xbmc.LOGERROR)
            return []

        radios = request_json(
            _BROWSING_ENDPOINT.format(country="fr", size=self.browsing_chunk_size),
            headers={"Authorization": f"Bearer {access_token}"},
            default={"result": []},
        )["result"]

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
        try:
            access_token = self._get_acces_token()
        except RequestException as e:
            raise AuthenticationRequired("Cannot retreive access token") from e

        streams = request_json(
            _STREAMS_ENDPOINT.format(radio_id=stream_id),
            headers={"Authorization": f"Bearer {access_token}"},
            default={"result": []},
        )["result"]

        streams = [stream for stream in streams if stream["transport"] == "http"]

        if len(streams) == 0:
            raise StreamDataDecodeError()

        for stream in streams:
            if stream["transport"] == "http":
                return {"path": stream["url"], "mime_type": "audio/mpeg"}

        raise StreamDataDecodeError()

    def _get_acces_token(self) -> str:
        """Get bearer token."""
        res = request("GET", _TOKEN_ENDPOINT)
        content = json.loads(res.json())
        return content.get("access_token")
