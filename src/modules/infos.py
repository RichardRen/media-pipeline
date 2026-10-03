class VideoInfo:
    def __init__(self, id, url, title, title_bili, description, description_bili, local_path, status, uploader,
                 uploader_id, channel, channel_id, duration, duration_string, view_count, playlist, playlist_id,
                 playlist_title, playlist_index, last_playlist_index):
        self.id: str = id
        self.url: str = url
        self.title: str = title
        self.title_bili: str = title_bili
        self.description: str = description
        self.description_bili: str = description_bili
        self.local_path: str = local_path
        self.status: str = status
        self.uploader: str = uploader
        self.uploader_id: str = uploader_id
        self.channel: str = channel
        self.channel_id: str = channel_id
        self.duration: int = duration
        self.duration_string: str = duration_string
        self.view_count: int = view_count
        self.playlist: str = playlist
        self.playlist_id: str = playlist_id
        self.playlist_title: str = playlist_title
        self.playlist_index: int = playlist_index
        self.last_playlist_index: int = last_playlist_index


class ChannelInfo:
    def __init__(self, channel_id, channel):
        self.channel_id = channel_id
        self.channel = channel
