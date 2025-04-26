# config.py
import os


class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'db', 'genebase.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "sdfklas0lk42j"
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024


def init_app(app):
    app.config.from_object(Config)