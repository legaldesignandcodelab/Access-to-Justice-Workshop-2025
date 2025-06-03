#!/usr/bin/env python3
"""
Test script to verify the asylum interview system setup
"""

import os
import sys
from dotenv import load_dotenv

def test_environment():
    """Test environment configuration"""
    print("🧪 Testing Environment Setup...")
    
    # Load environment variables
    load_dotenv()
    
    # Check OpenAI API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in .env file")
        return False
    elif api_key == "your_openai_api_key_here":
        print("❌ Please set a real OpenAI API key in .env file")
        return False
    else:
        print("✅ OpenAI API key configured")
    
    # Check other environment variables
    config_vars = [
        'AUDIO_CHUNK', 'AUDIO_CHANNELS', 'AUDIO_RATE', 'RECORD_DURATION',
        'TTS_RATE', 'TTS_VOLUME', 'OUTPUT_DIRECTORY', 'MAX_RETRIES'
    ]
    
    for var in config_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"⚠️ {var}: using default value")
    
    return True

def test_imports():
    """Test required package imports"""
    print("\n🧪 Testing Package Imports...")
    
    try:
        import openai
        print("✅ OpenAI package imported successfully")
    except ImportError as e:
        print(f"❌ OpenAI import failed: {e}")
        return False
    
    try:
        import pyaudio
        print("✅ PyAudio package imported successfully")
    except ImportError as e:
        print(f"❌ PyAudio import failed: {e}")
        print("💡 Try: brew install portaudio (on macOS)")
        return False
    
    try:
        import pyttsx3
        print("✅ pyttsx3 package imported successfully")
    except ImportError as e:
        print(f"❌ pyttsx3 import failed: {e}")
        return False
    
    try:
        from dotenv import load_dotenv
        print("✅ python-dotenv package imported successfully")
    except ImportError as e:
        print(f"❌ python-dotenv import failed: {e}")
        return False
    
    return True

def test_audio_devices():
    """Test audio device availability"""
    print("\n🧪 Testing Audio Devices...")
    
    try:
        import pyaudio
        audio = pyaudio.PyAudio()
        device_count = audio.get_device_count()
        
        if device_count == 0:
            print("❌ No audio devices found")
            return False
        else:
            print(f"✅ Found {device_count} audio devices")
            
            # List input devices
            input_devices = []
            for i in range(device_count):
                device_info = audio.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    input_devices.append(device_info['name'])
            
            if input_devices:
                print(f"✅ Input devices available: {len(input_devices)}")
                for device in input_devices[:3]:  # Show first 3
                    print(f"   - {device}")
            else:
                print("❌ No input devices found")
                return False
        
        audio.terminate()
        return True
        
    except Exception as e:
        print(f"❌ Audio device test failed: {e}")
        return False

def test_tts():
    """Test text-to-speech functionality"""
    print("\n🧪 Testing Text-to-Speech...")
    
    try:
        import pyttsx3
        engine = pyttsx3.init()
        
        voices = engine.getProperty('voices')
        if voices:
            print(f"✅ Found {len(voices)} TTS voices")
            print(f"   Default voice: {voices[0].name}")
        else:
            print("⚠️ No TTS voices found")
        
        # Test speech (comment out if you don't want audio)
        # engine.say("Test message")
        # engine.runAndWait()
        # print("✅ TTS test completed")
        
        return True
        
    except Exception as e:
        print(f"❌ TTS test failed: {e}")
        return False

def test_openai_connection():
    """Test OpenAI API connection"""
    print("\n🧪 Testing OpenAI Connection...")
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Test with a simple completion
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello, this is a test."}],
            max_tokens=10
        )
        
        if response.choices:
            print("✅ OpenAI API connection successful")
            return True
        else:
            print("❌ OpenAI API returned empty response")
            return False
            
    except Exception as e:
        print(f"❌ OpenAI connection failed: {e}")
        print("💡 Check your API key and internet connection")
        return False

def main():
    """Run all tests"""
    print("🚀 Asylum Interview System Setup Test")
    print("=" * 50)
    
    tests = [
        ("Environment Configuration", test_environment),
        ("Package Imports", test_imports),
        ("Audio Devices", test_audio_devices),
        ("Text-to-Speech", test_tts),
        ("OpenAI Connection", test_openai_connection)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! System is ready to use.")
        print("Run: python voice_test.py")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Please fix the issues above.")
        print("Check the README.md for troubleshooting tips.")

if __name__ == "__main__":
    main()
