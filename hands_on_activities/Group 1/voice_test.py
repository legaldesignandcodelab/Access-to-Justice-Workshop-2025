import os
import json
import wave
import tempfile
import threading
import signal
import requests
import base64
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pyaudio
import pyttsx3
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AsylumInterviewAgent:
    """
    Intelligent agent for conducting asylum interviews with voice interaction,
    automatic transcription, and structured data extraction.
    """
    
    def __init__(self):
        """Initialize the asylum interview agent with environment configuration"""
        # Load configuration from environment
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Audio settings
        self.audio_chunk = int(os.getenv('AUDIO_CHUNK', 1024))
        self.audio_channels = int(os.getenv('AUDIO_CHANNELS', 1))
        self.audio_rate = int(os.getenv('AUDIO_RATE', 44100))
        self.record_duration = int(os.getenv('RECORD_DURATION', 15))
        
        # TTS settings
        self.tts_engine = pyttsx3.init()
        
        self.setup_tts()
        
        # Output settings
        self.output_dir = os.getenv('OUTPUT_DIRECTORY', './interviews')
        self.file_prefix = os.getenv('FILE_PREFIX', 'asylum_interview_')
        
        # Interview settings
        self.max_retries = int(os.getenv('MAX_RETRIES', 3))
        self.question_timeout = int(os.getenv('QUESTION_TIMEOUT', 30))
        self.default_language = os.getenv('DEFAULT_LANGUAGE', 'auto')
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Interview state
        self.interview_data = {}
        self.current_question_index = 0
        self.detected_languages = set()
        
        # Define interview questions with categories
        self.questions = self._load_interview_questions()
        
        print("🤖 Asylum Interview Agent initialized successfully")
    
    def setup_tts(self):
        """Configure text-to-speech engine to use Emma voice"""
        try:
            voices = self.tts_engine.getProperty('voices')
            if voices:
                # Look for Emma voice first, then other high-quality female voices
                preferred_voices = [
                    'Emma',      # Preferred Emma voice
                    'Samantha',  # High-quality female voice
                    'Karen',     # Australian female voice
                    'Moira',     # Irish female voice
                    'Alice',     # Italian female voice
                ]
                
                selected_voice = None
                
                # First try to find exact name matches
                for preferred_name in preferred_voices:
                    for voice in voices:
                        if voice.name.lower() == preferred_name.lower():
                            selected_voice = voice.id
                            print(f"🎤 Found preferred voice: {voice.name}")
                            break
                    if selected_voice:
                        break
                
                # If no exact match, look for voices containing the preferred names
                if not selected_voice:
                    for preferred_name in preferred_voices:
                        for voice in voices:
                            if preferred_name.lower() in voice.name.lower():
                                selected_voice = voice.id
                                print(f"🎤 Found similar voice: {voice.name}")
                                break
                        if selected_voice:
                            break
                
                # Final fallback - use system default
                if not selected_voice:
                    selected_voice = voices[0].id
                    print(f"🎤 Using default voice: {voices[0].name}")
                
                self.tts_engine.setProperty('voice', selected_voice)
                print("🎤 Voice selected successfully")
            
            # Optimize speech parameters
            rate = int(os.getenv('TTS_RATE', 175))
            volume = float(os.getenv('TTS_VOLUME', 0.9))
            
            self.tts_engine.setProperty('rate', rate)
            self.tts_engine.setProperty('volume', volume)
            
            print(f"🎤 TTS configured - Rate: {rate} WPM, Volume: {volume}")
            
        except Exception as e:
            print(f"⚠️ TTS setup warning: {e}")
            print("📢 Using default TTS settings")
    
    def _load_interview_questions(self) -> List[Dict]:
        """Load structured interview questions"""
        return [
            {
                "id": "personal_info_1",
                "category": "personal_information",
                "question": "Please state your full name as it appears on your documents.",
                "required": True,
                "follow_up": "Could you spell your last name for me?"
            },
            {
                "id": "origin_1",
                "category": "origin",
                "question": "What is your country of origin?",
                "required": True,
                "follow_up": "Which specific city or region are you from?"
            },
            {
                "id": "language_1",
                "category": "language",
                "question": "What is your native language? Do you speak any other languages?",
                "required": True,
                "follow_up": None
            },
            {
                "id": "persecution_1",
                "category": "persecution",
                "question": "Can you describe the main reason you are seeking asylum? What happened that made you leave your country?",
                "required": True,
                "follow_up": "Can you provide more specific details about what happened?"
            },
            {
                "id": "timeline_1",
                "category": "timeline",
                "question": "When did you leave your home country? What was your journey like?",
                "required": True,
                "follow_up": "Did you travel directly to Switzerland?"
            },
            {
                "id": "family_1",
                "category": "family",
                "question": "Do you have any family members with you or still in your home country?",
                "required": False,
                "follow_up": "Are any family members in danger?"
            },
            {
                "id": "previous_applications",
                "category": "legal_history",
                "question": "Have you applied for asylum in any other country before coming to Switzerland?",
                "required": True,
                "follow_up": "What was the outcome of that application?"
            },
            {
                "id": "documentation",
                "category": "evidence",
                "question": "Do you have any documents to support your application, such as identity documents, medical records, or evidence of persecution?",
                "required": False,
                "follow_up": "If you don't have documents, can you explain why?"
            }
        ]
    
    def speak(self, text: str, priority: str = "normal"):
        """Convert text to speech with priority handling"""
        print(f"🗣️ Agent: {text}")
        
        # Add pauses for better comprehension
        if priority == "important":
            text = f"Please listen carefully. {text}"
        
        try:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception as e:
            print(f"❌ TTS Error: {e}")
    
    def record_audio(self, duration: Optional[int] = None) -> Optional[str]:
        """Record audio from microphone with error handling"""
        if duration is None:
            duration = self.record_duration
        
        print(f"🎤 Recording for up to {duration} seconds... Speak now.")
        
        try:
            audio = pyaudio.PyAudio()
            
            # Check if microphone is available
            device_count = audio.get_device_count()
            if device_count == 0:
                print("❌ No audio devices found")
                return None
            
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=self.audio_channels,
                rate=self.audio_rate,
                input=True,
                frames_per_buffer=self.audio_chunk
            )
            
            frames = []
            
            for _ in range(0, int(self.audio_rate / self.audio_chunk * duration)):
                try:
                    data = stream.read(self.audio_chunk, exception_on_overflow=False)
                    frames.append(data)
                except Exception as e:
                    print(f"⚠️ Audio read warning: {e}")
                    break
            
            stream.stop_stream()
            stream.close()
            audio.terminate()
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            
            with wave.open(temp_file.name, 'wb') as wf:
                wf.setnchannels(self.audio_channels)
                wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
                wf.setframerate(self.audio_rate)
                wf.writeframes(b''.join(frames))
            
            print("✅ Audio recorded successfully")
            return temp_file.name
            
        except Exception as e:
            print(f"❌ Recording error: {e}")
            return None
    
    def transcribe_audio(self, audio_file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """Transcribe audio using OpenAI Whisper"""
        try:
            with open(audio_file_path, 'rb') as audio_file:
                transcript = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    language=self.default_language if self.default_language != 'auto' else None
                )
            
            # Extract language information from verbose response
            detected_language = getattr(transcript, 'language', 'unknown')
            if detected_language and detected_language != 'unknown':
                self.detected_languages.add(detected_language)
            
            return transcript.text, detected_language
            
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            return None, None
        finally:
            # Clean up temporary file
            if os.path.exists(audio_file_path):
                os.unlink(audio_file_path)
    
    def process_response(self, transcribed_text: str, question_data: Dict) -> Dict:
        """Process response using AI to extract structured information"""
        prompt = f"""
        You are an AI assistant helping to process asylum interview responses. 
        
        Question Category: {question_data['category']}
        Question Asked: "{question_data['question']}"
        User Response: "{transcribed_text}"
        
        Please analyze this response and provide:
        1. Key information extracted
        2. Whether the response adequately answers the question
        3. Any red flags or concerns
        4. Suggested follow-up questions if needed
        5. Confidence level (1-10) in the response quality
        
        Format your response as JSON with the following structure:
        {{
            "extracted_info": "main information from the response",
            "adequately_answered": true/false,
            "concerns": ["list of any concerns"],
            "follow_up_needed": true/false,
            "suggested_follow_up": "specific follow-up question if needed",
            "confidence_level": 1-10,
            "summary": "brief summary for case file"
        }}
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert legal assistant specializing in asylum cases. Analyze responses carefully for completeness and credibility."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            print(f"❌ Response processing error: {e}")
            return {
                "extracted_info": transcribed_text,
                "adequately_answered": False,
                "concerns": [f"Processing error: {str(e)}"],
                "follow_up_needed": True,
                "confidence_level": 1,
                "summary": f"Raw response: {transcribed_text}"
            }
    
    def conduct_interview(self) -> Dict:
        """Main interview flow with intelligent question management"""
        print("\n🏛️ Asylum Interview Agent Starting...")
        print("=" * 60)
        
        # Welcome and explanation
        welcome_msg = """Welcome to the asylum interview system. I am an AI assistant that will help collect your information for your asylum application. 
        
        I will ask you several questions about your background and reasons for seeking asylum. Please speak clearly after each question. 
        
        You can ask me to repeat a question at any time. Let's begin."""
        
        self.speak(welcome_msg, priority="important")
        
        for i, question_data in enumerate(self.questions):
            print(f"\n📋 Question {i+1}/{len(self.questions)} - Category: {question_data['category']}")
            
            # Ask the main question
            success = self._ask_question_with_retry(question_data, i)
            
            if not success and question_data['required']:
                self.speak("This is a required question. Let me try a different approach.")
                # Could implement alternative questioning strategies here
        
        # Interview completion
        completion_msg = """Thank you for completing the interview. Your responses have been recorded and will be processed for your asylum application. 
        
        The information will be reviewed and may be used to prepare for your official interview with the authorities."""
        
        self.speak(completion_msg, priority="important")
        
        return self.interview_data
    
    def _ask_question_with_retry(self, question_data: Dict, question_index: int) -> bool:
        """Ask a question with retry logic and intelligent follow-up"""
        question_id = question_data['id']
        
        for attempt in range(self.max_retries):
            print(f"\n🔄 Attempt {attempt + 1}/{self.max_retries}")
            
            # Ask the question
            self.speak(question_data['question'])
            
            # Record response
            audio_file = self.record_audio()
            if not audio_file:
                self.speak("I couldn't record your response. Let me try again.")
                continue
            
            # Transcribe
            print("🔄 Processing your response...")
            transcribed_text, detected_language = self.transcribe_audio(audio_file)
            
            if not transcribed_text:
                self.speak("I couldn't understand your response. Please try again.")
                continue
            
            print(f"📝 Transcribed: {transcribed_text}")
            if detected_language:
                print(f"🌍 Language detected: {detected_language}")
            
            # Process the response
            processed_info = self.process_response(transcribed_text, question_data)
            
            # Store the information
            self.interview_data[question_id] = {
                "question": question_data['question'],
                "category": question_data['category'],
                "raw_response": transcribed_text,
                "processed_info": processed_info,
                "language": detected_language,
                "timestamp": datetime.now().isoformat(),
                "attempt": attempt + 1
            }
            
            # Check if response is adequate
            if processed_info.get('adequately_answered', False):
                print("✅ Response recorded successfully")
                
                # Ask follow-up if needed
                if processed_info.get('follow_up_needed') and question_data.get('follow_up'):
                    self._ask_followup(question_data['follow_up'], question_id)
                
                return True
            else:
                # Provide feedback and ask for clarification
                if attempt < self.max_retries - 1:
                    clarification = processed_info.get('suggested_follow_up', 
                                                     "Could you provide more details or rephrase your answer?")
                    self.speak(f"I need a bit more information. {clarification}")
        
        print("⚠️ Maximum retries reached for this question")
        return False
    
    def _ask_followup(self, follow_up_question: str, parent_question_id: str):
        """Ask a follow-up question"""
        print(f"\n🔍 Follow-up question:")
        self.speak(follow_up_question)
        
        audio_file = self.record_audio(duration=10)  # Shorter duration for follow-ups
        if audio_file:
            transcribed_text, detected_language = self.transcribe_audio(audio_file)
            if transcribed_text:
                # Store follow-up response
                if parent_question_id in self.interview_data:
                    self.interview_data[parent_question_id]['follow_up'] = {
                        "question": follow_up_question,
                        "response": transcribed_text,
                        "language": detected_language,
                        "timestamp": datetime.now().isoformat()
                    }
                print(f"📝 Follow-up recorded: {transcribed_text}")
    
    def save_interview_data(self, filename: Optional[str] = None) -> str:
        """Save comprehensive interview data"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.file_prefix}{timestamp}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # Add metadata
        complete_data = {
            "interview_metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_questions": len(self.questions),
                "answered_questions": len(self.interview_data),
                "detected_languages": list(self.detected_languages),
                "agent_version": "1.0",
                "configuration": {
                    "max_retries": self.max_retries,
                    "record_duration": self.record_duration,
                    "default_language": self.default_language
                }
            },
            "interview_data": self.interview_data
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(complete_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Complete interview data saved to: {filepath}")
        return filepath
    
    def generate_summary_report(self) -> str:
        """Generate a human-readable summary report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"{self.file_prefix}summary_{timestamp}.txt"
        report_filepath = os.path.join(self.output_dir, report_filename)
        
        with open(report_filepath, 'w', encoding='utf-8') as f:
            f.write("ASYLUM INTERVIEW SUMMARY REPORT\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Interview Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Questions: {len(self.questions)}\n")
            f.write(f"Questions Answered: {len(self.interview_data)}\n")
            f.write(f"Languages Detected: {', '.join(self.detected_languages) if self.detected_languages else 'None detected'}\n\n")
            
            for question_id, data in self.interview_data.items():
                f.write(f"QUESTION: {data['question']}\n")
                f.write(f"CATEGORY: {data['category']}\n")
                f.write(f"RESPONSE: {data['raw_response']}\n")
                
                if 'processed_info' in data and 'summary' in data['processed_info']:
                    f.write(f"SUMMARY: {data['processed_info']['summary']}\n")
                
                if 'follow_up' in data:
                    f.write(f"FOLLOW-UP: {data['follow_up']['response']}\n")
                
                f.write("-" * 30 + "\n\n")
        
        print(f"📄 Summary report saved to: {report_filepath}")
        return report_filepath

