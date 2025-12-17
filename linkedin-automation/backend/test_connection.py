#!/usr/bin/env python3
"""
Quick test script to verify backend services are configured correctly
"""

import sys

def test_imports():
    """Test that all modules can be imported"""
    try:
        from services.agiopen_client import AGIOpenClient
        from services.openai_client import OpenAIClient
        from services.image_generator import ImageGenerator
        from database import Session, PostHistory
        import config
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_config():
    """Test that config is loaded"""
    try:
        import config
        if config.AGIOPEN_API_KEY and config.OPENAI_API_KEY and config.OPENAIIMAGE_API_KEY:
            print("✅ All API keys loaded")
            return True
        else:
            print("❌ Some API keys are missing")
            return False
    except Exception as e:
        print(f"❌ Config error: {e}")
        return False

def test_database():
    """Test database connection"""
    try:
        from database import Session, PostHistory
        session = Session()
        count = session.query(PostHistory).count()
        session.close()
        print(f"✅ Database connection successful (found {count} posts)")
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

if __name__ == "__main__":
    print("Testing backend configuration...\n")
    
    all_passed = True
    all_passed &= test_imports()
    all_passed &= test_config()
    all_passed &= test_database()
    
    print("\n" + "="*50)
    if all_passed:
        print("✅ All tests passed! Backend is ready to run.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please check the errors above.")
        sys.exit(1)

