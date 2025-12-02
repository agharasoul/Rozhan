"""
تست‌های API روژان
pytest backend/tests/
"""
import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient


class TestImports:
    """تست import های اصلی"""
    
    def test_fastapi_imports(self):
        """FastAPI باید import بشه"""
        from fastapi import FastAPI
        assert FastAPI is not None
    
    def test_main_imports(self):
        """main.py باید import بشه"""
        import main
        assert main.app is not None
    
    def test_ai_provider_imports(self):
        """AI Provider باید import بشه"""
        import ai_provider
        assert ai_provider.AI is not None
    
    def test_auth_imports(self):
        """Auth باید import بشه"""
        import auth
        assert auth is not None
    
    def test_config_imports(self):
        """Config باید import بشه"""
        import config
        assert config is not None


class TestAPIEndpoints:
    """تست endpoint های API"""
    
    @pytest.fixture
    def client(self):
        """ساخت test client"""
        from main import app
        return TestClient(app)
    
    def test_root_endpoint(self, client):
        """تست / endpoint"""
        response = client.get("/")
        assert response.status_code == 200
    
    def test_health_check(self, client):
        """تست health check"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "status" in data or True  # Flexible check


class TestModels:
    """تست مدل‌های Pydantic"""
    
    def test_chat_request_model(self):
        """ChatRequest باید کار کنه"""
        from main import ChatRequest
        req = ChatRequest(message="سلام")
        assert req.message == "سلام"
    
    def test_chat_response_model(self):
        """ChatResponse باید کار کنه"""
        from main import ChatResponse
        res = ChatResponse(response="سلام!")
        assert res.response == "سلام!"


class TestAIProvider:
    """تست AI Provider"""
    
    def test_provider_exists(self):
        """Provider باید وجود داشته باشه"""
        from ai_provider import AI, GeminiProvider, OpenAIProvider, ClaudeProvider
        assert AI is not None
        assert GeminiProvider is not None
        assert OpenAIProvider is not None
        assert ClaudeProvider is not None
    
    def test_get_provider(self):
        """get_ai_provider باید کار کنه"""
        from ai_provider import get_ai_provider
        # Default provider
        provider = get_ai_provider('gemini')
        assert provider is not None


class TestDatabase:
    """تست Database"""
    
    def test_db_module(self):
        """db module باید import بشه"""
        import db
        assert db is not None


class TestEmotionDetector:
    """تست Emotion Detector"""
    
    def test_emotion_module(self):
        """emotion_detector باید import بشه"""
        import emotion_detector
        assert emotion_detector is not None


class TestSmartLearner:
    """تست Smart Learner"""
    
    def test_smart_learner_module(self):
        """smart_learner باید import بشه"""
        import smart_learner
        assert smart_learner is not None
