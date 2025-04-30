from twilio_whatsapp_client import WhatsAppBot
from data_manager import DataManager
from api_gpt import extract_ingredients_from_input
from api_spoon import find_recipes_by_ingredients, get_detailed_recipes
import re
import random
import os
import threading
from dotenv import load_dotenv
from flask_app import app as flask_app

# Load environment variables
load_dotenv()

# Create data manager instance
data_manager = DataManager()

class WhatsAppFoodApp:
    def __init__(self):
        self.initial_processing_complete = False
        self.new_message_sids = set()
        # Store last recipe suggestion for simple selection
        self.last_suggested_recipes = []
        self.bot = WhatsAppBot(message_callback=self.handle_message)
        
        # Current user tracking - use phone number from environment variable
        self.current_user = os.environ.get("your_whatsapp")
        print(f"Initializing app with user phone: {self.current_user}")
    
    def handle_message(self, message):
        """Process incoming WhatsApp messages and implement business logic"""
        # Skip messages from the bot itself
        if hasattr(message, 'author') and message.author == "system":
            return
        
        message_text = None
        image_location = None
        message_sid = getattr(message, 'sid', 'unknown')
        
        # Handle text message
        if hasattr(message, 'body'):
            print(f"📱 Message received: {message.body}")
            message_text = message.body
        
        # If we're in the initial processing phase, only track message SIDs
        # but don't download any images
        if not self.initial_processing_complete:
            # Just record that we've seen this message
            if hasattr(message, 'media') or hasattr(message, 'media_items'):
                print(f"⏭️ Skipping media download during initial processing: {message_sid}")
            return
        
        # Once initial processing is complete, any new message should be fully processed
        # Add this message to the set of new messages
        self.new_message_sids.add(message_sid)
        
        # Process the message based on content
        if message_text:
            # Check if this might be a recipe selection
            if self.last_suggested_recipes and self._is_recipe_selection(message_text):
                self._process_recipe_selection(message_text)
                return
            
            # If not a recipe selection, process as a regular text message
            self._process_text_message(message_text, message_sid)
        else:
            # Process media content
            image_location = self._process_media_content(message)
            if image_location:
                self._process_image(image_location, message_sid)
    
    def _is_recipe_selection(self, text):
        """Check if the text appears to be selecting a recipe"""
        # Check for common recipe selection patterns
        selection_patterns = [
            r'^[1-3]$',  # Just the number 1, 2, or 3
            r'^recipe\s*[1-3]$',  # "recipe 1", "recipe 2", etc.
            r'^number\s*[1-3]$',  # "number 1", "number 2", etc.
            r'^select\s*[1-3]$',  # "select 1", "select 2", etc.
            r'^choose\s*[1-3]$',  # "choose 1", "choose 2", etc.
            r'^I\s*want\s*[1-3]$',  # "I want 1", "I want 2", etc.
            r'^[1-3]\.?$',  # "1.", "2.", etc.
            r'^option\s*[1-3]$',  # "option 1", "option 2", etc.
        ]
        
        text = text.strip().lower()
        
        for pattern in selection_patterns:
            if re.match(pattern, text):
                return True
        
        return False
    
    def _extract_recipe_number(self, text):
        """Extract the recipe number (1-3) from selection text"""
        text = text.strip().lower()
        
        # Look for the first digit in the text
        for char in text:
            if char.isdigit() and char in ['1', '2', '3']:
                return int(char)
        
        # Default to 1 if we can't find a valid number
        return 1
    
    def _process_media_content(self, message):
        """Extract and save media from message"""
        media_list = []
        if hasattr(message, 'media') and isinstance(message.media, list):
            media_list = message.media
        elif hasattr(message, 'media_items'):
            media_list = message.media_items
        
        # Process any images
        for media_item in media_list:
            # Extract media info consistently
            media_type = (
                media_item.get('content_type') if isinstance(media_item, dict)
                else getattr(media_item, 'content_type', 'unknown')
            )
            media_sid = (
                media_item.get('sid') if isinstance(media_item, dict)
                else getattr(media_item, 'sid', 'unknown')
            )
            
            # We can potentially extract any kind of media here
            if media_type.startswith('image/'):
                print(f"📸 Processing image...")
                local_file = data_manager.save_media_to_img_folder(
                    service_sid=self.bot.service_sid,
                    media_sid=media_sid,
                    api_key=self.bot.api_key,
                    api_secret=self.bot.api_secret,
                    content_type=media_type
                )
                
                if local_file:
                    print(f"✅ Image saved: {local_file}")
                    return local_file
        
        return None
    
    def _process_image(self, image_path, message_sid):
        """Process image, extract ingredients and suggest recipes"""
        print(f"Image saved at: {image_path}")
        print("Starting image analysis...")
        
        # Extract ingredients from image
        try:
            print("Calling OpenAI API to extract ingredients...")
            zutatenliste = extract_ingredients_from_input(image_path)
            print("\nExtracted ingredients:")
            print(zutatenliste)
            
            # Check if we found valid ingredients or just non-food items
            if not zutatenliste or len(zutatenliste) < 2:
                # No ingredients or too few ingredients found
                humor_responses = [
                    "I'm looking for food ingredients, but my recipe radar isn't picking up much. 🔍",
                    "Hmm, I don't see anything I can turn into a delicious meal there. 🤔",
                    "My recipe powers are strong, but I need actual ingredients to work with! ✨",
                    "I'm great at suggesting recipes, but even I can't cook with what I'm seeing here. 🍳",
                    "I searched high and low but couldn't find enough ingredients to work with. 🧐",
                    "That's an interesting image, but I don't think it belongs in a recipe! 😄",
                    "I'm a foodie at heart, but I need actual food ingredients to suggest recipes. 🥗"
                ]
                humor_message = random.choice(humor_responses)
                
                response_message = f"{humor_message}\n\nPlease send a photo of food ingredients or list them in a text message like 'tomatoes, chicken, pasta'."
                self.bot.send_message(response_message)
                return
                
            # Get recipe suggestions
            try:
                # Inform user we're looking for recipes
                self.bot.send_message(f"I found these ingredients: {', '.join(zutatenliste)}\n\nLooking for recipes now...")
                
                print(f"Calling Spoonacular API to find recipes for: {zutatenliste}")
                rezepte = get_detailed_recipes(zutatenliste, number=3)
                print(f"\nFound {len(rezepte)} detailed recipes")
                
                if not rezepte:
                    response_message = "Unfortunately, I couldn't find any recipes with these ingredients. Try different ingredients."
                    self.bot.send_message(response_message)
                    return
                
                # Print recipe details for debugging
                for i, rezept in enumerate(rezepte):
                    print(f"Recipe {i+1}: {rezept.get('rezeptname')}")
                    print(f"  Health Score: {rezept.get('gesundheitsbewertung')}")
                    print(f"  URL: {rezept.get('rezept_url')}")
                
                # Store the recipes for potential selection
                self.last_suggested_recipes = rezepte
                
                # Format and send recipe response
                self._send_recipe_response(rezepte, zutatenliste)
                
            except Exception as e:
                print(f"Error getting recipes: {str(e)}")
                response_message = "I had trouble finding recipes. Please try again later."
                self.bot.send_message(response_message)
                
        except Exception as e:
            print(f"Error extracting ingredients: {str(e)}")
            response_message = "I encountered an error analyzing your image. Please try again later."
            self.bot.send_message(response_message)
    
    def _process_text_message(self, message_text, message_sid):
        """Process text message as ingredients list"""
        print(f"Text message: {message_text}")
        
        # Handle different text formats for ingredients
        try:
            # Check for common patterns indicating an ingredient list
            if ("," in message_text or  # Comma-separated list
                "\n" in message_text or  # Line-separated list
                len(message_text.split()) > 1):  # Multiple words
                
                print(f"Processing as ingredients list: {message_text}")
                
                # Strip common prefixes that might indicate a list
                clean_text = message_text
                prefixes = ["i have", "ingredients:", "ingredients", "food:"]
                for prefix in prefixes:
                    if clean_text.lower().startswith(prefix):
                        clean_text = clean_text[len(prefix):].strip()
                
                # Convert text to ingredient list using API
                print(f"Extracting ingredients from: {clean_text}")
                zutatenliste = extract_ingredients_from_input(zutaten_liste=clean_text)
                print(f"Extracted ingredients: {zutatenliste}")
                
                # Check if we found valid ingredients or just non-food items
                if not zutatenliste or len(zutatenliste) < 2:
                    # Too few ingredients to make meaningful suggestions
                    humor_responses = [
                        "I need a bit more to work with to create something delicious! 🍽️",
                        "My recipe creativity needs at least a few ingredients to spark. ✨",
                        "I'm afraid that's not enough for me to suggest something tasty. 😊",
                        "Even master chefs need more than that to make a proper meal! 👨‍🍳",
                        "I could suggest recipes with more ingredients - one or two just isn't enough. 🥄"
                    ]
                    humor_message = random.choice(humor_responses)
                    
                    response_message = f"{humor_message}\n\nPlease provide more ingredients (at least 2-3) separated by commas, like 'chicken, rice, carrots'."
                    self.bot.send_message(response_message)
                    return
                
                if zutatenliste:
                    # Inform user we're looking for recipes
                    self.bot.send_message("Looking for recipes with your ingredients...")
                    
                    # Get recipe suggestions
                    rezepte = get_detailed_recipes(zutatenliste, number=3)
                    print(f"Found {len(rezepte)} recipes")
                    
                    if rezepte:
                        # Store recipes for potential selection
                        self.last_suggested_recipes = rezepte
                        
                        # Send the recipe options
                        self._send_recipe_response(rezepte, zutatenliste)
                        return
                    else:
                        response_message = "I couldn't find any recipes with these ingredients. Try different ingredients or add more items to your list."
                        self.bot.send_message(response_message)
                        return
                else:
                    response_message = "I couldn't identify any food ingredients in your message. Please provide a list of ingredients separated by commas."
                    self.bot.send_message(response_message)
                    return
        except Exception as e:
            print(f"Error processing text ingredients: {str(e)}")
            response_message = "I had trouble processing your message. Please try again with a clear list of ingredients."
            self.bot.send_message(response_message)
            return
        
        # Default response for other messages
        response_message = ("Hello! Send me a photo of your refrigerator or a list of ingredients (e.g., 'tomatoes, cheese, chicken'), "
                           "and I'll suggest matching recipes for you.")
        self.bot.send_message(response_message)
    
    def _process_recipe_selection(self, message_text):
        """Process a recipe selection from the user"""
        if not self.last_suggested_recipes:
            # No recipes have been suggested
            self.bot.send_message("I don't have any recent recipe suggestions. Please send me ingredients first.")
            return
        
        # Extract the recipe number (1-3) from the message
        recipe_num = self._extract_recipe_number(message_text)
        
        # Validate the selection
        if recipe_num > len(self.last_suggested_recipes):
            self.bot.send_message("Sorry, I couldn't find that recipe. Please select from the options provided (1-3).")
            return
        
        # Get the selected recipe (adjust for 0-based indexing)
        selected_recipe = self.last_suggested_recipes[recipe_num - 1]
        
        # Save the recipe to the user's profile
        data_manager.save_recipe_for_user(self.current_user, selected_recipe)
        
        # Send the detailed recipe information
        self._send_detailed_recipe(selected_recipe)
    
    def _send_recipe_response(self, rezepte, zutatenliste):
        """Format and send recipe suggestions to user"""
        ingredients_text = ", ".join(zutatenliste)
        
        response = f"📋 *Ingredients found:*\n{ingredients_text}\n\n"
        response += "🍽️ *Here are 3 recipe suggestions for you:*\n\n"
        
        for i, rezept in enumerate(rezepte, 1):
            rezeptname = rezept.get('rezeptname', 'Unknown Recipe')
            gesundheitswert = rezept.get('gesundheitsbewertung', 'N/A')
            rezept_url = rezept.get('rezept_url', '#')
            zutaten = rezept.get('zutaten', [])
            
            # Format health score with emoji
            health_emoji = "🟢" if gesundheitswert and gesundheitswert > 70 else "🟡" if gesundheitswert and gesundheitswert > 40 else "🟠"
            
            response += f"*{i}. {rezeptname}* {health_emoji}\n"
            response += f"   Health Score: {gesundheitswert}/100\n"
            
            # Add a preview of ingredients if available
            if zutaten and len(zutaten) > 0:
                # Show up to 5 ingredients
                ingredient_preview = zutaten[:5]
                response += f"   Contains: {', '.join(ingredient_preview)}"
                if len(zutaten) > 5:
                    response += f" and {len(zutaten) - 5} more ingredients"
                response += "\n"
            
            response += f"   🔗 {rezept_url}\n\n"
        
        # Add a footer with selection instructions
        response += "To see detailed instructions for a recipe, reply with the number (1, 2, or 3).\n"
        response += "Or send another photo or list of ingredients for new suggestions! 🍳"
        
        self.bot.send_message(response)
    
    def _send_detailed_recipe(self, recipe):
        """Send detailed recipe information to the user"""
        rezeptname = recipe.get('rezeptname', 'Unknown Recipe')
        gesundheitswert = recipe.get('gesundheitsbewertung', 'N/A')
        rezept_url = recipe.get('rezept_url', '#')
        zutaten = recipe.get('zutaten', [])
        zubereitung = recipe.get('zubereitung', [])
        
        # Create the detailed response
        response = f"🍲 *{rezeptname}*\n\n"
        
        # Add health score
        response += f"Health Score: {gesundheitswert}/100\n\n"
        
        # Add all ingredients
        response += "*Ingredients:*\n"
        for zutat in zutaten:
            response += f"• {zutat}\n"
        response += "\n"
        
        # Add preparation instructions if available
        if zubereitung:
            response += "*Instructions:*\n"
            for i, step in enumerate(zubereitung[:10], 1):  # Limit to 10 steps to avoid message length issues
                response += f"{i}. {step}\n"
            
            if len(zubereitung) > 10:
                response += "...\n"
        
        # Add link to full recipe - make it more visible
        response += "\n*🔗 RECIPE LINK:*\n"
        response += f"{rezept_url}\n\n"
        
        # Add saved confirmation
        response += "✅ This recipe has been saved to your profile!\n\n"
        
        # Add footer
        response += "Want to try another recipe? Send me new ingredients or a photo of your fridge! 🥗"
        
        self.bot.send_message(response)
    
    def run(self):
        """Run the application"""
        try:
            # Setup the WhatsApp conversation
            self.bot.setup_conversation()
            
            print("\nStarting initial message processing (without downloading images)...")
            # Initial processing - process all messages but don't download images
            initial_messages = self.bot.process_recent_messages(limit=50)
            if not initial_messages:
                print("No messages found initially.")
            else:
                print(f"Processed {len(initial_messages)} message(s) during initialization.")
            
            # Set the flag to indicate we're done with initial processing
            self.initial_processing_complete = True
            print("\nInitial processing complete. Now downloading images for new messages only.")
            
            print("\nStarting automatic message polling (every 5 seconds, last 50 messages)...")
            print("Press Ctrl+C to stop polling.")
            
            # Start automatic polling - process all messages but images only for new ones
            self.bot.poll_for_new_messages(interval=5, limit=50, reset_history=False)
                
        except KeyboardInterrupt:
            print("\nProgram interrupted by user. Exiting.")
        except Exception as e:
            print(f"Error in main application: {e}")

def run_flask_app():
    """Run Flask web app in a separate thread"""
    flask_app.run(host='0.0.0.0', port=3007, debug=False, use_reloader=False)

# Run the application when executed directly
if __name__ == "__main__":
    print("=== Welcome to NutriScan ===")
    print("I'll help you find recipes based on the ingredients you have.")
    print("Starting the application...\n")
    
    # Start Flask web app in a separate thread
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()
    print("Web interface started at http://localhost:3007")
    
    # Initialize the WhatsApp application
    app = WhatsAppFoodApp()
    
    # Start the WhatsApp application
    app.run()
