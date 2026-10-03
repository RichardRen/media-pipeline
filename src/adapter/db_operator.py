import os

import psycopg2


class DbOperator:

    def __init__(self):
        pass

    @classmethod
    def insert_video_info(cls, video_info):
        cursor, conn = cls.conn_db()
        try:
            insert_query = """
                INSERT INTO video_info (
                    id, url, title, description, status, uploader,
                    uploader_id, channel, channel_id, duration, duration_string, view_count, playlist, playlist_id,
                    playlist_title, playlist_index, last_playlist_index
                ) VALUES (
                    %(id)s, %(url)s, %(title)s, %(description)s,
                    %(status)s, %(uploader)s, %(uploader_id)s, %(channel)s, %(channel_id)s, %(duration)s,
                    %(duration_string)s, %(view_count)s, %(playlist)s, %(playlist_id)s, %(playlist_title)s,
                    %(playlist_index)s, %(last_playlist_index)s
                )
                ON CONFLICT (id) DO NOTHING;
            """
            # 将 VideoInfo 转为字典
            cursor.execute(insert_query, video_info)
            conn.commit()
            video_id = video_info.get("id")
            print(f"Inserted video: {video_id}")
        except Exception as e:
            print(f"Error inserting video info: {e}")
        finally:
            cls.close_db(cursor, conn)

    @classmethod
    def query_video_info_by_id(cls, video_id) -> dict:
        query = "SELECT * FROM video_info WHERE id = %s;"
        try:
            cursor, conn = cls.conn_db()
            cursor.execute(query, (video_id,))
            result = cursor.fetchone()
            cls.close_db(cursor, conn)
            if result:
                # 将结果转换为字典
                column_names = [desc[0] for desc in cursor.description]
                video_info = dict(zip(column_names, result))
                return video_info
            else:
                return None
        except psycopg2.Error as e:
            print(f"Error querying video by id: {e}")
            return None

    @classmethod
    def update_vide_status_by_id(cls, video_id, status):
        query = "UPDATE video_info SET status = %s WHERE id = %s;"
        try:
            cursor, conn = cls.conn_db()
            # 执行更新语句
            cursor.execute(query, (status, video_id))
            # 提交更改
            conn.commit()
            # 检查更新是否成功
            if cursor.rowcount > 0:
                print(f"Status updated successfully for video ID: {video_id}")
            else:
                print(f"No record found with video ID: {video_id}")
            cls.close_db(cursor, conn)
        except psycopg2.Error as e:
            print(f"Error updating status for video ID {video_id}: {e}")

    @classmethod
    def update_translated_content_by_id(cls, video_id, title_zh, description_zh, title_bili, description_bili,
                                        local_path):
        query = "UPDATE video_info SET title_zh = %s, description_zh = %s, title_bili = %s, description_bili = %s, local_path = %s WHERE id = %s;"
        try:
            cursor, conn = cls.conn_db()
            # 执行更新语句
            cursor.execute(query, (title_zh, description_zh, title_bili, description_bili, local_path, video_id))
            # 提交更改
            conn.commit()
            # 检查更新是否成功
            if cursor.rowcount > 0:
                print(f"Status updated successfully for video ID: {video_id}")
            else:
                print(f"No record found with video ID: {video_id}")
            cls.close_db(cursor, conn)
        except psycopg2.Error as e:
            print(f"Error updating status for video ID {video_id}: {e}")

    @classmethod
    def insert_channel_info(cls, channel_info):
        cursor, conn = cls.conn_db()
        insert_query = """
            INSERT INTO channel_info (
                channel_id, channel
            ) VALUES (
                %(channel_id)s, %(channel)s
            )
            ON CONFLICT (channel_id) DO NOTHING;
        """
        cursor.execute(insert_query, channel_info.__dict__)
        conn.commit()
        cls.close_db(cursor, conn)

    @staticmethod
    def conn_db():
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB", "videos"),
            user=os.getenv("POSTGRES_USER", "user"),
            password=os.environ["POSTGRES_PASSWORD"],
            host=os.getenv("POSTGRES_HOST", "postgres"),
            port=int(os.getenv("POSTGRES_PORT", "5432"))
        )
        cursor = conn.cursor()
        return cursor, conn

    @staticmethod
    def close_db(cursor, conn):
        cursor.close()
        conn.close()
