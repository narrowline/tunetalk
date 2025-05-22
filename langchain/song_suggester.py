from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv, find_dotenv
import os
import logging
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(env_path):
    logger.debug(f"Loading .env file from: {env_path}")
    load_dotenv(env_path, verbose=True, override=True)
else:
    logger.error(f".env file not found at: {env_path}")
    raise RuntimeError(f".env file not found at: {env_path}")

# Initialize FastAPI app
app = FastAPI()

# Verify API key is available
api_key = os.getenv("OPENAI_API_KEY")
logger.debug(f"API Key loaded: {'Yes' if api_key else 'No'}")

if not api_key:
    raise RuntimeError("OPENAI_API_KEY environment variable is not set. Please check your .env file.")

class SongRequest(BaseModel):
    mood: str = ""
    activity: str = ""
    music_type: str = ""
    singer: str = ""
    language: str = ""

def get_openrouter_llm():
    try:
        # Get API key again to ensure it's still available
        current_api_key = os.getenv("OPENAI_API_KEY")
        if not current_api_key:
            raise ValueError("API key not found")
        
        logger.debug("Creating ChatOpenAI instance...")
        return ChatOpenAI(
            openai_api_base="https://openrouter.ai/api/v1",
            openai_api_key=current_api_key,
            model="tngtech/deepseek-r1t-chimera:free",
            temperature=0.7,
        )
    except Exception as e:
        logger.error(f"Error creating LLM instance: {str(e)}")
        raise

@app.post("/suggest-songs")
async def suggest_song(data: SongRequest):
    try:
        logger.debug(f"Received request with data: {data}")
        
        prompt_template = PromptTemplate(
            input_variables=["mood", "activity", "music_type", "singer", "language"],
            template = (
                "Answer strictly in English.\n"
                "Suggest exactly 3 {music_type} songs in {language} language.\n"
                "Songs must fit a {mood} mood and be good for {activity}.\n"
                "Preferably by {singer}.\n\n"
                "❗ Respond in this strict format only, with NO explanation or commentary:\n"
                "🎵 Song: <song 1>\n🎤 Artist: <artist 1>\n\n"
                "🎵 Song: <song 2>\n🎤 Artist: <artist 2>\n\n"
                "🎵 Song: <song 3>\n🎤 Artist: <artist 3>\n\n"
                "Only respond with the songs. Do not write anything else."
            )
        )

        prompt = prompt_template.format(**data.dict())
        logger.debug(f"Generated prompt: {prompt}")
        
        llm = get_openrouter_llm()
        logger.debug("LLM instance created successfully")
        
        response = llm.predict(prompt)
        logger.debug(f"Received response: {response}")
        # Split the response into multiple songs (assuming LLM returns multiple songs)
        lines = response.strip().split('\n')
        lines = [line.strip() for line in lines if line.strip()]
        songs = []
        temp_song = []

        # Start from the end, go in reverse to get last 3 songs
        for line in reversed(lines):
            if line.startswith("🎤 Artist:") or line.startswith("🎵 Song:"):
                temp_song.insert(0, line)
                if len(temp_song) == 2:
                    songs.insert(0, '\n'.join(temp_song))
                    temp_song = []
            if len(songs) == 3:
                break

        if not songs:
            songs = ["LLM did not return valid song format. Please try again."]
        
        # if not songs:
        #     songs = [response.strip()]  # Fallback to original response if parsing failed
            
        return {"songs": songs}
    except Exception as e:
        logger.error(f"Error in suggest_song: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    # Chitchat endpoint and LLM
class ChitchatRequest(BaseModel):
    query: str

def extract_direct_answer(response: str) -> str:
    """
    Extracts the short final answer and removes LLM reasoning or step-by-step thoughts.
    """
    lines = response.strip().splitlines()

    # Step 1: Remove meta-thinking lines
    filtered_lines = [
        line for line in lines
        if not line.lower().startswith((
            "okay", "i need", "let me", "first", "from what", "i should", 
            "i remember", "alright", "wait", "so the user", "since", "because", "as"
        ))
    ]

    # Step 2: Return first proper sentence with . ! or ?
    for line in filtered_lines:
        if line.strip() and line.strip()[-1] in ".!?":
            return line.strip()

    # Step 3: Fallback — return last 2 lines if nothing solid found
    return "\n".join(filtered_lines[-2:]) if filtered_lines else response.strip()

@app.post("/music-chitchat")
async def music_chitchat(data: ChitchatRequest):
    try:
        logger.debug(f"Received chitchat query: {data.query}")

        # Updated prompt allowing singer's personal info like relationships
        chitchat_prompt = PromptTemplate(
            input_variables=["query"],
            template=(
                "You are a helpful AI assistant who only talks about music, singers, bands, albums, concerts, and the music industry.\n"
                "You are also allowed to answer music-related personal topics of singers (like relationships, controversies, lifestyle) **only if they are relevant to public or musical context**.\n"
                "Avoid any off-topic discussion like politics, history, geography, sports, etc.\n\n"
                "Answer the question strictly in 2-4 lines, in English. Be direct, short, and conversational.\n"
                "Never explain, never reason, never think step-by-step. Just respond directly.\n\n"
                "Question: {query}\n"
                "Answer:"
            )
        )

        # Format prompt
        prompt = chitchat_prompt.format(query=data.query)
        logger.debug(f"Chitchat prompt: {prompt}")

        # Get LLM and get response
        llm = get_openrouter_llm()
        logger.debug("LLM instance ready.")
        llm_response = llm.predict(prompt)
        logger.debug(f"Raw LLM response: {llm_response}")

        # Clean response
        reply = extract_direct_answer(llm_response)
        logger.debug(f"Filtered reply: {reply}")

        return {"reply": reply}

    except Exception as e:
        logger.error(f"Error in music_chitchat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))