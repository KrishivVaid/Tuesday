import pyttsx3
import requests
import speech_recognition as sr
import datetime
import os
import socket
import json
from google.cloud import dialogflow_v2 as dialogflow
# Configuration and Global Variables
# Dialogflow configuration
DIALOGFLOW_PROJECT_ID = 'YOUR PROJECT ID '    
DIALOGFLOW_SESSION_ID = 'YOUR SESSION ID '        

# Gemini API key (if needed; not used by default) default it gives response of prefed queries/questions
GEMINI_API_KEY = 'YOUR API KEY '

# File to store the last used voice
VOICE_FILE = "last_used_voice.txt"
# Initialize pyttsx3

engine = pyttsx3.init('sapi5')
voices = engine.getProperty('voices')

# You may have fewer or more voices. Adjust indices if needed.
tuesday_voice = voices[0]  # Typically male voice
friday_voice = voices[1]   # Typically female voice
# Persist Last-Used Voice
def load_last_used_voice():
    """Load the last used voice (tuesday or friday) from a file."""
    if os.path.exists(VOICE_FILE):
        with open(VOICE_FILE, "r") as file:
            return file.read().strip().lower()
    return "tuesday"

def save_last_used_voice(voice_name):
    """Save the current voice (tuesday or friday) to a file."""
    with open(VOICE_FILE, "w") as file:
        file.write(voice_name.lower())

# Set initial voice based on saved file
last_used_voice = load_last_used_voice()
if last_used_voice == "friday":
    engine.setProperty('voice', friday_voice.id)
else:
    engine.setProperty('voice', tuesday_voice.id)
# TTS: speak()
def speak(text):
    """Speak the provided text using pyttsx3."""
    engine.say(text)
    engine.runAndWait()
# Greeting
def greet(voice_name="Tuesday"):
    """Greet based on current time and voice name."""
    hour = int(datetime.datetime.now().hour)
    if 0 <= hour < 12:
        speak(f"Good morning! I'm {voice_name}. How may I help you?")
    elif 12 <= hour < 18:
        speak(f"Good afternoon! I'm {voice_name}. How may I help you?")
    else:
        speak(f"Good evening! I'm {voice_name}. How may I help you?")

# Speech Recognition
def take_command():
    """
    Listen via microphone and return recognized text.
    Retries up to 3 times. Returns None if unrecognized.
    """
    r = sr.Recognizer()
    retries = 0
    
    while retries < 3:
        with sr.Microphone() as source:
            print("Listening...")
            r.pause_threshold = 1
            try:
                audio = r.listen(source, timeout=10, phrase_time_limit=5)
                print("Recognizing...")
                query = r.recognize_google(audio, language='en-in')
                print(f"User said: {query}\n")
                return query
            except sr.WaitTimeoutError:
                speak("I didn't hear anything, please say that again.")
            except sr.UnknownValueError:
                speak("I'm sorry, I didn't quite catch that. Could you please clarify?")
            except sr.RequestError:
                speak("Sorry, there was an issue with the speech service. Please try again.")
        
        retries += 1
    
    speak("I couldn't catch your voice after several attempts. Please check your microphone.")
    return None
# Network / Online Check
def is_online():
    """Check internet connectivity by connecting to 8.8.8.8:53."""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except OSError:
        return False

# Basic Offline Q&A
def basic_questions(query):
    """
    Provides some basic offline answers if Dialogflow
    can't be reached or doesn't have an answer.
    """
    q_lower = query.lower()

    # "Hey Tuesday" or "Hey Friday" checks
    if "hey tuesday" in q_lower or "tuesday" in q_lower:
        if "what time" in q_lower:
            return f"The time is {datetime.datetime.now().strftime('%H:%M:%S')}."
        elif "how are you" in q_lower:
            return "I'm doing great, thank you for asking!"
    elif "hey friday" in q_lower or "friday" in q_lower:
        if "what time" in q_lower:
            return f"The time is {datetime.datetime.now().strftime('%H:%M:%S')}."
        elif "how are you" in q_lower:
            return "I'm doing great, thank you for asking!"

    # Generic checks
    if "how are you" in q_lower:
        return "I'm doing great, thank you for asking!"
    elif "what time" in q_lower:
        return f"The time is {datetime.datetime.now().strftime('%H:%M:%S')}."
    elif "what day" in q_lower or "what is today" in q_lower:
        return f"Today is {datetime.datetime.now().strftime('%A')}, {datetime.datetime.now().strftime('%B %d, %Y')}."
    elif "who are you" in q_lower or "what is your name" in q_lower:
        return "I'm your virtual assistant, here to help you with anything!"
    elif "where are you from" in q_lower or "where do you live" in q_lower:
        return "I live in the digital world, on your device. I'm always here to help."
    elif "purpose" in q_lower or "why are you here" in q_lower:
        return "I'm here to assist you with any queries or tasks you may have."
    
    # No match
    return None

