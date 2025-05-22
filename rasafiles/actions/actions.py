# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

# from typing import Any, Text, Dict, List
#
# from rasa_sdk import Action, Tracker
# from rasa_sdk.executor import CollectingDispatcher
#
#
# class ActionHelloWorld(Action):
#
#     def name(self) -> Text:
#         return "action_hello_world"
#
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#
#         dispatcher.utter_message(text="Hello World!")
#
#         return []

# actions/actions.py

from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import random
import requests  #  for FastAPI cal
import logging

logger = logging.getLogger(__name__)


# --- ACTION: Chitchat Music Related ---
class ActionChitchatMusicRelated(Action):

    def name(self) -> Text:
        return "action_chitchat_music_related"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        user_query = tracker.latest_message.get('text')
        logger.info(f"User asked a music-related chitchat question: {user_query}")

        try:
            response = requests.post(
                "http://localhost:8000/music-chitchat",
                json={"query": user_query}
            )

            if response.status_code == 200:
                reply = response.json().get("reply", "Sorry, I couldn't find anything useful.")
                dispatcher.utter_message(text=reply)
            else:
                logger.error(f"Failed to get response from LangChain API: {response.status_code}")
                dispatcher.utter_message(text="Sorry, something went wrong while fetching the answer.")

        except Exception as e:
            logger.exception(f"Error during chitchat API call: {str(e)}")
            dispatcher.utter_message(text="I'm having trouble answering that right now.")

        return []


# --- ACTION: Suggest Songs ---

class ActionSuggestSong(Action):
    def name(self) -> Text:
        return "action_suggest_song"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        mood_options = ["happy", "sad", "romantic", "energetic", "peaceful", "angry", "nostalgic"]
        activity_options = ["driving", "working", "studying", "chilling", "partying", "exercising"]
        music_type_options = ["romantic", "rock", "lofi", "pop", "hip hop", "classical", "jazz"]
        singer_options = ["John Lennon", "Amy Winehouse", "Atif Aslam", " Freddie Mercury", "Elton John", "Ali zafar", "Adele", "Taylor Swift", "Ed Sheeran", "Arijit Singh"]
        language_options = ["Hindi", "Punjabi", "English", "Spanish", "Italian", "French"]

        mood = next(tracker.get_latest_entity_values("mood"), None)
        activity = next(tracker.get_latest_entity_values("activity"), None)
        music_type = next(tracker.get_latest_entity_values("music_type"), None)
        singer = next(tracker.get_latest_entity_values("singer"), None)
        language = next(tracker.get_latest_entity_values("language"), None)

        slot_values = {
            "mood": mood,
            "activity": activity,
            "music_type": music_type,
            "singer": singer,
            "language": language,
        }
        # Check if all values are None (user ne kuch nahi diya)
        if all(v is None for v in slot_values.values()):
            print("User ne koi slot nahi diya. Random values set ki ja rahi hain.")  # Debug
            slot_values = {
                "mood": random.choice(mood_options),
                "activity": random.choice(activity_options),
                "music_type": random.choice(music_type_options),
                "singer": random.choice(singer_options),
                "language": random.choice(language_options),
            }
        else:
            print("User ne kuch slots provide kiye hain. Sirf wahi slots use honge, baaqi empty rahenge.")  # Debug
            # Keep user-provided slots only, no random values
            slot_values = {k: v for k, v in slot_values.items() if v is not None}
        
        #  Check all entites 
        for key in ["mood", "activity", "music_type", "singer", "language"]:
            if key not in slot_values:
                slot_values[key] = ""

        try:
            print(f"Sending request to FastAPI with data: {slot_values}")  # Debug log
            response = requests.post("http://localhost:8000/suggest-songs", json=slot_values)
            response.raise_for_status()
            
            response_data = response.json()
            print(f"Received response from FastAPI: {response_data}")  # Debug log
            
            song_suggestions = response_data.get("songs", [])
            
            if not song_suggestions:
                print("No songs received from API")  # Debug log
                dispatcher.utter_message(text="Sorry, koi song suggestions nahi mile. Kya aap dobara try karenge?")
                return []

            message = "Here are some songs for your mood:\n\n"



            for song in song_suggestions:
                message += f"{song}\n\n"  # Song is already a formatted string

            dispatcher.utter_message(text=message.strip()) 
            review = "Do you like these suggestions? "
            dispatcher.utter_message(text=review) 
            

            return [
                SlotSet("mood", None),
                SlotSet("music_type", None),
                SlotSet("language", None),
                SlotSet("singer", None),
                SlotSet("activity", None),
            ]

        except requests.exceptions.ConnectionError:
            print("Connection error - FastAPI server might not be running")  # Debug log
            dispatcher.utter_message(text="Sorry, song suggestion server se connect nahi ho paa raha hai. Kya server chal raha hai?")
        except Exception as e:
            print(f"Error occurred: {str(e)}")  # Debug log
            dispatcher.utter_message(text="Sorry, songs suggest nahi ho paaye. Server error aaya hai.")

        return []

# rasa run --enable-api --cors "*" --debug
# uvicorn main:app --reload --port 8001   (fastapi)
# uvicorn song_suggester:app --reload --port 8000  (langchain)