#!/usr/bin/env python3
"""
Maps Hunter Dashboard — Flask app for reviewing leads from leads_v2.db.
"""

import re
import sqlite3

from flask import Flask, jsonify, redirect, render_template, request, url_for

DB_PATH = "leads_v2.db"

app = Flask(__name__)


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def clean_phone(phone: str) -> str:
    """Strip everything except digits and leading +."""
    if not phone or phone == "N/A":
        return ""
    digits = re.sub(r"[^\d+]", "", phone)
    return digits


@app.route("/")
def index():
    status_filter = request.args.get("status", "all")
    conn = get_db()

    if status_filter == "all":
        rows = conn.execute(
            "SELECT * FROM restaurants ORDER BY rating DESC NULLS LAST"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM restaurants WHERE status = ? ORDER BY rating DESC NULLS LAST",
            (status_filter,),
        ).fetchall()

    counts = {
        row["status"]: row["cnt"]
        for row in conn.execute(
            "SELECT status, COUNT(*) as cnt FROM restaurants GROUP BY status"
        ).fetchall()
    }
    counts["all"] = sum(counts.values())
    conn.close()

    leads = []
    for row in rows:
        phone_clean = clean_phone(row["phone"])
        wa_message = (
            "Dobrý den, viděl jsem vaši restauraci na Google Maps "
            "a chtěl bych se zeptat na možnost spolupráce. "
            "Máte zájem o krátký rozhovor?"
        )
        import urllib.parse
        wa_url = (
            f"https://wa.me/{phone_clean}?text={urllib.parse.quote(wa_message)}"
            if phone_clean
            else None
        )
        leads.append({
            "id": row["id"],
            "name": row["name"],
            "address": row["address"],
            "phone": row["phone"],
            "rating": row["rating"],
            "reviews_count": row["reviews_count"],
            "maps_url": row["maps_url"],
            "social_link": row["social_link"] if "social_link" in row.keys() else None,
            "email": row["email"],
            "status": row["status"],
            "wa_url": wa_url,
        })

    return render_template(
        "index.html",
        leads=leads,
        status_filter=status_filter,
        counts=counts,
    )


@app.route("/status/<int:lead_id>", methods=["POST"])
def update_status(lead_id: int):
    new_status = request.form.get("status")
    if new_status not in ("new", "contacted", "rejected"):
        return jsonify({"error": "invalid status"}), 400

    conn = get_db()
    conn.execute("UPDATE restaurants SET status = ? WHERE id = ?", (new_status, lead_id))
    conn.commit()
    conn.close()

    # Return to the same filter view the user was on
    return_filter = request.form.get("return_filter", "all")
    return redirect(url_for("index", status=return_filter))


if __name__ == "__main__":
    app.run(debug=True, port=5050)