#######################################
# Dialogflow Integration
#######################################

def ask_dialogflow(query):
    """
    Sends the user query to Dialogflow and returns the fulfillment text.
    """
    try:
        client = dialogflow.SessionsClient()
        session = client.session_path(DIALOGFLOW_PROJECT_ID, DIALOGFLOW_SESSION_ID)
        
        text_input = dialogflow.TextInput(text=query, language_code="en")
        query_input = dialogflow.QueryInput(text=text_input)
        
        response = client.detect_intent(request={"session": session, "query_input": query_input})
        return response.query_result.fulfillment_text.strip()
    except Exception as e:
        print(f"Dialogflow error: {e}")
        return None

def chat_with_bot(query):
    """
    High-level function to handle user query:
    1) Check internet & try Dialogflow
    2) If offline or no answer, fallback to basic_questions
    """
    if is_online():
        df_answer = ask_dialogflow(query)
        if df_answer:
            return df_answer
        else:
            offline_answer = basic_questions(query)
            return offline_answer if offline_answer else "I couldn't find an answer. Please try rephrasing."
    else:
        offline_answer = basic_questions(query)
        if offline_answer:
            return offline_answer
        else:
            return "I'm offline and I can't find an answer to that. Please try again later."

#######################################
# Voice Switching
#######################################

def set_voice(gender="tuesday"):
    """Switch between Tuesday (male) and Friday (female) voices."""
    global engine
    gender_lower = gender.lower()
    
    if gender_lower == "friday":
        engine.setProperty('voice', friday_voice.id)
        save_last_used_voice("friday")
        speak("Voice switched to Friday, your female assistant.")
    else:
        # Default to Tuesday if not recognized or if "tuesday"
        engine.setProperty('voice', tuesday_voice.id)
        save_last_used_voice("tuesday")
        speak("Voice switched to Tuesday, your male assistant.")

#######################################
# Conversation Modes
#######################################

def text_to_text_chat():
    """
    Text-to-Text mode:
    - User types text
    - Assistant prints response AND speaks it
    - User can switch modes by typing "change mode to speech to speech", etc.
    """
    print("You are now in Text-to-Text mode. Type 'bye' to exit or 'change mode to X' to switch mode.\n")

    while True:
        query = input("You: ").strip()
        if not query:
            continue
        
        # Check for exit
        if query.lower() in ["exit", "quit", "bye"]:
            print("Exiting Text-to-Text mode.")
            return None
        
        # Mode switching
        if "change mode to speech to speech" in query.lower():
            speak("Switching to Speech-to-Speech mode.")
            return "speech-to-speech"
        elif "change mode to speech to text" in query.lower():
            speak("Switching to Speech-to-Text mode.")
            return "speech-to-text"
        elif "change mode to text to text" in query.lower():
            speak("You are already in Text-to-Text mode.")
            continue

        # Voice switching
        if "switch voice to friday" in query.lower():
            set_voice("friday")
            continue
        elif "switch voice to tuesday" in query.lower():
            set_voice("tuesday")
            continue

        # Normal chat
        response = chat_with_bot(query)
        print(f"Bot: {response}")
        speak(response)

