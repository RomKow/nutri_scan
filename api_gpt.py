import openai
from openai import OpenAI
import os
import base64
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("openai_api_key"))

def extract_ingredients_from_input(image_path: str = None, zutaten_liste: list = None) -> list:
    """
    Extrahiert eine cleane, englische Zutatenliste entweder aus einem Bild (Kühlschrankfoto)
    oder aus einer gegebenen Liste (z.B. von WhatsApp-Text).
    Rückgabe: Liste von Zutaten optimiert für Spoonacular.
    """

    if not image_path and not zutaten_liste:
        raise ValueError("Bitte entweder ein Bildpfad oder eine Zutatenliste übergeben.")

    if image_path:
        # Bild analysieren und Zutaten erkennen
        with open(image_path, "rb") as img_file:
            base64_img = base64.b64encode(img_file.read()).decode("utf-8")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "You are a professional chef and nutritionist helping people make meals from what they have in their fridge. Analyze the image of the fridge content. If you see clear food ingredients like fruits, vegetables, dairy, or meat, respond with a list of ingredients like: INGREDIENTS: ingredient1, ingredient2, ingredient3.\n If no usable food is visible, or it doesn't make sense to cook with what's shown, respond instead with a funny joke like: ChatGPT thinks: [your short and humorous comment here]\n. Do not explain anything."
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}
                        }
                    ]
                }
            ],
            max_tokens=300,
            temperature=0.3
        )
        gpt_text = response.choices[0].message.content
        return [item.strip().lower() for item in gpt_text.split(",")]

    if zutaten_liste:
        # Falls String übergeben wurde (nicht Liste), umwandeln
        if isinstance(zutaten_liste, str):
            zutaten_liste = [z.strip() for z in zutaten_liste.split(",")]

        prompt = (
            "Convert this list of food ingredients into clean, comma-separated English keywords for cooking APIs like Spoonacular:\n"
            + ", ".join(zutaten_liste)
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.3
        )
        gpt_text = response.choices[0].message.content
        return [item.strip().lower() for item in gpt_text.split(",")]

    return []
