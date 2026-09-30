import logging
from flask import Blueprint, jsonify, request
from models.ticket_model import (
    get_all_tickets,
    get_ticket_by_id,
    create_ticket,
    update_ticket,
    delete_ticket,
)

logger = logging.getLogger("ticketing-app")
ticket_bp = Blueprint("tickets", __name__)


@ticket_bp.route("/tickets", methods=["GET"])
def get_tickets():
    try:
        return jsonify(get_all_tickets())
    except Exception as e:
        logger.exception("Failed to fetch tickets")
        return jsonify({"error": str(e)}), 500


@ticket_bp.route("/tickets", methods=["POST"])
def create():
    data = request.get_json()
    title = data.get("title")
    status = data.get("status", "open")
    created_by = data.get("created_by", "system")

    if not title:
        return jsonify({"error": "Title is required"}), 400

    try:
        ticket = create_ticket(title, status, created_by)
        return jsonify(ticket), 201
    except Exception as e:
        logger.exception("Failed to create ticket")
        return jsonify({"error": str(e)}), 500


@ticket_bp.route("/tickets/<int:ticket_id>", methods=["GET"])
def get_one(ticket_id):
    try:
        ticket = get_ticket_by_id(ticket_id)
        if not ticket:
            return jsonify({"error": "Ticket not found"}), 404
        return jsonify(ticket)
    except Exception as e:
        logger.exception(f"Failed to fetch ticket {ticket_id}")
        return jsonify({"error": str(e)}), 500


@ticket_bp.route("/tickets/<int:ticket_id>", methods=["PATCH"])
def update(ticket_id):
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
        ticket = update_ticket(ticket_id, updates, params)
        if not ticket:
            return jsonify({"error": "Ticket not found"}), 404
        return jsonify(ticket)
    except Exception as e:
        logger.exception(f"Failed to update ticket {ticket_id}")
        return jsonify({"error": str(e)}), 500


@ticket_bp.route("/tickets/<int:ticket_id>", methods=["DELETE"])
def delete(ticket_id):
    try:
        deleted = delete_ticket(ticket_id)
        if not deleted:
            return jsonify({"error": "Ticket not found"}), 404
        return jsonify({"message": "Ticket deleted", "id": ticket_id})
    except Exception as e:
        logger.exception(f"Failed to delete ticket {ticket_id}")
        return jsonify({"error": str(e)}), 500
