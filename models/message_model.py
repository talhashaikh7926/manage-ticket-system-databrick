from config.database import get_connection


def get_messages_by_ticket(ticket_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT message_id, ticket_id, message_text, author, created_at
                FROM ticketing_system_schema.ticket_messages
                WHERE ticket_id = %s
                ORDER BY created_at ASC
            """, (ticket_id,))
            return cur.fetchall()


def create_message(ticket_id, message_text, author):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ticketing_system_schema.ticket_messages (ticket_id, message_text, author)
                VALUES (%s, %s, %s)
                RETURNING message_id, ticket_id, message_text, author, created_at
            """, (ticket_id, message_text, author))
            message = cur.fetchone()
            conn.commit()
            return message
