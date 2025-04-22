from flask import Flask, jsonify

app = Flask(__name__)

@app.after_request
def add_security_headers(response):
    headers = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'Content-Security-Policy': "default-src 'self'",
        'Referrer-Policy': 'strict-origin-when-cross-origin'
    }
    response.headers.update(headers)
    return response