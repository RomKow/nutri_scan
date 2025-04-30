from openai import OpenAI
import os
from dotenv import load_dotenv
import json
import requests

# Lade Umgebungsvariablen aus .env (inkl. OPENAI_API_KEY)
load_dotenv()

# OpenAI-Client initialisieren
client = OpenAI(api_key=os.getenv("openai_api_key"))

def get_recipe_suggestions(lebensmittel_liste):
    """
    Fragt bei OpenAI 3 Rezeptvorschläge an, basierend auf einer Liste von Lebensmitteln oder einem Bild von Lebensmittel oder Kühlschrankinhalt.

    Args:
        lebensmittel_liste (str): Vom Nutzer übergebene Zutatenbeschreibung z.B. ("Tomaten, Käse, Gurken")

    Returns:
        list of dict: Liste mit Rezeptvorschlägen und geschätztem Nutri-Score:
        [
            {"name": "Tomaten-Käse-Brot", "nutriscore": "B"},
            {"name": "Paprika-Wrap", "nutriscore": "A"},
            ...
        ]
    """
    prompt = f"""
Du bist ein professioneller Ernährungsberater und Chefkoch.
Ein Nutzer hat dir die folgenden Zutaten genannt: {lebensmittel_liste}.

Schlage bitte 3 kreative Gerichte vor, die diese Zutaten sinnvoll verwenden. Gib für jedes Rezept bitte:
- den Rezeptnamen
- den geschätzten Nutri-Score (A–E)

Gib deine Antwort bitte ausschließlich im folgenden JSON-Format zurück – ohne Einleitung oder zusätzlichen Text:

[
  {{ "name": "Rezeptname 1", "nutriscore": "A" }},
  {{ "name": "Rezeptname 2", "nutriscore": "B" }},
  {{ "name": "Rezeptname 3", "nutriscore": "C" }}
]
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=500
    )

    antwort = response.choices[0].message.content.strip()
    print("GPT Antwort:\n", antwort)

    try:
        json_start = antwort.find("[")
        rezepte = json.loads(antwort[json_start:])
    except json.JSONDecodeError:
        rezepte = [{"name": "Fehler beim Parsen", "nutriscore": "?"}]

    return rezepte



def get_step_by_step_instructions(rezepttitel, zutatenliste):
    """
    Fragt bei OpenAI eine ausführliche, nummerierte Schritt-für-Schritt-Anleitung an.

    Args:
        rezepttitel (str): Titel des Rezepts.
        zutatenliste (list of dict): Liste von Zutaten mit Namen und Mengen.

    Returns:
        list of str: Strukturierte Kochanleitung als Liste von Schritten.
    """
    zutaten_text = ", ".join([f"{z['menge']} {z['name']}" for z in zutatenliste])
    prompt = f"""
Du bist ein professioneller Chefkoch. Erstelle eine ausführliche Schritt-für-Schritt-Kochanleitung in Deutsch für das Rezept "{rezepttitel}" mit folgenden Zutaten:

{zutaten_text}

Gib genaue Mengen, Zubereitungszeiten und Tipps an. Gib die Anleitung als nummerierte Liste zurück. Verwende einfache, aber professionelle Sprache.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=700
    )

    inhalt = response.choices[0].message.content.strip()
    return inhalt.split("\n") if "\n" in inhalt else [inhalt]

#Testaufrufe
vorschlaege = get_recipe_suggestions("Tomaten, Käse, Brot")
#print(vorschlaege)
