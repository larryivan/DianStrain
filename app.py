# app.py
from routes import app
from models import db
import os

# 确保数据库文件夹存在
db_path = os.path.join(os.path.dirname(__file__), 'instance', 'db')
if not os.path.exists(db_path):
    os.makedirs(db_path)

# 创建数据库文件
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True, threaded=True)
