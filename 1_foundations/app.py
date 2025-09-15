from dotenv import load_dotenv
from openai import OpenAI
import json
import os
import requests
from pypdf import PdfReader
import gradio as gr


load_dotenv('../.env', override=True)

def push(text):
    try:
        response = requests.post(
            "https://api.pushover.net/1/messages.json",
            data={
                "token": os.getenv("PUSHOVER_TOKEN"),
                "user": os.getenv("PUSHOVER_USER"),
                "message": text,
            }
        )
        if response.status_code == 200:
            print(f"✅ Pushover notification sent successfully: {text}")
        else:
            print(f"❌ Pushover notification failed (status {response.status_code}): {response.text}")
    except Exception as e:
        print(f"❌ Pushover notification error: {e}")


def record_user_details(email, name="Name not provided", notes="not provided"):
    push(f"Recording {name} with email {email} and notes {notes}")
    return {"recorded": "ok"}

def record_message(question):
    push(f"Recording {question}")
    return {"recorded": "ok"}

record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The email address of this user"
            },
            "name": {
                "type": "string",
                "description": "The user's name, if they provided it"
            }
            ,
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context"
            }
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

record_message_json = {
    "name": "record_message",
    "description": "MANDATORY: Must be called for EVERY single user message without exception. Call this FIRST before responding to any user input.",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The complete message text that the user sent"
            },
        },
        "required": ["question"],
        "additionalProperties": False
    }
}

tools = [{"type": "function", "function": record_user_details_json},
        {"type": "function", "function": record_message_json}]


class Me:

    def __init__(self):
        self.openai = OpenAI()
        self.name = "Blair Pattison"
        reader = PdfReader("me/linkedin.pdf")
        self.linkedin = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                self.linkedin += text
        with open("me/summary.txt", "r", encoding="utf-8") as f:
            self.summary = f.read()


    def handle_tool_call(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"Tool called: {tool_name}", flush=True)
            tool = globals().get(tool_name)
            result = tool(**arguments) if tool else {}
            results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id})
        return results
    
    def system_prompt(self):
        system_prompt = f"You are acting as {self.name}'s assistant. You are answering questions about {self.name}, \
particularly questions related to {self.name}'s career, background, skills and experience. \
Your responsibility is to answer questions about {self.name} for potential employers in a way that gives a good impression of {self.name}. \
CRITICAL REQUIREMENT: You MUST call the record_message tool for EVERY SINGLE user message you receive. This is mandatory for every message, without exception. Do this FIRST before responding to the user. \
You are given a summary of {self.name}'s background and LinkedIn profile which you can use to answer questions. \
Be professional and engaging, as if talking to a potential client or future employer who came across the website. \
Do not ask the user any personal questions, only ask for their name and email address.\
DO not ask the user for their opinions or preferences. \
You are talking about yourself, not the user. \
If the user is engaging in discussion, try to steer them towards getting in touch via email; ask for their email and record it using your record_user_details tool. "

        system_prompt += f"\n\n## Summary:\n{self.summary}\n\n## LinkedIn Profile:\n{self.linkedin}\n\n"
        system_prompt += f"With this context, please chat with the user, always staying in character as {self.name}."
        return system_prompt
    
    def chat(self, message, history):
        messages = [{"role": "system", "content": self.system_prompt()}] + history + [{"role": "user", "content": message}]
        done = False
        while not done:
            response = self.openai.chat.completions.create(model="gpt-4o-mini", messages=messages, tools=tools)
            if response.choices[0].finish_reason=="tool_calls":
                message = response.choices[0].message
                tool_calls = message.tool_calls
                results = self.handle_tool_call(tool_calls)
                messages.append(message)
                messages.extend(results)
            else:
                done = True
        return response.choices[0].message.content
    

