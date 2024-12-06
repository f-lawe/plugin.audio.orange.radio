"""Radio stream manager."""

from typing import Callable

import xbmc
import xbmcplugin

from lib.exceptions import AuthenticationRequired, StreamDataDecodeError
from lib.providers import OrangeProvider
from lib.router import router
from lib.utils.gui import create_play_item
from lib.utils.kodi import localize, log, ok_dialog


class StreamManager:
    """Load video streams using active provider."""

    def __init__(self):
        """Initialize Stream Manager object."""
        self.provider = OrangeProvider()

    def load_live_stream(self, stream_id: str) -> None:
        """Load live stream."""
        self._load_stream(self.provider.get_live_stream_info, stream_id)

    def load_podcast_stream(self, stream_id: str) -> None:
        """Load podcast stream."""
        self._load_stream(self.provider.get_podcast_stream_info, stream_id)

    def _load_stream(self, stream_getter: Callable[[str], dict], stream_id: str) -> None:
        """Load stream."""
        try:
            stream_info = stream_getter(stream_id)
        except StreamDataDecodeError:
            log("Cannot decode stream data", xbmc.LOGERROR)
            ok_dialog(localize(30900))
            xbmcplugin.setResolvedUrl(router.handle, False, create_play_item())
            return
        except AuthenticationRequired as e:
            log(e, xbmc.LOGERROR)
            ok_dialog(localize(30901))
            xbmcplugin.setResolvedUrl(router.handle, False, create_play_item())
            return

        play_item = create_play_item(stream_info)
        xbmcplugin.setResolvedUrl(router.handle, True, play_item)
