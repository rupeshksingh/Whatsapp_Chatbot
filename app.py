from flask import Flask, request, session
from twilio.twiml.messaging_response import MessagingResponse
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from transformers import AutoModelForCausalLM, AutoTokenizer

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'

Base = declarative_base()

# Database setup
DATABASE_URI = 'sqlite:///users.db'
engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)
db_session = Session()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    password = Column(String)

Base.metadata.create_all(engine)

class CustomChatModel:
    def __init__(self):
        self.model_name = 'microsoft/DialoGPT-medium'
        self.model = AutoModelForCausalLM.from_pretrained(self.model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

    def generate_response(self, input_text):
        inputs = self.tokenizer.encode(input_text + self.tokenizer.eos_token, return_tensors='pt')
        outputs = self.model.generate(inputs, max_length=100, pad_token_id=self.tokenizer.eos_token_id)
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return response

chat_model = CustomChatModel()

@app.route('/whatsapp', methods=['POST'])
def whatsapp():
    incoming_msg = request.values.get('Body', '').lower()
    response = MessagingResponse()
    msg = response.message()
    
    user_state = session.get('state', None)

    if 'i want to log in' in incoming_msg:
        msg.body('Sure, please enter your email:')
        session['state'] = 'awaiting_email'
    elif user_state == 'awaiting_email':
        session['email'] = incoming_msg
        msg.body('Please enter your password:')
        session['state'] = 'awaiting_password'
    elif user_state == 'awaiting_password':
        email = session.get('email')
        password = incoming_msg
        new_user = User(email=email, password=password)
        db_session.add(new_user)
        db_session.commit()
        msg.body('Your account has been registered')
        session['state'] = None
    else:
        response_text = chat_model.generate_response(incoming_msg)
        msg.body(response_text)
    
    return str(response)

if __name__ == '__main__':
    app.run(debug=True)