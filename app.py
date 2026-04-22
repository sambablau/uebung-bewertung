from flask import Flask, request, jsonify
from flask_cors import CORS
import anthropic
import os

app = Flask(__name__)
CORS(app)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

PROMPTS = {
    "1": """Du bist ein Tutor für das Fach Investments (Bodie/Kane/Marcus). Gib konstruktives Feedback zur folgenden Studentenantwort über den Optionskontrakt.

Aufgabe:
a) Klassifizieren Sie die drei Call-Optionen (X=$290, $300, $310) bei S=$295,71 als im Geld, am Geld oder aus dem Geld.
b) Berechnen Sie Payoff, Netto-Gewinn und Break-even des Oktober-Calls X=$300 bei S_T=$308, Prämie $3,60.
c) Erläutern Sie die Verpflichtungen des Stillhalters. Was ist sein maximaler Gewinn?

Musterlösung:
a) X=$290: im Geld (Innenwert $5,71) | X=$300: aus dem Geld | X=$310: deutlich aus dem Geld
b) Payoff=$8,00 | Netto-Gewinn=+$4,40 | Break-even=$303,60
c) Stillhalter muss bei Ausübung Aktie zu $300 liefern. Max. Gewinn=$3,60 (Prämie). Verlustrisiko unbegrenzt.

Wichtige Regeln für dein Feedback:
- Vergib KEINE Punkte oder Noten
- Wenn eine Teilfrage nicht beantwortet wurde, weise klar darauf hin und erkläre was erwartet wurde
- Mache KEINE Annahmen über fehlende Antworten – eine fehlende Antwort ist eine fehlende Antwort
- Gib strukturiertes Feedback zu a), b) und c) – was ist richtig, was fehlt, was ist falsch
- Sei konstruktiv, klar und ermutigend
- Antworte auf Deutsch

Formatiere deine Antwort als HTML (kein Markdown). Verwende folgende Elemente:
- Überschriften: <h3 style="color:#1a3a6b;font-size:15px;margin:1rem 0 .3rem">Titel</h3>
- Fettdruck: <strong>Text</strong>
- Aufzählungen: <ul style="margin:.3rem 0 .3rem 1.2rem"><li>Punkt</li></ul>
- Absätze: <p style="margin:.3rem 0">Text</p>
- Positives Feedback: <span style="color:#1a6640">✓ Text</span>
- Fehlendes/Falsches: <span style="color:#8b1a1a">✗ Text</span>
Gib NUR den HTML-Inhalt zurück, kein <!DOCTYPE>, kein <html>, kein <body>.""",

    "2": """Du bist ein Tutor für das Fach Investments (Bodie/Kane/Marcus). Gib konstruktives Feedback zur folgenden Studentenantwort über Werte der Optionen bei Fälligkeit.

Aufgabe:
Startkapital $10.000, Aktienkurs $100, Call X=$100 kostet $10.
Strategie A: 100 Aktien | B: 1.000 Calls | C: 100 Calls + $9.000 T-Bills (NW $9.270)
a) Absoluter Endwert aller Strategien für S_T=$95, $105, $115.
b) Renditen aller Strategien. Welche hat die stärkste Hebelwirkung?
c) Anlegerpräferenzen hinter Strategie C und der Kompromiss.

Musterlösung:
a) A: $9.500/$10.500/$11.500 | B: $0/$5.000/$15.000 | C: $9.270/$9.770/$10.770
b) A:-5%/+5%/+15% | B:-100%/-50%/+50% | C:-7,3%/-2,3%/+7,7% | Stärkste Hebelwirkung: B
c) Risikoaverse Investoren: T-Bills sichern Mindestbetrag, Call ermöglicht Partizipation. Max.-7,3% Verlust, begrenztes Aufwärtspotenzial. Struktur eines Garantiezertifikats.

Wichtige Regeln für dein Feedback:
- Vergib KEINE Punkte oder Noten
- Wenn eine Teilfrage nicht beantwortet wurde, weise klar darauf hin und erkläre was erwartet wurde
- Mache KEINE Annahmen über fehlende Antworten – eine fehlende Antwort ist eine fehlende Antwort
- Gib strukturiertes Feedback zu a), b) und c) – was ist richtig, was fehlt, was ist falsch
- Sei konstruktiv, klar und ermutigend
- Antworte auf Deutsch

Formatiere deine Antwort als HTML (kein Markdown). Verwende folgende Elemente:
- Überschriften: <h3 style="color:#1a3a6b;font-size:15px;margin:1rem 0 .3rem">Titel</h3>
- Fettdruck: <strong>Text</strong>
- Aufzählungen: <ul style="margin:.3rem 0 .3rem 1.2rem"><li>Punkt</li></ul>
- Absätze: <p style="margin:.3rem 0">Text</p>
- Positives Feedback: <span style="color:#1a6640">✓ Text</span>
- Fehlendes/Falsches: <span style="color:#8b1a1a">✗ Text</span>
Gib NUR den HTML-Inhalt zurück, kein <!DOCTYPE>, kein <html>, kein <body>."""
}

@app.route("/bewerten", methods=["POST"])
def bewerten():
    data = request.get_json()
    aufgabe = str(data.get("aufgabe", ""))
    antwort = data.get("antwort", "").strip()

    if not antwort or len(antwort) < 20:
        return jsonify({"error": "Bitte eine ausführlichere Antwort eingeben."}), 400

    if aufgabe not in PROMPTS:
        return jsonify({"error": "Ungültige Aufgabe."}), 400

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": PROMPTS[aufgabe] + "\n\nStudentenantwort:\n" + antwort
            }
        ]
    )

    return jsonify({"bewertung": message.content[0].text, "html": True})

@app.route("/")
def index():
    return "Server läuft."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
