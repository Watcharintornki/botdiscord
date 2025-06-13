from flask import Flask
import os
import main  # 👈 import เพื่อให้บอททำงาน

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Server is running and bot is alive!"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
