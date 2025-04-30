import os
from api_gpt import extract_ingredients_from_input
from api_spoon import find_recipes_by_ingredients, get_detailed_recipes

# Beispielbildpfad – passe diesen gegebenenfalls an
image_path = "Testbilder/img_2.png"

if not os.path.exists(image_path):
    print(f"Bild nicht gefunden unter Pfad: {image_path}")
else:
    print("Starte Analyse des Bildes...")
    zutatenliste = extract_ingredients_from_input(image_path)
    print("\nExtrahierte Zutatenliste:")
    print(zutatenliste)

    if zutatenliste:
        rezepte = get_detailed_recipes(zutatenliste, number=3)
        print("\nGefundene detaillierte Rezepte:")
        for rezept in rezepte:
            print(f"{rezept['rezeptname']} (Health Score: {rezept.get('gesundheitsbewertung', 'k.A.')})")
            print(f"Link: {rezept.get('rezept_url')}")
            print(f"Video: {rezept.get('video_url')}\n")