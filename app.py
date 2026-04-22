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

    "uebung2_1": """Du bist ein Tutor für das Fach Investments (Bodie/Kane/Marcus). Gib konstruktives Feedback zur folgenden Studentenantwort über Protective Put und Covered Call.

Aufgabe:
Investor hält 100 Aktien à $100.
a) Protective Put: X=$95, Prämie $3. Payoff-Tabelle für S_T=$80,$95,$110. Minimaler Gesamtpayoff?
b) Covered Call: X=$110, Prämie $4. Payoff-Tabelle für S_T=$80,$110,$120. Maximaler Gesamtpayoff?
c) Vergleich: Welche schützt vor Verlusten, welche begrenzt Gewinne? Unterschied in der Anlegermentalität?

Musterlösung:
a) S_T=$80: Aktie $80 + Put $15 = $95 | S_T=$95: $95+$0=$95 | S_T=$110: $110+$0=$110. Min. Payoff=$95.
b) S_T=$80: $80+$0=$80 | S_T=$110: $110+$0=$110 | S_T=$120: $120−$10=$110. Max. Payoff=$110.
c) Protective Put schützt nach unten (kostet Prämie, unbegrenzte Gewinne). Covered Call generiert Einnahmen, begrenzt aber Gewinne auf X. Unterschied: Schutz vs. Einkommenserzielung.

Wichtige Regeln:
- Vergib KEINE Punkte oder Noten
- Fehlende Antworten klar als fehlend kennzeichnen, keine Annahmen
- Feedback zu a), b), c) – was richtig, was fehlt, was falsch
- Konstruktiv, klar, ermutigend, auf Deutsch

Formatiere als HTML:
- Überschriften: <h3 style="color:#1a3a6b;font-size:14px;font-weight:600;margin:1rem 0 .3rem">Titel</h3>
- Fettdruck: <strong>Text</strong>
- Listen: <ul style="margin:.3rem 0 .3rem 1.2rem"><li>Punkt</li></ul>
- Absätze: <p style="margin:.2rem 0">Text</p>
- Richtig: <span style="color:#1a6640">✓ Text</span>
- Falsch/Fehlend: <span style="color:#8b1a1a">✗ Text</span>
Nur HTML-Inhalt, kein DOCTYPE/html/body.""",

    "uebung2_2": """Du bist ein Tutor für das Fach Investments (Bodie/Kane/Marcus). Gib konstruktives Feedback zur folgenden Studentenantwort über Straddle und Bullen-Spread.

Aufgabe:
Straddle: Long Call X=$100 à $8 + Long Put X=$100 à $6 (Kosten=$14)
Bullen-Spread: Long Call X₁=$95 à $12 + Short Call X₂=$110 à $4 (Nettokosten=$8)
a) Payoff und Netto-Gewinn Straddle für S_T=$80,$100,$120.
b) Payoff und Netto-Gewinn Bullen-Spread für S_T=$80,$100,$120.
c) Auf was wettet der Straddle-Käufer? Markterwartungen für Bullen-Spread?

Musterlösung:
a) S_T=$80: Payoff=$20, Gewinn=+$6 | S_T=$100: Payoff=$0, Gewinn=−$14 | S_T=$120: Payoff=$20, Gewinn=+$6
b) S_T=$80: Payoff=$0, Gewinn=−$8 | S_T=$100: Payoff=$5, Gewinn=−$3 | S_T=$120: Payoff=$15, Gewinn=+$7
c) Straddle: Wette auf hohe Volatilität (egal ob rauf oder runter). Bullen-Spread: moderate Aufwärtserwartung, Kosten reduziert durch Short Call.

Wichtige Regeln:
- Vergib KEINE Punkte oder Noten
- Fehlende Antworten klar als fehlend kennzeichnen, keine Annahmen
- Feedback zu a), b), c) – was richtig, was fehlt, was falsch
- Konstruktiv, klar, ermutigend, auf Deutsch

Formatiere als HTML:
- Überschriften: <h3 style="color:#1a3a6b;font-size:14px;font-weight:600;margin:1rem 0 .3rem">Titel</h3>
- Fettdruck: <strong>Text</strong>
- Listen: <ul style="margin:.3rem 0 .3rem 1.2rem"><li>Punkt</li></ul>
- Absätze: <p style="margin:.2rem 0">Text</p>
- Richtig: <span style="color:#1a6640">✓ Text</span>
- Falsch/Fehlend: <span style="color:#8b1a1a">✗ Text</span>
Nur HTML-Inhalt, kein DOCTYPE/html/body."""
}

def md_to_html(text):
    import re
    # Tabellen entfernen (zu komplex, einfach weglassen)
    text = re.sub(r'\|.*\|.*\n', '', text)
    text = re.sub(r'\|[-| ]+\|\n', '', text)
    # Horizontale Linien entfernen
    text = re.sub(r'\n---+\n', '\n', text)
    # H2 ## 
    text = re.sub(r'(?m)^## (.+)$', r'<h3 style="color:#1a3a6b;font-size:14px;font-weight:600;margin:1rem 0 .3rem">\1</h3>', text)
    # H1 #
    text = re.sub(r'(?m)^# (.+)$', r'<h2 style="color:#1a1916;font-size:15px;font-weight:600;margin:.5rem 0 .5rem">\1</h2>', text)
    # Fettdruck **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # ✓ grün
    text = re.sub(r'✓ ?(.+)', r'<span style="color:#1a6640">✓ \1</span>', text)
    # ✗ rot
    text = re.sub(r'✗ ?(.+)', r'<span style="color:#8b1a1a">✗ \1</span>', text)
    # Listenpunkte - item
    lines = text.split('\n')
    result = []
    in_list = False
    for line in lines:
        if re.match(r'^- ', line):
            if not in_list:
                result.append('<ul style="margin:.3rem 0 .3rem 1.2rem">')
                in_list = True
            result.append('<li>' + line[2:] + '</li>')
        else:
            if in_list:
                result.append('</ul>')
                in_list = False
            if line.strip() == '':
                result.append('')
            else:
                result.append('<p style="margin:.2rem 0">' + line + '</p>')
    if in_list:
        result.append('</ul>')
    return '\n'.join(result)


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

    return jsonify({"bewertung": md_to_html(message.content[0].text), "html": True})

@app.route("/")
def index():
    return "Server läuft."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
