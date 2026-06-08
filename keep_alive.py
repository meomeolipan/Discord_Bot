import os
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "디스코드 봇이 24시간 실행 중입니다!"

def run():
    # 렌더(Render)가 자동으로 할당해 주는 포트 번호를 찾아서 엽니다.
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
