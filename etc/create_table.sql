DROP TABLE IF EXISTS video_info;

CREATE TABLE IF NOT EXISTS video_info (
    id VARCHAR(20) PRIMARY KEY,             -- 视频唯一标识符
    url TEXT NOT NULL,                      -- 视频 URL
    title TEXT NOT NULL,                    -- 视频标题
    title_zh TEXT,                          -- 视频标题zh
    title_bili TEXT,                        -- 视频标题bili
	description TEXT,                       -- 视频描述
	description_zh TEXT,                    -- 视频描述zh
	description_bili TEXT,                  -- 视频描述bili
	local_path TEXT,                        -- 本地存储路径(文件名)
	status VARCHAR(20) NOT NULL,            -- fetched, translated, downloaded, uploaded
	uploader TEXT NOT NULL,                 -- 上传者
    uploader_id VARCHAR(50),                -- 播放列表上传者 ID
    channel TEXT NOT NULL,                  -- 播放列表频道名称
    channel_id VARCHAR(50),                 -- 播放列表频道 ID
    duration INT,                           -- 视频时长（秒）
    duration_string VARCHAR(20),            -- 视频时长（字符串格式）
    view_count INT,                         -- 视频观看次数
    playlist TEXT,                          -- 播放列表名称
    playlist_id VARCHAR(50),                -- 播放列表 ID
    playlist_title TEXT,                    -- 播放列表标题
    playlist_index INT,                     -- 视频在播放列表中的索引
    last_playlist_index INT                 -- 播放列表总视频数
);

DROP TABLE IF EXISTS channel_info;

create table IF NOT EXISTS channel_info (
	channel_id VARCHAR(50) PRIMARY KEY,    -- 播放列表上传者 ID
	channel TEXT NOT NULL                  -- 上传者
);