def speech_to_text_chat():
    """
    Speech-to-Text mode:
    - User speaks
    - Assistant prints recognized text + the response
    - Assistant DOES NOT speak the response
    - Mode can be changed if user says "change mode to text to text", etc.
    """
    speak("You are now in Speech-to-Text mode. Say 'change mode to ...' or 'bye' to exit.")
    
    while True:
        query = take_command()
        if not query:
            continue
        
        # Check for exit
        if query.lower() in ["exit", "quit", "bye"]:
            speak("Exiting Speech-to-Text mode.")
            return None
        
        # Mode switching
        if "change mode to speech to speech" in query.lower():
            speak("Switching to Speech-to-Speech mode.")
            return "speech-to-speech"
        elif "change mode to speech to text" in query.lower():
            speak("You are already in Speech-to-Text mode.")
            continue
        elif "change mode to text to text" in query.lower():
            speak("Switching to Text-to-Text mode.")
            return "text-to-text"

        # Voice switching
        if "switch voice to friday" in query.lower():
            set_voice("friday")
            continue
        elif "switch voice to tuesday" in query.lower():
            set_voice("tuesday")
            continue

        # Normal chat
        response = chat_with_bot(query)
        print(f"You said: {query}")
        print(f"Bot: {response}")

def speech_to_speech_chat():
    """
    Speech-to-Speech mode:
    - User speaks
    - Assistant speaks back the response
    - User can say "change mode to text to text" etc. to switch mode
    """
    speak("You are now in Speech-to-Speech mode. Say 'change mode to ...' or 'bye' to exit.")

    while True:
        query = take_command()
        if not query:
            continue
        
        # Check for exit
        if query.lower() in ["exit", "quit", "bye"]:
            speak("Exiting Speech-to-Speech mode.")
            return None
        
        # Mode switching
        if "change mode to speech to speech" in query.lower():
            speak("You are already in Speech-to-Speech mode.")
            continue
        elif "change mode to speech to text" in query.lower():
            speak("Switching to Speech-to-Text mode.")
            return "speech-to-text"
        elif "change mode to text to text" in query.lower():
            speak("Switching to Text-to-Text mode.")
            return "text-to-text"

        # Voice switching
        if "switch voice to friday" in query.lower():
            set_voice("friday")
            continue
        elif "switch voice to tuesday" in query.lower():
            set_voice("tuesday")
            continue

        # Normal chat
        response = chat_with_bot(query)
        print(f"You said: {query}")
        print(f"Bot: {response}")
        speak(response)

#######################################
# Initial Mode Selection by Key
#######################################

def choose_mode_by_key():
    """
    Prompt the user to select a mode by typing 1, 2, or 3:
    1 -> Text-to-Text
    2 -> Speech-to-Text
    3 -> Speech-to-Speech
    Returns a string: "text-to-text", "speech-to-text", or "speech-to-speech".
    """
    speak("Please select a mode by typing the corresponding number.")
    print("\nSelect a mode:")
    print("  1) Text-to-Text")
    print("  2) Speech-to-Text")
    print("  3) Speech-to-Speech")
    
    while True:
        choice = input("Enter 1, 2, or 3: ").strip()
        if choice == '1':
            speak("You selected Text-to-Text mode.")
            return "text-to-text"
        elif choice == '2':
            speak("You selected Speech-to-Text mode.")
            return "speech-to-text"
        elif choice == '3':
            speak("You selected Speech-to-Speech mode.")
            return "speech-to-speech"
        else:
            speak("Invalid choice. Please enter 1, 2, or 3.")

#######################################
# Main
#######################################

if __name__ == "__main__":
    # Greet user with last used voice
    greet(last_used_voice.capitalize())

    # Ask for mode by key
    mode = choose_mode_by_key()

    # Loop until user exits
    while True:
        if mode == "text-to-text":
            new_mode = text_to_text_chat()
        elif mode == "speech-to-text":
            new_mode = speech_to_text_chat()
        elif mode == "speech-to-speech":
            new_mode = speech_to_speech_chat()
        else:
            # If somehow invalid, re-choose
            new_mode = choose_mode_by_key()
        
        if new_mode:
            # The user switched mode
            mode = new_mode
        else:
            # The user typed or said "bye/exit/quit" -> break
            break
    
    speak("Goodbye! Have a great day.")
