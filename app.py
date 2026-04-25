from flask import Flask, request, jsonify
from flask_cors import CORS
import anthropic
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

app = Flask(__name__)
CORS(app)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# ── E-Mail-Konfiguration ──────────────────────────────────────────────────────
# Zum Deaktivieren: EMAIL_ENABLED auf "false" setzen im Render Dashboard
# Variablen werden bei jedem Request neu gelesen (nicht nur beim Start)

def send_notification(aufgabe, antwort, feedback_html):
    """Sendet E-Mail-Benachrichtigung an den Professor."""
    email_enabled  = os.environ.get("EMAIL_ENABLED", "true").lower() == "true"
    email_from     = os.environ.get("EMAIL_FROM", "profdrfs@gmail.com")
    email_password = os.environ.get("EMAIL_PASSWORD", "").replace(" ", "")
    email_to       = os.environ.get("EMAIL_TO", "finance@wifa.uni-leipzig.de")

    print(f"E-Mail-Status: enabled={email_enabled}, from={email_from}, to={email_to}, password_set={bool(email_password)}")

    if not email_enabled:
        print("E-Mail deaktiviert (EMAIL_ENABLED=false)")
        return
    if not email_password:
        print("E-Mail-Fehler: EMAIL_PASSWORD nicht gesetzt")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Feedback-Einreichung: {aufgabe} – {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        msg["From"]    = email_from
        msg["To"]      = email_to

        html_body = f"""
<html><body style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto;padding:20px">
  <h2 style="color:#1a3a6b;border-bottom:2px solid #1a3a6b;padding-bottom:8px">
    Neue Feedback-Einreichung</h2>
  <table style="width:100%;border-collapse:collapse;margin-bottom:20px">
    <tr><td style="padding:6px;font-weight:bold;width:120px">Aufgabe:</td>
        <td style="padding:6px">{aufgabe}</td></tr>
    <tr style="background:#f5f4f0">
        <td style="padding:6px;font-weight:bold">Zeitpunkt:</td>
        <td style="padding:6px">{datetime.now().strftime('%d.%m.%Y um %H:%M Uhr')}</td></tr>
  </table>
  <h3 style="color:#1a3a6b">Antwort des Studierenden</h3>
  <div style="background:#f5f4f0;border-left:4px solid #c8c4bc;padding:12px 16px;
              margin-bottom:20px;white-space:pre-wrap;font-size:14px">{antwort}</div>
  <h3 style="color:#1a3a6b">KI-Feedback</h3>
  <div style="background:#ffffff;border:1px solid #e0ddd6;border-radius:6px;
              padding:12px 16px;font-size:14px">{feedback_html}</div>
</body></html>"""

        msg.attach(MIMEText(html_body, "html", "utf-8"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(email_from, email_password)
            server.sendmail(email_from, email_to, msg.as_string())
        print(f"E-Mail erfolgreich gesendet an {email_to}")
    except Exception as e:
        print(f"E-Mail-Fehler: {e}")

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

Wichtige Regeln:
- Vergib KEINE Punkte oder Noten
- Gib IMMER Feedback zu ALLEN drei Teilen a), b) und c) – jeden Teil einzeln mit eigenem <h3>-Abschnitt
- Wenn ein Teil fehlt: Schreibe IMMER '<span style="color:#8b1a1a">✗ Diese Teilaufgabe wurde nicht beantwortet. Bitte vergessen Sie nicht, alle Teile der Aufgabe zu bearbeiten.</span>'
- Mache KEINE Annahmen über fehlende Antworten – eine fehlende Antwort ist eine fehlende Antwort
- Sei konstruktiv, klar und auf Deutsch

Formatiere deine Antwort als HTML (kein Markdown). Verwende folgende Elemente:
- Überschriften: <h3 style="color:#1a3a6b;font-size:15px;margin:1rem 0 .3rem">Titel</h3>
- Fettdruck: <strong>Text</strong>
- Aufzählungen: <ul style="margin:.3rem 0 .3rem 1.2rem"><li>Punkt</li></ul>
- Absätze: <p style="margin:.3rem 0">Text</p>
- Positives Feedback: <span style="color:#1a6640">✓ Text</span>
- Fehlendes/Falsches: <span style="color:#8b1a1a">✗ Text</span>
Gib NUR den HTML-Inhalt zurück, kein <!DOCTYPE>, kein <html>, kein <body>.""",

    "2": """Du bist Tutor für Investments (Bodie/Kane/Marcus Kap. 20). Gib Feedback zur Antwort über Optionsstrategien im Vergleich.

