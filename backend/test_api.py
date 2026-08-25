import requests

response = requests.post("http://127.0.0.1:8000/api/chat", json={"user_id": 1, "message": "How can I improve my wheat yield?"})
print(response.status_code)
print(response.json())
