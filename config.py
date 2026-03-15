import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'farmacia-secret-key-2024'
    basedir = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'farmacia.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
