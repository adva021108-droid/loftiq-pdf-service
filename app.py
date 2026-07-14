"""Loftiq PDF service — a small Flask app that renders project data to PDF."""

from io import BytesIO

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

from generate_pdf import generate_report

app = Flask(__name__)
CORS(app)


@app.get("/health")
def health():
    """Liveness/readiness probe."""
    return jsonify({"status": "ok", "service": "loftiq-pdf-service"})


@app.post("/generate-pdf")
def generate_pdf():
    """Render posted project JSON to a PDF and return it as a download."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Request body must be valid JSON"}), 400
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400

    try:
        pdf_bytes = generate_report(data)
    except Exception as exc:  # noqa: BLE001 - surface a clean error to the client
        app.logger.exception("PDF generation failed")
        return jsonify({"error": "Failed to generate PDF", "detail": str(exc)}), 500

    filename = _download_name(data)
    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


def _download_name(data):
    """Derive a safe, human-friendly download filename from the project data."""
    raw = data.get("title") or data.get("project_name") or data.get("name") or "report"
    slug = "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in str(raw))
    slug = "-".join(slug.split()).strip("-_").lower() or "report"
    return f"{slug}.pdf"


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