Aufgabe: Ein Investor hat $10.500 zu investieren und vergleicht drei Strategien bei S_0=$105, X=$105, Call-Prämie=$10, T-Bill-Zins=5%.
a) Berechnen Sie die absoluten Payoffs für S_T=$95, $105, $115 für alle drei Strategien: A (100 Aktien), B (1.000 Calls), C (100 Calls + T-Bills).
b) Berechnen Sie die Renditen für alle drei Strategien bei den gleichen Szenarien.

Musterlösung (Lehrbuch: exakt 1.000 Calls à $10 = $10.000 investiert, restliche $500 in T-Bills):
a) A: $9.500/$10.500/$11.500 | B (1.000 Calls): $0/$0/$10.000 | C (100 Calls + $9.500 T-Bills): $9.270/$9.770/$10.770
b) A: −9,5%/0%/+9,5% | B: −100%/−100%/−4,8% | C: −11,7%/−6,9%/+2,6%

Wichtig: Strategie B kauft exakt 1.000 Calls (=$10.000), nicht 1.050. Die restlichen $500 bleiben uninvestiert oder gehen in T-Bills je nach Aufgabenstellung im Lehrbuch.

Regeln: Keine Punkte. IMMER Feedback zu a), b) UND c) – alle drei Teile ohne Ausnahme. Wenn eine Teilaufgabe fehlt: Schreibe IMMER '<span style="color:#8b1a1a">✗ Diese Teilaufgabe wurde nicht beantwortet. Bitte vergessen Sie nicht, alle Teile der Aufgabe zu bearbeiten.</span>'. Konstruktiv, auf Deutsch.
Formatiere als HTML: <h3> in #1a3a6b, ✓ grün (#1a6640), ✗ rot (#8b1a1a). Nur HTML-Inhalt.""",

    "uebung2_1": """Du bist ein Tutor für das Fach Investments (Bodie/Kane/Marcus). Gib konstruktives Feedback zur folgenden Studentenantwort über Protective Put und Covered Call.

Aufgabe:
Investor hält 100 Aktien à $100.
a) Protective Put: X=$95, Prämie $3. Payoff-Tabelle für S_T=$80,$95,$110. Minimaler Gesamtpayoff?
b) Covered Call: X=$110, Prämie $4. Payoff-Tabelle für S_T=$80,$110,$120. Maximaler Gesamtpayoff?
c) Vergleich: Welche schützt vor Verlusten, welche begrenzt Gewinne? Unterschied in der Anlegermentalität?

Musterlösung:
a) Protective Put – Payoff (ohne Prämie):
S_T=$80: Aktie $80 + Put $15 = Payoff $95 | Netto-Gewinn = $95 - $100 - $3 = -$8
S_T=$95: Aktie $95 + Put $0 = Payoff $95 | Netto-Gewinn = $95 - $100 - $3 = -$8
S_T=$110: Aktie $110 + Put $0 = Payoff $110 | Netto-Gewinn = $110 - $100 - $3 = +$7
Minimaler Payoff = $95 (= X). Die Frage fragt nach dem Payoff, NICHT nach dem Netto-Gewinn.

b) Covered Call – Payoff (ohne Prämie):
S_T=$80: Aktie $80 + Short Call $0 = Payoff $80 | Netto-Gewinn = $80 - $100 + $4 = -$16
S_T=$110: Aktie $110 + Short Call $0 = Payoff $110 | Netto-Gewinn = $110 - $100 + $4 = +$14
S_T=$120: Aktie $120 - Call $10 = Payoff $110 | Netto-Gewinn = $110 - $100 + $4 = +$14
Maximaler Payoff = $110 (= X). Die Prämie von $4 ist NICHT Teil des Payoffs. Die Frage fragt nach dem Payoff, NICHT nach dem Netto-Gewinn.

c) Protective Put schützt nach unten (Mindest-Payoff = X), lässt unbegrenzte Gewinne zu, kostet Prämie. Covered Call generiert Prämieneinnahmen, begrenzt aber Gewinne auf X. Protective Put = Versicherungsmentalität. Covered Call = Einkommenserzielung mit Verkaufsdisziplin.

Wichtige Regeln:
- Vergib KEINE Punkte oder Noten
- Gib IMMER Feedback zu ALLEN drei Teilen a), b) und c) – auch wenn eine Teilfrage fehlt
- Wenn eine Teilfrage fehlt: Schreibe IMMER explizit '<span style="color:#8b1a1a">✗ Diese Teilaufgabe wurde nicht beantwortet. Bitte vergessen Sie nicht, alle Teile der Aufgabe zu bearbeiten.</span>' und erkläre kurz was erwartet wurde
- Mache KEINE Annahmen über fehlende Antworten
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
- Gib IMMER Feedback zu ALLEN drei Teilen a), b) und c) – auch wenn eine Teilfrage fehlt
- Wenn eine Teilfrage fehlt: Schreibe IMMER explizit '<span style="color:#8b1a1a">✗ Diese Teilaufgabe wurde nicht beantwortet. Bitte vergessen Sie nicht, alle Teile der Aufgabe zu bearbeiten.</span>' und erkläre kurz was erwartet wurde
- Mache KEINE Annahmen über fehlende Antworten
- Konstruktiv, klar, ermutigend, auf Deutsch

Formatiere als HTML:
- Überschriften: <h3 style="color:#1a3a6b;font-size:14px;font-weight:600;margin:1rem 0 .3rem">Titel</h3>
- Fettdruck: <strong>Text</strong>
- Listen: <ul style="margin:.3rem 0 .3rem 1.2rem"><li>Punkt</li></ul>
- Absätze: <p style="margin:.2rem 0">Text</p>
- Richtig: <span style="color:#1a6640">✓ Text</span>
- Falsch/Fehlend: <span style="color:#8b1a1a">✗ Text</span>
Nur HTML-Inhalt, kein DOCTYPE/html/body.""",

    "uebung3_1": """Du bist ein Tutor für das Fach Investments (Bodie/Kane/Marcus). Gib konstruktives Feedback zur folgenden Studentenantwort über die Put-Call-Parität.

Aufgabe:
S₀=$110, C=$17, P=$5, r=5%, T=1J., X=$105.
a) Überprüfen Sie Put-Call-Parität: C+X/(1+r)ᵀ vs. P+S₀. Berechnen Sie beide Seiten.
b) Gilt Parität? Welches Portfolio ist über-/unterbewertet? Arbitragestrategie und risikofreier Gewinn?

Musterlösung:
a) C+PV(X) = $17+$100 = $117 | P+S₀ = $5+$110 = $115. Parität gilt NICHT.
b) Zerobond+Call ($117) überbewertet, Aktie+Put ($115) unterbewertet. Arbitrage: Kauf Aktie+Put für $115, Verkauf Zerobond+Call für $117 → risikofreier Gewinn = $2. Alle Cashflows bei T=1 gleich null (kein Risiko).

Wichtige Regeln:
- Vergib KEINE Punkte oder Noten
- Gib IMMER Feedback zu BEIDEN Teilen a) und b) – auch wenn eine Teilfrage fehlt
- Wenn eine Teilfrage fehlt: Schreibe IMMER explizit '<span style="color:#8b1a1a">✗ Diese Teilaufgabe wurde nicht beantwortet. Bitte vergessen Sie nicht, alle Teile der Aufgabe zu bearbeiten.</span>' und erkläre kurz was erwartet wurde
- Mache KEINE Annahmen über fehlende Antworten
- Konstruktiv, klar, ermutigend, auf Deutsch

Formatiere als HTML:
- Überschriften: <h3 style="color:#1a3a6b;font-size:14px;font-weight:600;margin:1rem 0 .3rem">Titel</h3>
- Fettdruck: <strong>Text</strong>
- Listen: <ul style="margin:.3rem 0 .3rem 1.2rem"><li>Punkt</li></ul>
- Absätze: <p style="margin:.2rem 0">Text</p>
- Richtig: <span style="color:#1a6640">✓ Text</span>
- Falsch/Fehlend: <span style="color:#8b1a1a">✗ Text</span>
Nur HTML-Inhalt, kein DOCTYPE/html/body.""",

    "uebung3_2": """Du bist ein Tutor für das Fach Investments (Bodie/Kane/Marcus). Gib konstruktives Feedback zur folgenden Studentenantwort über optionsähnliche Wertpapiere.

Aufgabe:
a) Wandelanleihe: Nennwert $1.000, Kupon $80, Laufzeit 10J., Baa (8,5%), Wandlungsverhältnis 25, Aktienkurs $50. Berechne Conversion Value. Erkläre warum Preis $1.255 über Conversion Value ($1.250) und Straight Bond Wert ($967) liegt.
b) Callable Bond: Welche Option hat der Emittent? Wie wirkt Kündigungsrecht auf den Preis?

Musterlösung:
a) Conversion Value = 25×$50 = $1.250. Preis $1.255 liegt über beiden Untergrenzen wegen Optionswert des Wandlungsrechts (= Call-Option auf Aktie).
b) Emittent hat Call-Option (Rückkaufrecht zu Call Price). Investor ist short in diesem Call → Preis Callable Bond = Straight Bond − Wert der Call-Option < Straight Bond.

Wichtige Regeln:
- Vergib KEINE Punkte oder Noten
- Gib IMMER Feedback zu BEIDEN Teilen a) und b) – auch wenn eine Teilfrage fehlt
- Wenn eine Teilfrage fehlt: Schreibe IMMER explizit '<span style="color:#8b1a1a">✗ Diese Teilaufgabe wurde nicht beantwortet. Bitte vergessen Sie nicht, alle Teile der Aufgabe zu bearbeiten.</span>' und erkläre kurz was erwartet wurde
- Mache KEINE Annahmen über fehlende Antworten
- Konstruktiv, klar, ermutigend, auf Deutsch

Formatiere als HTML:
- Überschriften: <h3 style="color:#1a3a6b;font-size:14px;font-weight:600;margin:1rem 0 .3rem">Titel</h3>
- Fettdruck: <strong>Text</strong>
- Listen: <ul style="margin:.3rem 0 .3rem 1.2rem"><li>Punkt</li></ul>
- Absätze: <p style="margin:.2rem 0">Text</p>
- Richtig: <span style="color:#1a6640">✓ Text</span>
- Falsch/Fehlend: <span style="color:#8b1a1a">✗ Text</span>
Nur HTML-Inhalt, kein DOCTYPE/html/body.""",

    "uebung4_1": """Du bist ein Tutor für Investments (Bodie/Kane/Marcus, Kap. 21). Gib Feedback zur Antwort über inneren Wert, Zeitwert und Bestimmungsgrößen.

Aufgabe: S₀=$60, X=$50, σ=40%, r=10%, T=1J., C=$17,67.
a) Berechne inneren Wert und Zeitwert.
b) Fünf Bestimmungsgrößen des Call-Werts + Richtung ihrer Wirkung.

Musterlösung:
a) Innerer Wert = max{$60−$50,0} = $10. Zeitwert = $17,67−$10 = $7,67.
b) S↑→C↑, X↑→C↓, σ↑→C↑, T↑→C↑, r↑→C↑, D↑→C↓.

Regeln: Keine Punkte. IMMER Feedback zu a) und b). Fehlende Teile IMMER explizit mit dem Satz '<span style="color:#8b1a1a">✗ Diese Teilaufgabe wurde nicht beantwortet. Bitte vergessen Sie nicht, alle Teile der Aufgabe zu bearbeiten.</span>' kennzeichnen. Konstruktiv, auf Deutsch.
Formatiere als HTML mit blauen h3-Überschriften, grünem ✓ und rotem ✗.""",

    "uebung4_2": """Du bist ein Tutor für Investments (Bodie/Kane/Marcus, Kap. 21). Gib Feedback zur Antwort über Grenzen für Optionswerte.

Aufgabe:
a) Drei Grenzen für den Call-Wert mit ökonomischer Intuition.
b) Warum ist vorzeitige Ausübung amerikanischer Calls (ohne Dividenden) wertlos? Was gilt für Puts?

Musterlösung:
a) C≥0, C≤S₀, C≥S₀−PV(X). Untere Grenze = adjustierter innerer Wert.
b) Call: lebend mehr wert als tot (Zeitwert aufgeben). C_amerikanisch=C_europäisch. Put: vorzeitige Ausübung kann optimal sein bei Insolvenz (Zeitwert des Geldes). C_amerikanisch>C_europäisch.

Regeln: Keine Punkte. IMMER Feedback zu a) und b). Fehlende Teile IMMER explizit mit dem Satz '<span style="color:#8b1a1a">✗ Diese Teilaufgabe wurde nicht beantwortet. Bitte vergessen Sie nicht, alle Teile der Aufgabe zu bearbeiten.</span>' kennzeichnen. Konstruktiv, auf Deutsch.
Formatiere als HTML mit blauen h3-Überschriften, grünem ✓ und rotem ✗.""",

    "uebung5_1": """Du bist ein Tutor für Investments (Bodie/Kane/Marcus, Kap. 21). Gib Feedback zur Antwort über das Binomialmodell.

Aufgabe: S₀=$100, u=1,20, d=0,90, X=$110, r=10%, T=1J.
a) Hedge Ratio H und fairer Call-Preis C.
b) C=$6,50 (überbewertet): Arbitragestrategie und Gewinn.

Musterlösung:
a) Su=$120→Cu=$10, Sd=$90→Cd=$0. H=(10−0)/(120−90)=1/3. Hedge: 1 Aktie−3 Calls. Payoff=$90 in beiden Fällen. PV=$81,82. $100−3C=$81,82 → C=$6,06.
b) Verkauf 3 Calls (+$19,50), Kauf 1 Aktie (−$100), Leihe $80,50. Risikofreier Gewinn = $1,45 in beiden Szenarien.

Regeln: Keine Punkte. IMMER Feedback zu a) und b). Fehlende Teile IMMER explizit mit dem Satz '<span style="color:#8b1a1a">✗ Diese Teilaufgabe wurde nicht beantwortet. Bitte vergessen Sie nicht, alle Teile der Aufgabe zu bearbeiten.</span>' kennzeichnen. Konstruktiv, auf Deutsch.
Formatiere als HTML mit blauen h3-Überschriften, grünem ✓ und rotem ✗.""",

    "uebung5_2": """Du bist ein Tutor für Investments (Bodie/Kane/Marcus, Kap. 21). Gib Feedback zur Antwort über die Black-Scholes-Formel.

Aufgabe: S₀=$100, X=$95, T=0,25J., σ=50%, r=10%.
a) d₁, d₂, N(d₁)=0,6664, N(d₂)=0,5714 und C₀.
b) P₀ via Put-Call-Parität und Black-Scholes-Put-Formel.

Musterlösung:
a) d₁=0,43, d₂=0,18. C₀=$100×0,6664−$95×e^(−0,025)×0,5714=$66,64−$52,94=$13,70.
b) P₀=C₀+X·e^(−rT)−S₀=$13,70+$92,65−$100=$6,35. Black-Scholes-Put: P₀=$95×0,9753×0,4286−$100×0,3336=$39,71−$33,36=$6,35.

Regeln: Keine Punkte. IMMER Feedback zu a) und b). Fehlende Teile IMMER explizit mit dem Satz '<span style="color:#8b1a1a">✗ Diese Teilaufgabe wurde nicht beantwortet. Bitte vergessen Sie nicht, alle Teile der Aufgabe zu bearbeiten.</span>' kennzeichnen. Konstruktiv, auf Deutsch.
Formatiere als HTML mit blauen h3-Überschriften, grünem ✓ und rotem ✗.""",

    "uebung6_1": """Du bist ein Tutor für Investments (Bodie/Kane/Marcus, Kap. 21). Gib Feedback zur Antwort über Delta, Elastizität und Portfolio Insurance.

Aufgabe: Portfolio $100 Mio., Put-Delta=−0,6.
a) Delta-Formel für Call/Put. Elastizität berechnen: S=$120, C=$5, Delta=0,6.
b) Aktien- und T-Bill-Position für synthetische PI. Zeige Gleichheit bei 2% Rückgang.

Musterlösung:
a) Delta_Call=N(d₁), Delta_Put=N(d₁)−1. Elastizität=Delta×(S/C)=0,6×24=14,4.
b) Aktien=$40 Mio., T-Bills=$60 Mio. Verlust bei 2%: echt −$2Mio.+$1,2Mio.=−$0,8Mio.; synthetisch −2%×$40Mio.=−$0,8Mio.

Regeln: Keine Punkte. IMMER Feedback zu a) und b). Fehlende Teile IMMER explizit mit dem Satz '<span style="color:#8b1a1a">✗ Diese Teilaufgabe wurde nicht beantwortet. Bitte vergessen Sie nicht, alle Teile der Aufgabe zu bearbeiten.</span>' kennzeichnen. Konstruktiv, auf Deutsch.
Formatiere als HTML mit blauen h3-Überschriften, grünem ✓ und rotem ✗.""",

    "uebung6_2": """Du bist ein Tutor für Investments (Bodie/Kane/Marcus, Kap. 21). Gib Feedback zur Antwort über Delta-neutrales Hedging.

Aufgabe: 1.000 Puts, Delta=−0,453, Puts à $4,495, Aktie à $90.
a) Anzahl Aktien für Delta-neutral. Gesamtkosten der Position.
b) Konzept Delta-neutrales Hedging. Warum nicht perfekt? Rolle des Gamma?

Musterlösung:
a) 453 Aktien (=1.000×0,453). Kosten: $4.495+$40.770=$45.265.
b) Delta-neutral: Gesamtdelta=0, kleine Kursschwankungen egal. Wette nur auf Volatilität. Nicht perfekt wegen Gamma: Delta ändert sich bei Kursbewegungen → Rebalancing nötig. Großes Gamma → häufiges Rebalancing.

Regeln: Keine Punkte. IMMER Feedback zu a) und b). Fehlende Teile IMMER explizit mit dem Satz '<span style="color:#8b1a1a">✗ Diese Teilaufgabe wurde nicht beantwortet. Bitte vergessen Sie nicht, alle Teile der Aufgabe zu bearbeiten.</span>' kennzeichnen. Konstruktiv, auf Deutsch.
Formatiere als HTML mit blauen h3-Überschriften, grünem ✓ und rotem ✗.""",

    "uebung7_1": """Du bist Tutor für Investments (Bodie/Kane/Marcus Kap. 22). Gib Feedback zur Antwort über Futures-Grundlagen.
Aufgabe: Long-Futures Öl F_0=$72, 1.000 Barrel, Margin 10%.
a) Payoff-Tabelle für P_T=$68,$72,$76 (Long+Short), Nullsummenspiel zeigen.
b) Initial Margin, Rendite bei $1 Kursanstieg, Hebeleffekt.
Musterlösung: a) Gewinn Long=P_T−F_0: −$4k/$0/+$4k; Short umgekehrt; Summe immer 0. b) Margin=$7.200; $1.000/$7.200=13,9%; Hebel=10.
Regeln: Keine Punkte. IMMER Feedback zu a) und b). Fehlende Teile benennen. Deutsch.
HTML: h3 blau, ✓ grün, ✗ rot.""",

    "uebung7_2": """Du bist Tutor für Investments (Bodie/Kane/Marcus Kap. 22). Gib Feedback zur Antwort über Marking to Market.
Aufgabe: Long Silber-Futures, 5.000 Oz, F_0=$20,10. Preise: $20,20/$20,25/$20,18/$20,18/$20,21.
a) Tägliche MtM-Gewinne/-Verluste.
b) Summe = (P_T−F_0)×5.000 zeigen.
Musterlösung: a) Tag1:+$500,Tag2:+$250,Tag3:−$350,Tag4:$0,Tag5:+$150. b) Summe=$550=($20,21−$20,10)×5.000=$550✓.
Regeln: Keine Punkte. IMMER Feedback zu a) und b). Fehlende Teile benennen. Deutsch.
HTML: h3 blau, ✓ grün, ✗ rot.""",

    "uebung8_1": """Du bist Tutor für Investments (Bodie/Kane/Marcus Kap. 22). Gib Feedback zur Antwort über Hedging mit Öl-Futures.
Aufgabe: Öl-Produzent, 100.000 Barrel, F_0=$52/Barrel, Short Hedge.
a) Gesamterlös für P_T=$51,$52,$53.
b) Vorteil Hedging; was gibt Produzent auf?
Musterlösung: a) Immer $5.200.000 (= 100.000 × F_0). b) Planungssicherheit, aber kein Upside-Potenzial.
Regeln: Keine Punkte. IMMER Feedback zu a) und b). Fehlende Teile benennen. Deutsch.
HTML: h3 blau, ✓ grün, ✗ rot.""",

    "uebung8_2": """Du bist Tutor für Investments (Bodie/Kane/Marcus Kap. 22). Gib Feedback zur Antwort über Basisrisiko.
Aufgabe: 100 Oz Gold, S_0=$1.691, F_0=$1.696 (Short). Tag 5: S_5=$1.695, F_5=$1.699.
a) Gewinn/Verlust Kassa + Futures, Nettogewinn.
b) Basisrisiko: Basis-Änderung, warum Hedge nicht perfekt?
Musterlösung: a) +$400−$300=+$100. b) Basis: −$5→−$4 (Verengung $1/Oz). Hedge nicht perfekt weil Kassa und Futures unterschiedlich bewegt.
Regeln: Keine Punkte. IMMER Feedback zu a) und b). Fehlende Teile benennen. Deutsch.
HTML: h3 blau, ✓ grün, ✗ rot.""",

    "uebung9_1": """Du bist Tutor für Investments (Bodie/Kane/Marcus Kap. 22). Gib Feedback zur Antwort über Spot-Futures-Parität.
Aufgabe: S_0=$4.000, d=2%, r_f=1%, T=1J. F_akt=$3.965.
a) Fairer F_0, Arbitragestrategie, Gewinn.
b) Cost-of-Carry Intuition, warum F_0 < S_0?
Musterlösung: a) F_0=$3.960. Arbitrage: Leihe, kaufe Index, Short Futures → +$5 risikolos. b) d>r_f → Halten vorteilhaft → F_0<S_0.
Regeln: Keine Punkte. IMMER Feedback zu a) und b). Fehlende Teile benennen. Deutsch.
HTML: h3 blau, ✓ grün, ✗ rot.""",

    "uebung9_2": """Du bist Tutor für Investments (Bodie/Kane/Marcus Kap. 22). Gib Feedback zur Antwort über Futurespreise vs. erwartete Kassapreise.
Aufgabe: β=1,2, r_f=3%, Marktprämie=8%, S_0=$100, E(P_T)=$110.
a) k (CAPM), F_0, Vergleich mit E(P_T).
b) Warum F_0<E(P_T) bei positivem Beta? Erwartete Rendite Long-Futures?
Musterlösung: a) k=12,6%, F_0=$103<E(P_T)=$110. b) Positives Beta→k>r_f→F_0<E(P_T). Erwartete Rendite=$7 (Risikoprämie).
Regeln: Keine Punkte. IMMER Feedback zu a) und b). Fehlende Teile benennen. Deutsch.
HTML: h3 blau, ✓ grün, ✗ rot.""",

    "uebung10_1": """Du bist Tutor für Investments (Bodie/Kane/Marcus Kap. 23). Gib Feedback zur Antwort über Zins-Parität.
Aufgabe: E_0=$2/£, r_US=4%, r_UK=5%, T=1J. F_0=$1,97 (verletzt Parität).
a) Fairer F_0, Covered Interest Arbitrage, Gewinn.
b) Intuition Terminabschlag: warum F_0<E_0?
Musterlösung: a) F_0=$1,981. Arbitrage: Leihe £, tausche $, anlegen, Forward-Kauf → $0,0115 risikolos. b) UK-Zins>US-Zins→Pfund Terminabschlag→Anlageindifferenz.
Regeln: Keine Punkte. IMMER Feedback zu a) und b). Fehlende Teile benennen. Deutsch.
HTML: h3 blau, ✓ grün, ✗ rot.""",

    "uebung10_2": """Du bist Tutor für Investments (Bodie/Kane/Marcus Kap. 23). Gib Feedback zur Antwort über Währungsrisiko-Management.
Aufgabe: US-Exporteur, £2 Mio., Exposure $200.000 bei $0,10/£, Kontraktgröße £62.500, F_0=$1,40/£.
a) Hedge Ratio H, Kontraktanzahl.
b) Kompensation bei F_T=$1,30/£.
Musterlösung: a) H=£2 Mio., 32 Short-Kontrakte. b) Verlust −$200.000, Gewinn Futures +$200.000, Netto=$0✓.
Regeln: Keine Punkte. IMMER Feedback zu a) und b). Fehlende Teile benennen. Deutsch.
HTML: h3 blau, ✓ grün, ✗ rot.""",

    "uebung11_1": """Du bist Tutor für Investments (Bodie/Kane/Marcus Kap. 23). Gib Feedback zur Antwort über Aktienindexfutures.
Aufgabe: Portfolio β=0,8, $30 Mio., S&P 2.000, erwarteter Rückgang 2,5%, Multiplikator $50.
a) Portfolioverlust, Kontraktanzahl.
b) Kompensation bei 2,5% Rückgang.
Musterlösung: a) Verlust=$600.000, 240 Short-Kontrakte. b) 240×$2.500=$600.000✓.
Regeln: Keine Punkte. IMMER Feedback zu a) und b). Fehlende Teile benennen. Deutsch.
HTML: h3 blau, ✓ grün, ✗ rot.""",

    "uebung11_2": """Du bist Tutor für Investments (Bodie/Kane/Marcus Kap. 23). Gib Feedback zur Antwort über Zinsfutures.
Aufgabe: Portfolio $10 Mio., D*=9J., T-Bond-Futures D*=10J., Kurs $90, Multiplikator 1.000. 10 Bp Zinsanstieg.
a) PVBP Portfolio, PVBP Futures, Kontraktanzahl.
b) Kompensation bei 10 Bp.
Musterlösung: a) PVBP_P=$9.000, PVBP_F=$90, 100 Short-Kontrakte. b) −$90.000+$90.000=$0✓.
Regeln: Keine Punkte. IMMER Feedback zu a) und b). Fehlende Teile benennen. Deutsch.
HTML: h3 blau, ✓ grün, ✗ rot.""",

    "uebung12_1": """Du bist Tutor für Investments (Bodie/Kane/Marcus Kap. 23). Gib Feedback zur Antwort über Zinsswaps.
Aufgabe: $100 Mio. Anleihen (7% Kupon), Swap: zahle 7% fix, erhalte LIBOR. LIBOR=6,5%/7%/7,5%.
a) Netto-Einkommen für alle drei LIBOR-Szenarien.
b) Effektive Umwandlung? Vorteil gegenüber Anleihen-Verkauf?
Musterlösung: a) Netto=LIBOR×$100Mio.: $6,5/$7/$7,5 Mio. b) Variabel verzinslich. Schneller/billiger als Verkauf.
Regeln: Keine Punkte. IMMER Feedback zu a) und b). Fehlende Teile benennen. Deutsch.
HTML: h3 blau, ✓ grün, ✗ rot.""",

    "uebung12_2": """Du bist Tutor für Investments (Bodie/Kane/Marcus Kap. 23). Gib Feedback zur Antwort über Rohstoff-Futures.
Aufgabe: Orangensaft: r_f=5%, Marktprämie=8%, β=0,117, E(P_T)=$1,45, T=0,5J.
a) k, Barwert E(P_T), fairer F_0.
b) Warum kein Parität-Modell? Was stattdessen?
Musterlösung: a) k=5,94%, PV=$1,409, F_0=$1,444. b) Verderblich, saisonal→Parität gilt nicht. DCF mit risikoadjustierter Rate.
Regeln: Keine Punkte. IMMER Feedback zu a) und b). Fehlende Teile benennen. Deutsch.
HTML: h3 blau, ✓ grün, ✗ rot."""
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

    feedback_html = md_to_html(message.content[0].text)
    send_notification(aufgabe, antwort, feedback_html)
    return jsonify({"bewertung": feedback_html, "html": True})

@app.route("/")
def index():
    return "Server läuft."

@app.route("/test-email")
def test_email():
    """Test-Endpunkt: Rufe /test-email im Browser auf um E-Mail zu testen."""
    send_notification("TEST", "Dies ist eine Test-Einreichung.", "<p>Test-Feedback funktioniert.</p>")
    email_enabled  = os.environ.get("EMAIL_ENABLED", "true").lower() == "true"
    email_password = os.environ.get("EMAIL_PASSWORD", "").replace(" ", "")
    return (f"EMAIL_ENABLED={email_enabled}, "
            f"EMAIL_PASSWORD={'gesetzt (Länge=' + str(len(email_password)) + ')' if email_password else 'FEHLT'}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
