"""Helpers for Kodi GUI."""

from xbmcgui import ListItem


def create_list_item(item_data: dict, is_folder: bool = False) -> ListItem:
    """Create a list item from data."""
    list_item = ListItem(label=item_data.get("label"), path=item_data.get("path"))

    if "art" in item_data:
        item_art_data: dict = item_data.get("art", {})
        list_item.setArt(
            {
                "poster": item_art_data.get("poster"),
                "thumb": item_art_data.get("thumb"),
            }
        )

    if not is_folder:
        list_item.setProperties(
            {
                "IsPlayable": "true",
            }
        )

    if "info" in item_data:
        item_info_data: dict = item_data.get("info", {})
        video_info_tag = list_item.getVideoInfoTag()

        if "duration" in item_info_data:
            video_info_tag.setDuration(item_info_data.get("duration"))

        if "genres" in item_info_data:
            video_info_tag.setGenres(item_info_data.get("genres"))

        if "plot" in item_info_data:
            video_info_tag.setPlot(item_info_data.get("plot"))

        if "year" in item_info_data:
            video_info_tag.setYear(item_info_data.get("year"))

    return list_item


def create_play_item(stream_info: dict = None) -> ListItem:
    """Create a play item from stream data."""
    if stream_info is None:
        stream_info = {}

    play_item = ListItem(path=stream_info.get("path"))
    play_item.setContentLookup(False)
    play_item.setMimeType(stream_info.get("mime_type"))
    play_item.setProperty("inputstream", "inputstream.ffmpegdirect")

    return play_item
