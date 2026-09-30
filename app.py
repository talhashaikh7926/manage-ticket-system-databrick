import os
import logging
from flask import Flask, jsonify, render_template
from config.database import get_connection
from controllers.ticket_controller import ticket_bp
from controllers.message_controller import message_bp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ticketing-app")

app = Flask(__name__)
app.register_blueprint(ticket_bp)
app.register_blueprint(message_bp)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@app.route("/test-db")
def test_db():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database(), current_user")
                result = cur.fetchone()
                return jsonify({
                    "status": "connected",
                    "database": result["current_database"],
                    "user": result["current_user"],
                })
    except Exception as e:
        logger.exception("Database connection failed")
        return jsonify({"error": str(e)}), 500


@app.errorhandler(Exception)
def handle_exception(err):
    logger.exception("Unhandled exception")
    status_code = getattr(err, "code", 500)
    if not isinstance(status_code, int):
        status_code = 500
    return jsonify({"error": str(err)}), status_code


if __name__ == "__main__":
    port = int(os.environ.get("DATABRICKS_APP_PORT", 8000))
    app.run(host="0.0.0.0", port=port)
