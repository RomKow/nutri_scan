import os
import time
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

class WhatsAppBot:
    def __init__(self, message_callback=None):
        # Load environment variables
        self.api_key = os.environ["api_key_sid"]
        self.api_secret = os.environ["api_key_secret"]
        self.account_sid = os.environ["account_sid"]
        self.service_sid = os.environ["conversation_service_id"]
        
        # Initialize the client
        self.client = Client(self.api_key, self.api_secret, self.account_sid)
        
        # Initialize conversation
        self.conversation = None
        self.last_processed_messages = set()  # Track messages by SID
        self.your_whatsapp = os.environ["your_whatsapp"]
        self.twilio_whatsapp = os.environ["twilio_whatsapp"]
        
        # Store the callback function
        self.message_callback = message_callback
    
    def setup_conversation(self):
        """Sets up the conversation - finds existing or creates new one"""
        # Check for existing conversations
        conversations = self.client.conversations.v1.services(self.service_sid).conversations.list(limit=50)
        
        print("Checking for existing conversations...")
        for conv in conversations:
            print(f"Found conversation: {conv.sid} - {conv.friendly_name}")
            
            # Check if this conversation has the user's WhatsApp number as a participant
            participants = self.client.conversations.v1.services(self.service_sid).conversations(
                conv.sid
            ).participants.list()
            
            for participant in participants:
                # Check if this participant's address matches your WhatsApp number
                if (hasattr(participant, 'messaging_binding') and 
                    participant.messaging_binding.get('address') == self.your_whatsapp):
                    print(f"Found conversation with your WhatsApp number: {conv.sid}")
                    self.conversation = conv
                    break
            
            # If we found our conversation, break out of the outer loop too
            if self.conversation:
                break

        # If no conversations exist, create a new one
        if not self.conversation:
            print("No existing conversations found. Creating a new one...")
            self.conversation = self.client.conversations.v1.services(self.service_sid).conversations.create(
                friendly_name="WhatsApp Test Conversation"
            )
            
            print(f"Created new conversation with SID: {self.conversation.sid}")
            
            # Add yourself as a WhatsApp participant to the new conversation
            try:
                participant = self.client.conversations.v1.services(self.service_sid).conversations(
                    self.conversation.sid
                ).participants.create(
                    messaging_binding_address=self.your_whatsapp,  # Your WhatsApp number
                    messaging_binding_proxy_address=self.twilio_whatsapp  # The hackathon WhatsApp number
                )
                print(f"Added participant with SID: {participant.sid}")
                
                print("===== IMPORTANT =====")
                print("Send a message from your WhatsApp now")
                print("Previous initiation of the conversation is required.")
                print("After you've sent a message, run this script again to send a response.")
                print("============================")
            except Exception as e:
                print(f"Error adding participant: {e}")
                print("This is expected if you're already a participant in another conversation.")
        else:
            print(f"Using existing conversation with SID: {self.conversation.sid}")
        
        return self.conversation
    
    def send_message(self, message_body):
        """Sends a message to the conversation"""
        if not self.conversation:
            print("No conversation available. Run setup_conversation() first.")
            return False
        
        try:
            message = self.client.conversations.v1.services(self.service_sid).conversations(
                self.conversation.sid
            ).messages.create(
                body=message_body
            )
            print(f"Message sent! Message SID: {message.sid}")
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            print("Make sure you've already sent a message from your WhatsApp first.")
            return False
    
    def clear_message_history(self):
        """Clears the tracked message history to force reprocessing of messages"""
        self.last_processed_messages.clear()
        print("Message history cleared. All messages will be reprocessed.")

    def process_recent_messages(self, limit=20, process_all=False):
        """Manually process the most recent messages"""
        if not self.conversation:
            print("No conversation available. Run setup_conversation() first.")
            return []
        
        print(f"Fetching {limit} most recent messages...")
        
        # Get latest messages, ordered by date (newest first)
        messages = self.client.conversations.v1.services(self.service_sid).conversations(
            self.conversation.sid
        ).messages.list(limit=limit, order='desc')
        
        # Determine which messages to process
        messages_to_process = []
        for message in messages:
            if process_all or message.sid not in self.last_processed_messages:
                messages_to_process.append(message)
                self.last_processed_messages.add(message.sid)
        
        if not messages_to_process:
            print("No new messages to process.")
            return []
        
        # Process the messages
        for message in messages_to_process:
            # Try to fetch message details directly from API
            message_detail = self.fetch_message_detail(message.sid)
            if message_detail:
                # Use the detailed message object with more information
                message = message_detail
            
            # Continue with regular processing...
            self._process_message(message)
        
        return messages_to_process

    def _process_message(self, message):
        """Internal method to process a single message"""
        # If a callback function is provided, call it with the message
        if self.message_callback:
            self.message_callback(message)

    def poll_for_new_messages(self, interval=5, limit=20, reset_history=False):
        """Polls for new messages every 'interval' seconds"""
        if not self.conversation:
            print("No conversation available. Run setup_conversation() first.")
            return
        
        print(f"Starting to poll for new messages every {interval} seconds...")
        print("Press Ctrl+C to stop polling.")
        
        # Option to reset message history
        if reset_history:
            self.clear_message_history()
        
        # Process existing messages initially
        initial_messages = self.process_recent_messages(limit=limit)
        if not initial_messages:
            print("No new messages found initially. Waiting for new messages...")
        
        try:
            while True:
                # Get latest messages and process any new ones
                new_messages = self.process_recent_messages(limit=limit)
                
                # If no new messages, just wait
                if not new_messages:
                    # Wait for the next polling interval
                    time.sleep(interval)
                    continue
                
                # Wait for the next polling interval
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\nStopped polling for messages.")

    def fetch_message_detail(self, message_sid):
        """Fetch detailed message information directly from the API"""
        try:
            # Get message detail from the Conversations API
            message_detail = self.client.conversations.v1.services(self.service_sid).conversations(
                self.conversation.sid
            ).messages(message_sid).fetch()
            
            return message_detail
        except Exception as e:
            print(f"Error fetching message detail: {e}")
            return None


if __name__ == "__main__":
    bot = WhatsAppBot()
    bot.setup_conversation()
    
    # Test message
    # bot.send_message("Hello from the WhatsApp Bot!")
    
    # Start polling for new messages every 5 seconds
    bot.poll_for_new_messages(5)
