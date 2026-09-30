import os
import logging
from flask import Flask, jsonify, request, render_template
from databricks.sdk import WorkspaceClient
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ticketing-app")

app = Flask(__name__)
_w = WorkspaceClient()

# These environment variables are automatically injected by Databricks
# when you add a Lakebase resource to your app.yaml
PGHOST = os.environ.get("PGHOST")
PGDATABASE = os.environ.get("PGDATABASE", "databricks_postgres")
PGUSER = os.environ.get("PGUSER")
PGPORT = os.environ.get("PGPORT", "5432")
DATABRICKS_CLIENT_ID = os.environ.get("DATABRICKS_CLIENT_ID")


def get_oauth_token():
    """Generate a short-lived OAuth token for Lakebase authentication."""
    token_response = _w.dbutils.secrets.get_token(
        application_id=DATABRICKS_CLIENT_ID,
        lifetime_seconds=3600  # 1 hour
    )
    return token_response.token_value


def get_connection():
    """Create a psycopg2 connection to Lakebase using OAuth token."""
    token = get_oauth_token()
    
    conn = psycopg2.connect(
        host=PGHOST,
        port=PGPORT,
        database=PGDATABASE,
        user=PGUSER,
        password=token,
        sslmode="require",
        cursor_factory=RealDictCursor
    )
    return conn


def init_db():
    """Tables already exist in ticketing_system_schema - no initialization needed."""
    pass


@app.route("/")
def index():
    """Main UI - ticket management dashboard."""
    return render_template("index.html")


@app.route("/healthz")
def healthz():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


@app.route("/test-db")
def test_db():
    """Test database connection and show configuration."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database(), current_user")
                result = cur.fetchone()
                return jsonify({
                    "status": "connected",
                    "database": result["current_database"],
                    "user": result["current_user"],
                    "config": {
                        "PGHOST": PGHOST,
                        "PGDATABASE": PGDATABASE,
                        "PGUSER": PGUSER,
                        "PGPORT": PGPORT
                    }
                })
    except Exception as e:
        logger.exception("Database connection failed")
        return jsonify({"error": str(e)}), 500


@app.route("/tickets", methods=["GET"])
def get_tickets():
    """Get all tickets."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ticket_id, title, status, created_by, created_at
                    FROM ticketing_system_schema.tickets
                    ORDER BY created_at DESC
                """)
                tickets = cur.fetchall()
                return jsonify(tickets)
    except Exception as e:
        logger.exception("Failed to fetch tickets")
        return jsonify({"error": str(e)}), 500


@app.route("/tickets", methods=["POST"])
def create_ticket():
    """Create a new ticket."""
    data = request.get_json()
    
    title = data.get("title")
    status = data.get("status", "open")
    created_by = data.get("created_by", "system")
    
    if not title:
        return jsonify({"error": "Title is required"}), 400
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO ticketing_system_schema.tickets (title, status, created_by)
                    VALUES (%s, %s, %s)
                    RETURNING ticket_id, title, status, created_by, created_at
                """, (title, status, created_by))
                ticket = cur.fetchone()
                conn.commit()
                return jsonify(ticket), 201
    except Exception as e:
        logger.exception("Failed to create ticket")
        return jsonify({"error": str(e)}), 500


@app.route("/tickets/<int:ticket_id>", methods=["GET"])
def get_ticket(ticket_id):
    """Get a specific ticket by ID."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ticket_id, title, status, created_by, created_at
                    FROM ticketing_system_schema.tickets
                    WHERE ticket_id = %s
                """, (ticket_id,))
                ticket = cur.fetchone()
                
                if not ticket:
                    return jsonify({"error": "Ticket not found"}), 404
                
                return jsonify(ticket)
    except Exception as e:
        logger.exception(f"Failed to fetch ticket {ticket_id}")
        return jsonify({"error": str(e)}), 500


@app.route("/tickets/<int:ticket_id>", methods=["PATCH"])
def update_ticket(ticket_id):
    """Update a ticket's status, priority, or description."""
    data = request.get_json()
    
    updates = []
    params = []
    
    if "status" in data:
        updates.append("status = %s")
        params.append(data["status"])
    
    if "title" in data:
        updates.append("title = %s")
        params.append(data["title"])
    
    if not updates:
        return jsonify({"error": "No fields to update"}), 400
    
    params.append(ticket_id)
    
    try:
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
                
                if not ticket:
                    return jsonify({"error": "Ticket not found"}), 404
                
                conn.commit()
                return jsonify(ticket)
    except Exception as e:
        logger.exception(f"Failed to update ticket {ticket_id}")
        return jsonify({"error": str(e)}), 500


@app.route("/tickets/<int:ticket_id>", methods=["DELETE"])
def delete_ticket(ticket_id):
    """Delete a ticket."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM ticketing_system_schema.tickets WHERE ticket_id = %s RETURNING ticket_id", (ticket_id,))
                deleted = cur.fetchone()
                
                if not deleted:
                    return jsonify({"error": "Ticket not found"}), 404
                
                conn.commit()
                return jsonify({"message": "Ticket deleted", "id": ticket_id})
    except Exception as e:
        logger.exception(f"Failed to delete ticket {ticket_id}")
        return jsonify({"error": str(e)}), 500


@app.route("/tickets/<int:ticket_id>/messages", methods=["GET"])
def get_ticket_messages(ticket_id):
    """Get all messages for a specific ticket."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT message_id, ticket_id, message_text, author, created_at
                    FROM ticketing_system_schema.ticket_messages
                    WHERE ticket_id = %s
                    ORDER BY created_at ASC
                """, (ticket_id,))
                messages = cur.fetchall()
                return jsonify(messages)
    except Exception as e:
        logger.exception(f"Failed to fetch messages for ticket {ticket_id}")
        return jsonify({"error": str(e)}), 500


@app.route("/tickets/<int:ticket_id>/messages", methods=["POST"])
def create_ticket_message(ticket_id):
    """Add a message to a ticket."""
    data = request.get_json()
    
    message_text = data.get("message_text")
    author = data.get("author", "system")
    
    if not message_text:
        return jsonify({"error": "message_text is required"}), 400
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Verify ticket exists
                cur.execute(
                    "SELECT 1 FROM ticketing_system_schema.tickets WHERE ticket_id = %s",
                    (ticket_id,)
                )
                if not cur.fetchone():
                    return jsonify({"error": "Ticket not found"}), 404
                
                # Insert message
                cur.execute("""
                    INSERT INTO ticketing_system_schema.ticket_messages (ticket_id, message_text, author)
                    VALUES (%s, %s, %s)
                    RETURNING message_id, ticket_id, message_text, author, created_at
                """, (ticket_id, message_text, author))
                message = cur.fetchone()
                conn.commit()
                return jsonify(message), 201
    except Exception as e:
        logger.exception(f"Failed to create message for ticket {ticket_id}")
        return jsonify({"error": str(e)}), 500


@app.errorhandler(Exception)
def handle_exception(err):
    """Global error handler."""
    logger.exception("Unhandled exception")
    status_code = getattr(err, "code", 500)
    if not isinstance(status_code, int):
        status_code = 500
    return jsonify({"error": str(err)}), status_code


if __name__ == "__main__":
    # Initialize database on startup
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    # Start Flask app
    port = int(os.environ.get("DATABRICKS_APP_PORT", 8000))
    app.run(host="0.0.0.0", port=port)
