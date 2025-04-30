import os
import requests
import json
from pathlib import Path
from datetime import datetime

class DataManager:
    def __init__(self, img_dir="img", data_dir="data"):
        """Initialize the DataManager with directories for storing media and data"""
        self.img_dir = Path(img_dir)
        self.img_dir.mkdir(exist_ok=True)
        
        # Add data directory for JSON storage
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Path to the main data file
        self.data_file = self.data_dir / "data.json"
        
        # Initialize data file if it doesn't exist
        if not self.data_file.exists():
            self._initialize_data_file()
    
    def _initialize_data_file(self):
        """Initialize the data file with an empty structure"""
        initial_data = {
            "users": {}
        }
        self.save_data(initial_data)
    
    def save_data(self, data):
        """Save data to the JSON file"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_data(self):
        """Load data from the JSON file"""
        if not self.data_file.exists():
            return {"users": {}}
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Error loading JSON data, initializing new data file")
            self._initialize_data_file()
            return {"users": {}}
    
    def get_user_data(self, phone_number):
        """Get user data by phone number"""
        data = self.load_data()
        if phone_number in data["users"]:
            return data["users"][phone_number]
        return None

    def save_media_to_img_folder(self, service_sid, media_sid, api_key, api_secret, content_type='image/jpeg'):
        """Download media from Twilio and save it to the img folder"""
        try:
            # Check if we've already downloaded this media
            extension = content_type.split('/')[-1] if '/' in content_type else 'bin'
            if extension == 'jpeg':
                extension = 'jpg'
            
            # Generate filename based on media_sid
            filename = f"media_{media_sid}.{extension}"
            filepath = self.img_dir / filename
            
            # Check if file already exists
            if filepath.exists():
                print(f"✅ Media already exists: {filepath}")
                return str(filepath)
            
            # Construct the media content URL
            media_content_url = f"https://mcs.us1.twilio.com/v1/Services/{service_sid}/Media/{media_sid}/Content"
            
            print(f"... Downloading media from: {media_content_url}")
            
            # Set up authentication
            auth = (api_key, api_secret)
            
            # Make the request with proper authentication
            response = requests.get(
                media_content_url, 
                auth=auth,
                headers={
                    'Accept': content_type,
                }
            )
            
            if response.status_code == 200:
                # Save the file
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                # Check file size to ensure we got actual content
                file_size = os.path.getsize(filepath)
                print(f"✅ Media saved to: {filepath} ({file_size} bytes)")
                
                return str(filepath)
            else:
                print(f"❌ Failed to download media: {response.status_code}")
                
                # Try alternate URL format as fallback
                alt_url = f"https://api.twilio.com/2010-04-01/Accounts/{api_key}/Messages/{media_sid}/Media/Content"
                print(f"🔄 Trying alternate URL: {alt_url}")
                
                alt_response = requests.get(alt_url, auth=auth)
                if alt_response.status_code == 200:
                    with open(filepath, 'wb') as f:
                        f.write(alt_response.content)
                    print(f"✅ Media saved to: {filepath}")
                    return str(filepath)
                else:
                    print(f"❌ Alternate method also failed: {alt_response.status_code}")
                
                return None
        except Exception as e:
            print(f"❌ Error downloading media: {str(e)}")
            return None 

    def save_user_data(self, phone_number):
        """Save user information to the data file"""
        data = self.load_data()
        
        # Create user entry if it doesn't exist
        if phone_number not in data["users"]:
            data["users"][phone_number] = {
                "created_at": datetime.now().isoformat(),
                "saved_recipes": []
            }
        
        self.save_data(data)
        return data["users"][phone_number] 

    def save_recipe_for_user(self, phone_number, recipe_data):
        """Save a selected recipe for a user"""
        data = self.load_data()
        
        # Ensure user exists
        if phone_number not in data["users"]:
            # Create user record if it doesn't exist
            data["users"][phone_number] = {
                "saved_recipes": []
            }
        
        # Create a recipe object with the requested fields
        recipe_to_save = {
            "rezeptname": recipe_data.get("rezeptname", "Unknown Recipe"),
            "bild_url": recipe_data.get("bild_url", ""),
            "gesundheitsbewertung": recipe_data.get("gesundheitsbewertung", 0),
            "rezept_url": recipe_data.get("rezept_url", ""),
            "video_url": recipe_data.get("video_url", ""),
            "zubereitung": recipe_data.get("zubereitung", []),
            "zutaten": recipe_data.get("zutaten", []),
            "saved_at": datetime.now().isoformat()
        }
        
        # Add recipe to user's saved recipes
        data["users"][phone_number]["saved_recipes"].append(recipe_to_save)
        
        # Save updated data
        self.save_data(data)
        print(f"Recipe saved for user {phone_number}")
        return True 