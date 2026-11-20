PASSWORD="Testing-Strong-Password42!"
ORIGIN="http://127.0.0.1:5173"

def sign_in(client,email="baseline@example.com",password=PASSWORD,register=True):
    client.headers["Origin"]=ORIGIN
    bootstrap=client.get("/api/auth/session")
    assert bootstrap.status_code == 200
    client.headers["X-CSRF-Token"]=bootstrap.json()["csrf_token"]
    response=client.post("/api/auth/register" if register else "/api/auth/login",json={"email":email,"password":password})
    if register and response.status_code == 409:
        response=client.post("/api/auth/login",json={"email":email,"password":password})
    assert response.status_code in {200,201}, response.json()
    client.headers["X-CSRF-Token"]=response.json()["csrf_token"]
    return response.json()["user"]["id"]
