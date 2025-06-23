from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import google.generativeai as genai
from dotenv import load_dotenv
import os
import base64
from langdetect import detect
from models import db, User, Chat, BloodDonor, UserActionLog
from datetime import datetime, timezone, timedelta
import pytz
import PIL.Image
import io
from functools import wraps
from flask_migrate import Migrate
import threading
import time

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///drwise.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
migrate = Migrate(app, db)

# Configure login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Set timezone to IST
ist = pytz.timezone('Asia/Kolkata')

def get_ist_time():
    return datetime.now(ist)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Configure Gemini API
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env file")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest")

# Health assistant system prompt
HEALTH_SYSTEM_PROMPT = """You are Dr.Wise, an AI health assistant designed to provide comprehensive health guidance. Your role is to:
1. Conduct a thorough health assessment
2. Provide potential conditions based on symptoms
3. Suggest appropriate treatments and medications
4. Recommend lifestyle changes and dietary modifications

IMPORTANT: Always respond in the same language that the user uses in their message.

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

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            flash('Admin access required.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('landing'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            # Log login action
            log = UserActionLog(user_id=user.id, action='login', details='User logged in')
            db.session.add(log)
            db.session.commit()
            return redirect(url_for('landing'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('chat_interface'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'error')
            return render_template('register.html')
        
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('chat_interface'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    # Log logout action
    log = UserActionLog(user_id=current_user.id, action='logout', details='User logged out')
    db.session.add(log)
    db.session.commit()
    logout_user()
    return redirect(url_for('landing'))

@app.route('/chat')
@login_required
def chat_interface():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    user_message = request.form.get('message')
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    try:
        # Detect the language of the user's message
        detected_language = detect(user_message)
        
        # Get conversation history from database
        recent_chats = Chat.query.filter_by(user_id=current_user.id).order_by(Chat.timestamp.desc()).limit(5).all()
        conversation_history = []
        for chat in reversed(recent_chats):
            conversation_history.append({'role': 'USER', 'message': chat.message})
            conversation_history.append({'role': 'ASSISTANT', 'message': chat.response})
        
        # Build the full conversation context
        conversation_context = HEALTH_SYSTEM_PROMPT
        for msg in conversation_history:
            conversation_context += f"\n{msg['role']}: {msg['message']}"
        conversation_context += f"\nUSER: {user_message}"

        # Generate response from Gemini
        response = model.generate_content(conversation_context)
        assistant_message = response.text

        # Save chat to database with UTC timezone-aware timestamp
        now_utc = datetime.now(timezone.utc)
        chat = Chat(
            user_id=current_user.id,
            message=user_message,
            response=assistant_message,
            timestamp=now_utc
        )
        db.session.add(chat)
        db.session.commit()

        return jsonify({'message': assistant_message})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat-history')
@login_required
def get_chat_history():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    chats = Chat.query.filter_by(user_id=current_user.id)\
        .order_by(Chat.timestamp.desc())\
        .paginate(page=page, per_page=per_page)

    def to_ist(ts):
        # If timestamp is naive, treat as UTC
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(ist)

    return jsonify({
        'chats': [{
            'id': chat.id,
            'message': chat.message,
            'response': chat.response,
            'timestamp': to_ist(chat.timestamp).strftime('%Y-%m-%d %I:%M:%S %p IST')
        } for chat in chats.items],
        'has_next': chats.has_next,
        'has_prev': chats.has_prev,
        'total_pages': chats.pages,
        'current_page': chats.page
    })

@app.route('/api/new_chat', methods=['POST'])
@login_required
def new_chat():
    return jsonify({'status': 'success'})

@app.route('/blood-bank')
def blood_bank():
    return render_template('blood_bank.html')

@app.route('/bmi-calculator')
def bmi_calculator():
    return render_template('bmi_calculator.html')

@app.route('/medicine-helper')
@login_required
def medicine_helper():
    return render_template('medicine_helper.html')

@app.route('/api/medicine-helper', methods=['POST'])
@login_required
def identify_medicine_and_uses():
    try:
        print("Medicine helper API called")
        medicine_name = None
        
        # Check if image was uploaded
        if 'image' in request.files:
            print("Image file detected")
            image = request.files['image']
            if image.filename == '':
                print("No filename provided")
                return jsonify({'error': 'No image selected'}), 400
            
            print(f"Image filename: {image.filename}")
            
            # Validate file type
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
            if not ('.' in image.filename and 
                   image.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
                print(f"Invalid file type: {image.filename}")
                return jsonify({'error': 'Invalid file type. Please upload PNG, JPG, JPEG, GIF, or BMP'}), 400
            
            try:
                # Read and encode image
                image_bytes = image.read()
                print(f"Image size: {len(image_bytes)} bytes")
                
                # Create image part for Gemini
                image_stream = io.BytesIO(image_bytes)
                pil_image = PIL.Image.open(image_stream)
                print(f"PIL image created: {pil_image.size}")
                
                # First prompt to identify the medicine from image
                identification_prompt = "Identify the medicine in this image (e.g., pill or packaging). Provide only the name of the medicine."
                print("Sending image to Gemini for identification")
                response = model.generate_content([identification_prompt, pil_image])
                medicine_name = response.text.strip()
                print(f"Gemini response: {medicine_name}")
                
                # Clean up the medicine name (remove extra text, punctuation, etc.)
                medicine_name = medicine_name.replace('The medicine in this image is', '').replace('This is', '').strip()
                medicine_name = medicine_name.rstrip('.').strip()
                print(f"Cleaned medicine name: {medicine_name}")
                
            except Exception as img_error:
                print(f"Image processing error: {str(img_error)}")
                return jsonify({'error': f'Error processing image: {str(img_error)}'}), 500
            
        # Check if text input was provided
        elif 'medicine_name' in request.form:
            print("Text input detected")
            medicine_name = request.form['medicine_name'].strip()
            if not medicine_name:
                print("Empty medicine name")
                return jsonify({'error': 'Please enter a medicine name'}), 400
            print(f"Medicine name from text: {medicine_name}")
        
        else:
            print("No image or text input provided")
            return jsonify({'error': 'Please provide either an image or medicine name'}), 400
        
        if not medicine_name:
            print("No medicine name identified")
            return jsonify({'error': 'Could not identify medicine name'}), 400
        
        try:
            # Second prompt to get use cases
            use_cases_prompt = f"Provide a concise explanation of the use cases for the medicine {medicine_name}. Format the response as a bullet-point list starting with 'Use cases for {medicine_name}:'. Focus on common medical indications and avoid dosage or administration details."
            print("Getting use cases from Gemini")
            response = model.generate_content(use_cases_prompt)
            use_cases = response.text.strip()
            print(f"Use cases received: {len(use_cases)} characters")
        except Exception as api_error:
            print(f"API error: {str(api_error)}")
            return jsonify({'error': f'Error getting use cases: {str(api_error)}'}), 500
        
        print("Returning successful response")
        return jsonify({
            'status': 'success',
            'medicine_name': medicine_name,
            'use_cases': use_cases
        })
        
    except Exception as e:
        print(f"General error: {str(e)}")
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/nutrition-info')
@login_required
def nutrition_info():
    return render_template('nutrition_info.html')

@app.route('/api/nutrition-helper', methods=['POST'])
@login_required
def nutrition_helper():
    import PIL.Image
    import io
    try:
        food_name = None
        # Check if image was uploaded
        if 'image' in request.files:
            image = request.files['image']
            if image.filename == '':
                return jsonify({'error': 'No image selected'}), 400
            allowed_extensions = {'png', 'jpg', 'jpeg'}
            if not ('.' in image.filename and image.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
                return jsonify({'error': 'Invalid file type. Please upload PNG, JPG, or JPEG'}), 400
            try:
                image_bytes = image.read()
                image_stream = io.BytesIO(image_bytes)
                pil_image = PIL.Image.open(image_stream)
                identification_prompt = "Identify the food item in this image. Provide only the name of the food item."
                response = model.generate_content([identification_prompt, pil_image])
                food_name = response.text.strip()
                food_name = food_name.replace('The food item in this image is', '').replace('This is', '').strip()
                food_name = food_name.rstrip('.').strip()
            except Exception as img_error:
                return jsonify({'error': f'Error processing image: {str(img_error)}'}), 500
        elif 'food_name' in request.form:
            food_name = request.form['food_name'].strip()
            if not food_name:
                return jsonify({'error': 'Please enter a food name'}), 400
        else:
            return jsonify({'error': 'Please provide either an image or food name'}), 400
        if not food_name:
            return jsonify({'error': 'Could not identify food name'}), 400
        try:
            nutrition_prompt = f"Provide a concise list of the key nutritional contents (e.g., calories, protein, fat, carbohydrates, fiber, vitamins, minerals) for one standard serving of {food_name}. Specify the serving size (e.g., 1 medium apple, 1 large egg, 1 cup of milk). Format each item as: '{food_name} contains [amount] of [nutrient].' Use a bullet-point list. Ensure the amounts are accurate and based on standard nutritional data."
            response = model.generate_content(nutrition_prompt)
            nutrition_info = response.text.strip()
        except Exception as api_error:
            return jsonify({'error': f'Error getting nutrition info: {str(api_error)}'}), 500
        return jsonify({
            'status': 'success',
            'food_name': food_name,
            'nutrition_info': nutrition_info
        })
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/api/blood-donors', methods=['GET', 'POST'])
@login_required
def handle_blood_donors():
    if request.method == 'POST':
        data = request.json
        donor = BloodDonor(
            user_id=current_user.id,
            name=data['name'],
            blood_group=data['blood_group'],
            location=data['location'],
            contact=data['contact']
        )
        db.session.add(donor)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Donor registered'})
    else:
        blood_group = request.args.get('blood_group')
        location = request.args.get('location')
        query = BloodDonor.query
        if blood_group:
            query = query.filter_by(blood_group=blood_group)
        if location:
            query = query.filter(BloodDonor.location.ilike(f'%{location}%'))
        donors = query.order_by(BloodDonor.created_at.desc()).all()
        def to_ist(ts):
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return ts.astimezone(ist)
        return jsonify({'donors': [{
            'id': d.id,
            'name': d.name,
            'blood_group': d.blood_group,
            'location': d.location,
            'contact': d.contact,
            'created_at': to_ist(d.created_at).strftime('%Y-%m-%d %I:%M:%S %p IST')
        } for d in donors]})

@app.route('/api/blood-statistics')
@login_required
def get_blood_statistics():
    from sqlalchemy import func
    
    # Get total count of donors
    total_donors = BloodDonor.query.count()
    
    if total_donors == 0:
        # Return default statistics if no donors
        return jsonify({
            'statistics': {
                'A+': 0, 'A-': 0, 'B+': 0, 'B-': 0,
                'AB+': 0, 'AB-': 0, 'O+': 0, 'O-': 0
            },
            'total_donors': 0
        })
    
    # Get count for each blood type
    blood_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    statistics = {}
    
    for blood_type in blood_types:
        count = BloodDonor.query.filter_by(blood_group=blood_type).count()
        percentage = round((count / total_donors) * 100, 1)
        statistics[blood_type] = percentage
    
    return jsonify({
        'statistics': statistics,
        'total_donors': total_donors
    })

@app.route('/api/identify-medicine', methods=['POST'])
@login_required
def identify_medicine():
    if 'image' in request.files:
        image = request.files['image']
        image_bytes = image.read()
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        prompt = "Identify the medicine in this image and provide detailed information, uses, side effects, and warnings."
        response = model.generate_content([prompt, image_b64])
        return jsonify({'status': 'success', 'medicine': response.text})
    elif 'name' in request.form:
        name = request.form['name']
        prompt = f"Provide detailed information about the medicine '{name}', including uses, side effects, and warnings."
        response = model.generate_content(prompt)
        return jsonify({'status': 'success', 'medicine': response.text})
    return jsonify({'error': 'No image or name provided'}), 400

@app.route('/api/nutrition-info', methods=['POST'])
@login_required
def get_nutrition_info():
    if 'image' in request.files:
        image = request.files['image']
        image_bytes = image.read()
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        prompt = "Identify the food in this image and provide detailed nutritional information (calories, protein, carbs, fat, vitamins, minerals, and health tips)."
        response = model.generate_content([prompt, image_b64])
        return jsonify({'status': 'success', 'nutrition': response.text})
    elif 'name' in request.form:
        name = request.form['name']
        prompt = f"Provide detailed nutritional information about '{name}' (calories, protein, carbs, fat, vitamins, minerals, and health tips)."
        response = model.generate_content(prompt)
        return jsonify({'status': 'success', 'nutrition': response.text})
    return jsonify({'error': 'No image or name provided'}), 400

@app.route('/admin')
@admin_required
def admin_dashboard():
    user_count = User.query.count()
    chat_count = Chat.query.count()
    donor_count = BloodDonor.query.count()
    return render_template('admin/dashboard.html', user_count=user_count, chat_count=chat_count, donor_count=donor_count)

@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Cannot delete admin user.', 'error')
        return redirect(url_for('admin_users'))
    db.session.delete(user)
    db.session.commit()
    # Log action
    log = UserActionLog(user_id=current_user.id, action='delete_user', details=f'Deleted user {user.username}')
    db.session.add(log)
    db.session.commit()
    flash('User deleted.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/create', methods=['POST'])
@admin_required
def admin_create_user():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    is_admin = request.form.get('is_admin') == '1'
    
    # Validation
    if not username or not email or not password:
        flash('All fields are required.', 'error')
        return redirect(url_for('admin_users'))
    
    if password != confirm_password:
        flash('Passwords do not match.', 'error')
        return redirect(url_for('admin_users'))
    
    if len(password) < 6:
        flash('Password must be at least 6 characters long.', 'error')
        return redirect(url_for('admin_users'))
    
    # Check if username or email already exists
    if User.query.filter_by(username=username).first():
        flash('Username already exists.', 'error')
        return redirect(url_for('admin_users'))
    
    if User.query.filter_by(email=email).first():
        flash('Email already exists.', 'error')
        return redirect(url_for('admin_users'))
    
    # Create new user
    password_hash = generate_password_hash(password)
    new_user = User(
        username=username,
        email=email,
        password_hash=password_hash,
        is_admin=is_admin
    )
    
    try:
        db.session.add(new_user)
        db.session.commit()
        
        # Log action
        log = UserActionLog(
            user_id=current_user.id, 
            action='create_user', 
            details=f'Created user {username} (Admin: {is_admin})'
        )
        db.session.add(log)
        db.session.commit()
        
        flash(f'User {username} created successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error creating user. Please try again.', 'error')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/chats')
@admin_required
def admin_chats():
    user_filter = request.args.get('user', '')
    if user_filter:
        chats = Chat.query.join(User).filter(User.username.ilike(f'%{user_filter}%')).order_by(Chat.timestamp.desc()).all()
    else:
        chats = Chat.query.order_by(Chat.timestamp.desc()).all()
    
    # Get all users for the filter dropdown
    users = User.query.order_by(User.username).all()
    return render_template('admin/chats.html', chats=chats, users=users, selected_user=user_filter)

@app.route('/admin/blood-donors')
@admin_required
def admin_blood_donors():
    donors = BloodDonor.query.order_by(BloodDonor.created_at.desc()).all()
    return render_template('admin/blood_donors.html', donors=donors)

@app.route('/admin/logs')
@admin_required
def admin_logs():
    logs = UserActionLog.query.order_by(UserActionLog.timestamp.desc()).all()
    return render_template('admin/logs.html', logs=logs)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
    
    