def main():
    """Main function to run the asylum interview agent"""
    
    # Load environment variables first
    load_dotenv()
    
    # Check if OpenAI API key is configured
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OpenAI API key not found!")
        print("Please set your OPENAI_API_KEY in the .env file")
        print("Copy .env.sample to .env and add your API key")
        return
    
    try:
        # Initialize the agent
        agent = AsylumInterviewAgent()
        
        # Conduct the interview
        print("\n🚀 Starting asylum interview process...")
        interview_results = agent.conduct_interview()
        
        # Save results
        saved_file = agent.save_interview_data()
        summary_file = agent.generate_summary_report()
        
        # Display final summary
        print("\n" + "=" * 60)
        print("📊 INTERVIEW COMPLETED")
        print("=" * 60)
        print(f"✅ Questions answered: {len(interview_results)}/{len(agent.questions)}")
        print(f"🌍 Languages detected: {', '.join(agent.detected_languages) if agent.detected_languages else 'None'}")
        print(f"💾 Data saved to: {saved_file}")
        print(f"📄 Summary saved to: {summary_file}")
        print("\n🎯 Next steps:")
        print("1. Review the generated summary report")
        print("2. Prepare additional documentation if needed")
        print("3. Schedule official interview with authorities")
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Interview interrupted by user")
    except Exception as e:
        print(f"\n❌ System error: {e}")
        print("Please check your configuration and try again")

if __name__ == "__main__":
    main()