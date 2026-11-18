import re
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.auth import router
from database.database import Base, get_db


class AccountFlow(unittest.TestCase):
    def test_verified_password_login_and_revocation(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        sessions = sessionmaker(bind=engine)

        def database():
            with sessions() as db:
                yield db

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = database
        credentials = {"email": "farmer@example.org", "password": "sample-password"}
        with TestClient(app) as client, patch.dict("os.environ", RESEND_API_KEY="test", AUTH_EMAIL_FROM="test@example.org"), patch("api.local_login.requests.post") as delivery:
            signup = client.post("/auth/signup", json=credentials)
            self.assertEqual(signup.status_code, 200)
            code = re.search(r"\b\d{6}\b", delivery.call_args.kwargs["json"]["text"])[0]
            verify = {"email": credentials["email"], "ticket": signup.json()["ticket"], "token": code}
            self.assertEqual(client.post("/auth/login", json=credentials).status_code, 401)
            self.assertEqual(client.post("/auth/verify", json=verify).status_code, 200)
            self.assertEqual(client.post("/auth/verify", json=verify).status_code, 400)
            self.assertEqual(client.post("/auth/login", json={**credentials, "password": "not-correct"}).status_code, 401)
            login = client.post("/auth/login", json=credentials)
            headers = {"Authorization": "Bearer " + login.json()["access_token"]}
            self.assertEqual(client.get("/profile", headers=headers).status_code, 200)
            self.assertEqual(client.post("/auth/logout", headers=headers).status_code, 204)
            self.assertEqual(client.get("/profile", headers=headers).status_code, 401)
            delivery.assert_called_once()
        engine.dispose()
