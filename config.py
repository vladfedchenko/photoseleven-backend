class BaseConfig(object):
    DEBUG = False
    TESTING = False
    SECRET_KEY = 'this-really-needs-to-be-changed'
    MONGO_USERNAME = 'username'
    MONGO_PASSWORD = 'password'
    MONGO_URI = f'mongodb://{MONGO_USERNAME}:{MONGO_PASSWORD}@localhost:27017/photoseleven'
    TOKEN_EXPIRATION_DAYS = 365
    UPLOADS_DIR = 'change-me!!'
    ALLOWED_MEDIA_EXT = {'jpg': 'image/jpeg', 'mp4': 'video/mp4'}
    ALLOWED_MEDIA_HEADERS = {'image/jpeg', 'video/mp4'}


class ProductionConfig(BaseConfig):
    pass


class DevelopmentConfig(BaseConfig):
    UPLOADS_DIR = 'dev'
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    MONGO_USERNAME = 'test'
    MONGO_PASSWORD = 'test'
    MONGO_URI = f'mongodb://{MONGO_USERNAME}:{MONGO_PASSWORD}@localhost:27017/test_photoseleven'
    SERVER_NAME = 'localhost.localdomain:5000'
    UPLOADS_DIR = '/tmp/photoseleven-test'
