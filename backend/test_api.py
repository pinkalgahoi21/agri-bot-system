import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.routes import router


class ProtectedRoutes(unittest.TestCase):
    def test_chat_requires_identity(self):
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            response = client.post('/chat', json={'user_id': 1, 'message': 'Crop advice'})
        self.assertEqual(response.status_code, 401)
