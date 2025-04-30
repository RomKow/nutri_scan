# NutriScan Recipe App

NutriScan is a WhatsApp-based recipe suggestion tool with a web interface for viewing saved recipes.

## Features

- WhatsApp bot that suggests recipes based on ingredients (via text or image)
- Web interface to view and browse saved recipes
- Detailed recipe pages with ingredients, instructions, and links to original sources

## Setup

1. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Make sure your `.env` file has the following variables:

   ```
   # Twilio
   conversation_service_id=your_conversation_service_id
   account_sid=your_account_sid
   api_key_sid=your_api_key_sid
   api_key_secret=your_api_key_secret

   # OpenAI
   openai_api_key=your_openai_api_key

   # Spoonacular
   SPOONACULAR_API_KEY=your_spoonacular_api_key

   # WhatsApp
   your_whatsapp="whatsapp:+your_phone_number"
   twilio_whatsapp="whatsapp:+twilio_phone_number"
   ```

3. Run the application:

   ```
   python app.py
   ```

4. Access the web interface at: `http://localhost:3007`

## Usage

### WhatsApp Bot

- Send a list of ingredients as text (e.g., "chicken, rice, tomatoes")
- Or send a photo of your ingredients
- Select recipes by responding with a number (1, 2, or 3)

### Web Interface

- View all saved recipes at the home page
- Click on a recipe to see detailed instructions and ingredients
