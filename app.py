from flask import Flask, request, jsonify
from flask_cors import CORS
import anthropic
import os
import re
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def send_notification(aufgabe_titel, antwort, feedback_html, aufgabe_text=""):
    api_key  = os.environ.get("RESEND_API_KEY", "")
    email_to = os.environ.get("EMAIL_TO", "finance@wifa.uni-leipzig.de")

    if not api_key:
        print("E-Mail-Fehler: RESEND_API_KEY nicht gesetzt")
        return

    aufgabe_block = (
        f'<h3 style="color:#1a3a6b">Aufgabenstellung</h3>'
        f'<div style="background:#e8eef8;border-left:4px solid #1a3a6b;padding:12px 16px;'
        f'margin-bottom:20px;font-size:14px;white-space:pre-wrap">{aufgabe_text}</div>'
        if aufgabe_text else ""
    )

    html_body = f"""
<html><body style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto;padding:20px">
  <h2 style="color:#1a3a6b;border-bottom:2px solid #1a3a6b;padding-bottom:8px">
    Neue Feedback-Einreichung</h2>
  <table style="width:100%;border-collapse:collapse;margin-bottom:20px">
    <tr><td style="padding:6px;font-weight:bold;width:120px">Aufgabe:</td>
        <td style="padding:6px">{aufgabe_titel}</td></tr>
    <tr style="background:#f5f4f0">
        <td style="padding:6px;font-weight:bold">Zeitpunkt:</td>
        <td style="padding:6px">{datetime.now().strftime('%d.%m.%Y um %H:%M Uhr')}</td></tr>
  </table>
  {aufgabe_block}
  <h3 style="color:#1a3a6b">Antwort des Studierenden</h3>
  <div style="background:#f5f4f0;border-left:4px solid #c8c4bc;padding:12px 16px;
              margin-bottom:20px;white-space:pre-wrap;font-size:14px">{antwort}</div>
  <h3 style="color:#1a3a6b">KI-Feedback</h3>
  <div style="background:#ffffff;border:1px solid #e0ddd6;border-radius:6px;
              padding:12px 16px;font-size:14px">{feedback_html}</div>
</body></html>"""

    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "from": "Investments Feedback <onboarding@resend.dev>",
                "to": [email_to],
                "subject": f"Feedback-Einreichung: {aufgabe_titel} – {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                "html": html_body
            }
        )
        if resp.status_code == 200 or resp.status_code == 201:
            print(f"E-Mail erfolgreich gesendet an {email_to}")
        else:
            print(f"E-Mail-Fehler: {resp.status_code} – {resp.text}")
    except Exception as e:
        print(f"E-Mail-Fehler: {e}")


SYSTEM_PROMPT = """Du bist Tutor für Investments (Bodie/Kane/Marcus) an der Universität Leipzig.
Dir werden die Aufgabenstellung, die Musterlösung und die Antwort eines Studenten übergeben.
Gib konstruktives Feedback auf Deutsch.

Pflicht: Deine Antwort MUSS für jede Teilaufgabe (a, b, c – soweit vorhanden) einen eigenen
<h3>-Abschnitt enthalten. Fülle jeden Abschnitt vollständig aus – brich niemals ab.

Regeln:
- Vergib KEINE Punkte oder Noten
- Gib IMMER Feedback zu ALLEN Teilaufgaben – auch wenn eine fehlt
- Wenn eine Teilaufgabe fehlt: <span style="color:#8b1a1a">✗ Diese Teilaufgabe wurde nicht beantwortet.</span>
- KRITISCH: Beziehe dich NUR auf das was der Student tatsächlich geschrieben hat.
  Unterstelle NIEMALS etwas das nicht explizit in der Studentenantwort steht.
- Gib AUSSCHLIESSLICH reinen HTML-Inhalt zurück – KEIN Markdown, KEINE ```-Blöcke,
  kein DOCTYPE, kein <html>, kein <body>

HTML-Format:
- Überschriften: <h3 style="color:#1a3a6b;font-size:14px;font-weight:600;margin:1rem 0 .3rem">Teil a) – Titel</h3>
- Absätze: <p style="margin:.2rem 0">Text</p>
- Listen: <ul style="margin:.3rem 0 .3rem 1.2rem"><li>Punkt</li></ul>
- Fettdruck: <strong>Text</strong>
- Richtig: <span style="color:#1a6640">✓ Text</span>
- Falsch/Fehlend: <span style="color:#8b1a1a">✗ Text</span>"""


def strip_html(html):
    """Entfernt HTML-Tags für lesbare Textdarstellung."""
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&sub;', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


@app.route("/bewerten", methods=["POST"])
def bewerten():
    data = request.get_json()
    antwort      = (data.get("antwort") or "").strip()
    aufgabe_html = (data.get("aufgabe") or "").strip()
    muster_html  = (data.get("musterloesung") or "").strip()
    aufgabe_titel = (data.get("titel") or "Offene Aufgabe").strip()

    if not antwort or len(antwort) < 20:
        return jsonify({"error": "Bitte eine ausführlichere Antwort eingeben."}), 400
    if not aufgabe_html:
        return jsonify({"error": "Aufgabenstellung fehlt."}), 400

    aufgabe_text  = strip_html(aufgabe_html)
    muster_text   = strip_html(muster_html) if muster_html else ""

    user_message = f"""Aufgabenstellung:
{aufgabe_text}

Musterlösung:
{muster_text}

Antwort des Studenten:
{antwort}"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )

    feedback_html = message.content[0].text
    send_notification(aufgabe_titel, antwort, feedback_html, aufgabe_html)
    return jsonify({"bewertung": feedback_html, "html": True})


@app.route("/")
def index():
    return "Server läuft."

@app.route("/test-email")
def test_email():
    send_notification("TEST", "Dies ist eine Test-Einreichung.", "<p>Test-Feedback funktioniert.</p>")
    api_key = os.environ.get("RESEND_API_KEY", "")
    return f"RESEND_API_KEY={'gesetzt (Länge=' + str(len(api_key)) + ')' if api_key else 'FEHLT'}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
