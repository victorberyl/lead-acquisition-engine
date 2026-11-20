import sqlite3
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
DB_PATH = "base44_leads.db"

def init_b2b_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS b2b_leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_name TEXT NOT NULL UNIQUE,
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
        print("[+] Database initialized successfully.")
    except Exception as e:
        print(f"[-] Database initialization error: {e}")

init_b2b_db()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/b2b/leads", methods=["GET"])
def get_b2b_leads():
    category = request.args.get("category", "")
    zip_code = request.args.get("zip_code", "")
    
    query = "SELECT * FROM b2b_leads WHERE 1=1"
    params = []
    
    if category:
        query += " AND category LIKE ?"
        params.append(f"%{category}%")
    if zip_code:
        query += " AND zip_code = ?"
        params.append(zip_code)
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    leads = [dict(row) for row in rows]
    return jsonify({"status": "success", "count": len(leads), "leads": leads})

@app.route("/api/b2b/leads/<int:lead_id>/status", methods=["PATCH"])
def update_lead_status(lead_id):
    data = request.json or {}
    new_status = data.get("status")
    
    if not new_status:
        return jsonify({"status": "error", "message": "Missing status"}), 400
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE b2b_leads SET status = ? WHERE id = ?", (new_status, lead_id))
    conn.commit()
    conn.close()
    
    return jsonify({"status": "success", "lead_id": lead_id, "status": new_status})

@app.route("/api/webhooks/lead", methods=["POST"])
def receive_webhook_lead():
    data = request.json or {}
    business_name = data.get("business_name")
    
    if not business_name:
        return jsonify({"status": "error", "message": "business_name required"}), 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO b2b_leads (business_name, category, zip_code, address, phone, email, website, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'New')
            ON CONFLICT(business_name) DO UPDATE SET
                phone=excluded.phone,
                email=excluded.email,
                status='New'
        """, (
            business_name,
            data.get("category", "Uncategorized"),
            data.get("zip_code", ""),
            data.get("address", ""),
            data.get("phone", ""),
            data.get("email", ""),
            data.get("website", "")
        ))
        conn.commit()
        return jsonify({"status": "success", "message": "Lead ingested successfully"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        conn.close()

if __name__ == "__main__":
    app.run(debug=True, port=5000)