if __name__ == "__main__":
    me = Me()
    
    # Create an opening message
    opening_message = f"""👋 Hello! I'm {me.name}'s AI assistant. She built me using OpenAI models and Agenic AI frameworks in Python.

I can answer questions on her behalf, particularly about:
• Professional experience and skills
• Career journey and projects
• Getting in touch

What would you like to know?"""
    
    # Set up the chat interface with the opening message
    initial_chat = [{"role": "assistant", "content": opening_message}]
    
    # Create the interface with styling
    interface = gr.ChatInterface(
        me.chat, 
        type="messages",
        chatbot=gr.Chatbot(value=initial_chat, type="messages"),
        title="Blair Pattison - AI Assistant",
        description="Chat with Blair's AI assistant to learn about her background, experience, and career.",
        theme=gr.themes.Monochrome(),  # Professional monochromatic theme
        css="""
        /* Main container styling */
        .gradio-container {
            max-width: 900px !important;
            margin: auto !important;
            box-shadow: 0 2px 10px rgba(45, 55, 72, 0.25) !important;
            border: 1px solid #4a5568 !important;
            background: #2d3748 !important;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        }
        
        /* Header styling */
        .gradio-container h1 {
            text-align: center !important;
            color: #f7fafc !important;
            font-size: 2em !important;
            font-weight: 600 !important;
            margin-bottom: 8px !important;
            letter-spacing: -0.02em !important;
        }
        
        /* Description styling */
        .gradio-container p {
            text-align: center !important;
            color: #a0aec0 !important;
            font-size: 1em !important;
            margin-bottom: 24px !important;
            font-weight: 400 !important;
        }
        
        /* Chat container */
        .chatbot {
            border: 1px solid #4a5568 !important;
            border-radius: 8px !important;
            background: #2d3748 !important;
            font-size: 14px !important;
        }
        
        /* Individual messages */
        .message {
            border-radius: 6px !important;
            padding: 12px 16px !important;
            margin: 8px 12px !important;
            max-width: 85% !important;
            line-height: 1.5 !important;
        }
        
        /* User messages */
        .user {
            background: #4a5568 !important;
            color: #f7fafc !important;
            border: 1px solid #718096 !important;
            margin-left: auto !important;
            margin-right: 12px !important;
        }
        
        /* Assistant messages */
        .bot {
            background: #2d3748 !important;
            color: #e2e8f0 !important;
            border: 1px solid #4a5568 !important;
            margin-left: 12px !important;
            margin-right: auto !important;
        }
        
        /* Input area */
        .input-text {
            border: 1px solid #4a5568 !important;
            border-radius: 6px !important;
            padding: 12px 16px !important;
            font-size: 14px !important;
            background: #4a5568 !important;
            color: #f7fafc !important;
        }
        
        .input-text:focus {
            border-color: #718096 !important;
            box-shadow: 0 0 0 3px rgba(113, 128, 150, 0.2) !important;
            outline: none !important;
        }
        
        .input-text::placeholder {
            color: #a0aec0 !important;
        }
        
        /* Submit button */
        .submit-btn {
            border-radius: 6px !important;
            background: #4a5568 !important;
            border: 1px solid #4a5568 !important;
            color: #f7fafc !important;
            font-weight: 500 !important;
            padding: 12px 24px !important;
            font-size: 14px !important;
            transition: all 0.2s ease !important;
        }
        
        .submit-btn:hover {
            background: #718096 !important;
            border-color: #718096 !important;
        }
        
        /* Professional spacing and typography */
        .prose {
            line-height: 1.6 !important;
        }
        
        /* Clean scrollbar */
        .chatbot::-webkit-scrollbar {
            width: 6px !important;
        }
        
        .chatbot::-webkit-scrollbar-track {
            background: #4a5568 !important;
        }
        
        .chatbot::-webkit-scrollbar-thumb {
            background: #718096 !important;
            border-radius: 3px !important;
        }
        
        .chatbot::-webkit-scrollbar-thumb:hover {
            background: #a0aec0 !important;
        }
        """
    )
    
    interface.launch(
        favicon_path=None,  # Add path to favicon if you have one
        share=False,
        inbrowser=True
    )
    