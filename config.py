import os
import logging
from dotenv import load_dotenv

load_dotenv()

# app
APP_NAME = "Qiscus Multichannel CSAT"
DEBUG = True
SECRET_KEY = os.environ.get("SECRET_KEY")

# logging
logging.getLogger("werkzeug").disabled = True
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s %(levelname)s : %(message)s"
)

# database
SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
SQLALCHEMY_TRACK_MODIFICATIONS = False

SUPER_ADMIN_TOKEN = os.environ.get("SUPER_ADMIN_TOKEN")
