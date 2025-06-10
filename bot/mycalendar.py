import psycopg2


class Calendar:
    def __init__(self, conn):
        self.conn = conn
        # Создание таблицы при необходимости
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    name TEXT NOT NULL,
                    date DATE NOT NULL,
                    time TIME NOT NULL,
                    details TEXT
                );
            """)
            self.conn.commit()

    def create_event(self, user_id, event_name, event_date, event_time, event_details):
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO events (user_id, name, date, time, details)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (user_id, event_name, event_date, event_time, event_details),
            )
            event_id = cur.fetchone()[0]
            self.conn.commit()
            return event_id

    def get_event(self, user_id, event_id):
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, date, time, details FROM events WHERE id=%s AND user_id=%s",
                (event_id, user_id)
            )
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "date": str(row[2]),
                    "time": str(row[3]),
                    "details": row[4]
                }
            return None

    def get_all_events(self, user_id):
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, date, time, details FROM events WHERE user_id=%s ORDER BY date, time",
                (user_id,)
            )
            rows = cur.fetchall()
            return [
                {
                    "id": r[0],
                    "name": r[1],
                    "date": str(r[2]),
                    "time": str(r[3]),
                    "details": r[4]
                }
                for r in rows
            ]

    def edit_event(self, user_id, event_id, event_name=None, event_date=None, event_time=None, event_details=None):
        columns = []
        values = []
        if event_name:
            columns.append("name=%s")
            values.append(event_name)
        if event_date:
            columns.append("date=%s")
            values.append(event_date)
        if event_time:
            columns.append("time=%s")
            values.append(event_time)
        if event_details:
            columns.append("details=%s")
            values.append(event_details)
        if not columns:
            return False  # ничего не меняется
        values.extend([event_id, user_id])
        with self.conn.cursor() as cur:
            cur.execute(
                f"UPDATE events SET {', '.join(columns)} WHERE id=%s AND user_id=%s",
                values
            )
            self.conn.commit()
            return cur.rowcount > 0

    def delete_event(self, user_id, event_id):
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM events WHERE id=%s AND user_id=%s", (event_id, user_id))
            self.conn.commit()
            return cur.rowcount > 0