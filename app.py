from flask import Flask, render_template, request, jsonify, session
import google.generativeai as genai
from dotenv import load_dotenv
import os
import base64
from langdetect import detect

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for session management

# Configure Gemini API using environment variable
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env file")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest")

# Health assistant system prompt with language instruction
HEALTH_SYSTEM_PROMPT = """You are Dr.Wise, an AI health assistant designed to provide comprehensive health guidance. Your role is to:
1. Conduct a thorough health assessment
2. Provide potential conditions based on symptoms
3. Suggest appropriate treatments and medications
4. Recommend lifestyle changes and dietary modifications

IMPORTANT: Always respond in the same language that the user uses in their message. If the user writes in Spanish, respond in Spanish. If they write in French, respond in French, and so on.

Follow these guidelines:

1. Initial Assessment:
   - Gather essential health information:
     * Age and gender
     * Symptoms and issues
     * Duration of symptoms/issues
     * Existing medical conditions
     * Current medications
     * Family medical history
     * Lifestyle factors (diet, exercise, sleep)
     * Stress levels and mental health
   - Ask one question at a time
   - Wait for user's response before proceeding

2. Direct Questions Handling:
   - If user asks direct questions about specific conditions or concerns, provide a direct answer while:
     * Acknowledging the specific symptom/concern
     * Explaining the likelihood and risk factors
     * Providing relevant medical information
     * Including appropriate warnings and next steps
   - After answering, continue with the assessment process to gather more context
   - Always maintain a balance between direct answers and comprehensive assessment

3. Analysis and Guidance:
   After gathering information, provide a structured response including:
   a) Potential Conditions:
      - List possible conditions based on symptoms
      - Explain why each condition might be relevant
      - Include risk factors and severity levels
   
   b) Recommended Treatments:
      - Over-the-counter medications (if appropriate)
      - Prescription medications (mention they need doctor's approval)
      - Natural remedies and home treatments
      - Physical therapy or exercises
   
   c) Lifestyle Modifications:
      - Dietary changes and restrictions
      - Exercise recommendations
      - Sleep hygiene tips
      - Stress management techniques
   
   d) Prevention and Monitoring:
      - Warning signs to watch for
      - When to seek emergency care
      - Follow-up recommendations
      - Preventive measures

4. Communication Guidelines:
   - Use a professional but friendly tone
   - Be empathetic and understanding
   - Explain medical terms in simple language
   - Format responses with clear sections
   - Use **bold** for important points
   - Include relevant warnings in warning-message format
   - Format emergency situations with emergency-message styling

5. Important Rules:
   - Never make definitive diagnoses
   - Always encourage consulting healthcare professionals
   - Include emergency warnings when appropriate
   - Maintain conversation context throughout the session
   - Ask follow-up questions when needed
   - Provide specific, actionable recommendations
   - Include both conventional and alternative treatment options
   - Consider the user's lifestyle and preferences
   - Always respond in the same language as the user's message

6. Response Format:
   For direct questions:
   - Provide a clear, direct answer
   - Include relevant medical information
   - Add appropriate warnings
   - Suggest next steps
   - Continue with assessment


   For general assessment:
   - Brief acknowledgment of the user's concern
   - Summary of gathered information
   - Potential conditions section
   - Treatment recommendations
   - Lifestyle modifications
   - Prevention and monitoring tips
   - Clear next steps
   - When to seek professional help
   - Follow-up recommendations

Remember to:
- Ask relevant questions one at a time
- Provide clear, structured information
- Include specific recommendations
- End with appropriate next steps
- Use formatting for better readability:
  * **bold** for important points
  * warning-message for warnings
  * emergency-message for emergencies
  * health-tip for lifestyle recommendations
- Always respond in the same language as the user's message

Current conversation context:
"""

@app.route('/')
def index():
    # Initialize session for new users
    if 'conversation_history' not in session:
        session['conversation_history'] = []
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.form.get('message')
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    try:
        # Detect the language of the user's message
        detected_language = detect(user_message)
        
        # Get conversation history from session
        conversation_history = session.get('conversation_history', [])
        
        # Build the full conversation context
        conversation_context = HEALTH_SYSTEM_PROMPT
        for msg in conversation_history:
            conversation_context += f"\n{msg['role']}: {msg['message']}"
        conversation_context += f"\nUSER: {user_message}"

        # Generate response from Gemini
        response = model.generate_content(conversation_context)
        assistant_message = response.text

        # Update conversation history
        conversation_history.append({'role': 'USER', 'message': user_message})
        conversation_history.append({'role': 'ASSISTANT', 'message': assistant_message})
        session['conversation_history'] = conversation_history

        return jsonify({'message': assistant_message})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    try:
        # Get the audio data from the request
        audio_data = request.json.get('audio')
        if not audio_data:
            return jsonify({'error': 'No audio data provided'}), 400

        # Decode the base64 audio data
        audio_bytes = base64.b64decode(audio_data.split(',')[1])

        # Use Gemini for transcription
        response = model.generate_content([
            "Transcribe this audio accurately, maintaining proper punctuation and formatting:",
            {"mime_type": "audio/webm", "data": audio_bytes}
        ])
        
        transcription = response.text
        return jsonify({'transcription': transcription})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/new_chat', methods=['POST'])
def new_chat():
    # Clear conversation history
    session['conversation_history'] = []
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True)
    
    
