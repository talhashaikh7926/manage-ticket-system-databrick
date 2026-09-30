import logging
from flask import Blueprint, jsonify, request
from models.ticket_model import ticket_exists
from models.message_model import get_messages_by_ticket, create_message

logger = logging.getLogger("ticketing-app")
message_bp = Blueprint("messages", __name__)


@message_bp.route("/tickets/<int:ticket_id>/messages", methods=["GET"])
def get_messages(ticket_id):
    try:
        return jsonify(get_messages_by_ticket(ticket_id))
    except Exception as e:
        logger.exception(f"Failed to fetch messages for ticket {ticket_id}")
        return jsonify({"error": str(e)}), 500


@message_bp.route("/tickets/<int:ticket_id>/messages", methods=["POST"])
def add_message(ticket_id):
    data = request.get_json()
    message_text = data.get("message_text")
    author = data.get("author", "system")

    if not message_text:
        return jsonify({"error": "message_text is required"}), 400

    try:
        if not ticket_exists(ticket_id):
            return jsonify({"error": "Ticket not found"}), 404
        message = create_message(ticket_id, message_text, author)
        return jsonify(message), 201
    except Exception as e:
        logger.exception(f"Failed to create message for ticket {ticket_id}")
        return jsonify({"error": str(e)}), 500
