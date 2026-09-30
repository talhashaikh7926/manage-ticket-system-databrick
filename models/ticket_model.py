from config.database import get_connection


def get_all_tickets():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ticket_id, title, status, created_by, created_at
                FROM ticketing_system_schema.tickets
                ORDER BY created_at DESC
            """)
            return cur.fetchall()


def get_ticket_by_id(ticket_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ticket_id, title, status, created_by, created_at
                FROM ticketing_system_schema.tickets
                WHERE ticket_id = %s
            """, (ticket_id,))
            return cur.fetchone()


def create_ticket(title, status, created_by):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ticketing_system_schema.tickets (title, status, created_by)
                VALUES (%s, %s, %s)
                RETURNING ticket_id, title, status, created_by, created_at
            """, (title, status, created_by))
            ticket = cur.fetchone()
            conn.commit()
            return ticket


def update_ticket(ticket_id, updates, params):
    with get_connection() as conn:
        with conn.cursor() as cur:
            sql = f"""
                UPDATE ticketing_system_schema.tickets
                SET {', '.join(updates)}
                WHERE ticket_id = %s
                RETURNING ticket_id, title, status, created_by, created_at
            """
            cur.execute(sql, params)
            ticket = cur.fetchone()
            conn.commit()
            return ticket


def delete_ticket(ticket_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM ticketing_system_schema.tickets WHERE ticket_id = %s RETURNING ticket_id",
                (ticket_id,)
            )
            deleted = cur.fetchone()
            conn.commit()
            return deleted


def ticket_exists(ticket_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM ticketing_system_schema.tickets WHERE ticket_id = %s",
                (ticket_id,)
            )
            return cur.fetchone() is not None
