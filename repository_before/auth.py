from flask import request
from werkzeug.security import check_password_hash

def check_auth(request):
    auth = request.authorization
    if not auth or not check_password_hash('hashedpass', auth.password):  # Hardcoded, duplicated logic
        return False
    return True