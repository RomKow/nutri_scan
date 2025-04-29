import requests
import os
import json
from datetime import datetime

SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY")

def find_recipes_by_ingredients(ingredients, number=3, ranking=1, ignore_pantry=True):
    """
    Sucht nach Rezepten basierend auf einer Liste von Zutaten.

    Args:
        ingredients (list[str]): Liste der Zutaten (z.B. ["tomato", "cheese", "bread"]).
        number (int): Anzahl der gewünschten Rezepte.
        ranking (int): 1 = beste Übereinstimmung zuerst, 2 = maximale Verwendung der Zutaten.
        ignore_pantry (bool): Ob Vorratskammer-Zutaten ignoriert werden sollen.

    Returns:
        list[dict]: Liste der Rezeptdaten.
    """
    url = "https://api.spoonacular.com/recipes/findByIngredients"
    params = {
        "ingredients": ",".join(ingredients),
        "number": number,
        "ranking": ranking,
        "ignorePantry": str(ignore_pantry).lower(),
        "apiKey": SPOONACULAR_API_KEY
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"Fehler bei Rezeptsuche: {response.status_code}")
        return []

    return response.json()

def get_detailed_recipes(ingredients, number=3):
    """
    Führt eine erweiterte Rezeptsuche durch, inklusive Gesundheitsdaten, Rezeptlink und Anleitung.
    """
    rezepte = find_recipes_by_ingredients(ingredients, number=number)
    ergebnisse = []

    for rezept in rezepte:
        rezept_id = rezept.get("id")
        if not rezept_id:
            continue

        detail_url = f"https://api.spoonacular.com/recipes/{rezept_id}/information"
        detail_params = {
            "includeNutrition": "true",
            "apiKey": SPOONACULAR_API_KEY
        }

        detail_response = requests.get(detail_url, params=detail_params)
        if detail_response.status_code != 200:
            print(f" Fehler beim Abrufen von Details für Rezept {rezept_id}")
            continue

        detail_data = detail_response.json()
        daten = {
            "rezeptname": detail_data.get("title"),
            "bild_url": detail_data.get("image"),
            "gesundheitsbewertung": detail_data.get("healthScore"),
            "rezept_url": detail_data.get("sourceUrl"),
            "video_url": detail_data.get("video", "Kein Video verfügbar"),
            "zubereitung": [step["step"] for instruction in detail_data.get("analyzedInstructions", []) for step in instruction.get("steps", [])],
            "zutaten": [z["original"] for z in detail_data.get("extendedIngredients", [])],
            "nutrition": detail_data.get("nutrition", {})
        }

        ergebnisse.append(daten)

    return ergebnisse
