import json
import os
import sqlite3
from flask import Flask, jsonify, request

app = Flask(__name__)
DB_PATH = "base44_leads.db"


def init_b2b_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS b2b_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name TEXT NOT NULL,
            category TEXT,
            zip_code TEXT,
            address TEXT,
            phone TEXT,
            email TEXT,
            website TEXT,
            status TEXT DEFAULT 'New',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


init_b2b_db()


@app.route("/api/b2b/leads", methods=["GET"])
def get_b2b_leads():
    category = request.args.get("category", "")
    zip_code = request.args.get("zip_code", "")
    has_email = request.args.get("has_email", "")

    query = "SELECT * FROM b2b_leads WHERE 1=1"
    params = []

    if category:
        query += " AND category LIKE ?"
        params.append(f"%{category}%")
    if zip_code:
        query += " AND zip_code = ?"
        params.append(zip_code)
    if has_email.lower() == "true":
        query += " AND email IS NOT NULL AND email != ''"

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    leads = [dict(row) for row in rows]
    return jsonify({"status": "success", "count": len(leads), "leads": leads})


@app.route("/api/b2b/status", methods=["POST"])
def update_lead_status():
    data = request.json
    lead_id = data.get("lead_id")
    new_status = data.get("status")

    if not lead_id or not new_status:
        return jsonify(
            {"status": "error", "message": "Missing lead_id or status"}
        ), 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE b2b_leads SET status = ? WHERE id = ?", (new_status, lead_id)
    )
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Lead status updated"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)