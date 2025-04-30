from flask import Flask, render_template, redirect, url_for
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

def load_recipes():
    """Load the recipes data for the current user"""
    try:
        with open("data/data.json", "r") as f:
            data = json.load(f)
        
        # Get the current user from environment variables
        current_user = os.environ.get("your_whatsapp")
        
        # Check if user exists in data
        if current_user in data["users"]:
            return data["users"][current_user]["saved_recipes"]
        else:
            return []
    except Exception as e:
        print(f"Error loading recipes: {e}")
        return []

@app.route("/")
def index():
    """Main page with list of recipes"""
    recipes = load_recipes()
    return render_template("index.html", all_found_recipes=recipes)


if __name__ == "__main__":
    app.run(debug=True) 