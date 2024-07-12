import os

redis_host = os.environ.get('REDIS_HOST', 'localhost')
db_dir = os.path.join(os.getcwd(), 'src/datastore/reviews.db')


class BaseConfig:
    """Base configuration"""
    BASE_DIR = os.getcwd()

    TESTING = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI', f'sqlite:///{db_dir}')

    REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT = os.environ.get("REDIS_PORT", 6379)

    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.googlemail.com")
    MAIL_PORT = os.environ.get("MAIL_PORT", 587)
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", True)
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", False)
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", '')
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", '')
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "your_email@example.com")


class DevelopmentConfig(BaseConfig):
    """Development configuration"""
    # DEBUG = True


class ProductionConfig(BaseConfig):
    """Production configuration"""
    DEBUG = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
