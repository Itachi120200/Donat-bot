import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [7698694481]
CARD_NUMBER = os.getenv("CARD_NUMBER", "4067 0700 0274 1192")
CARD_HOLDER = os.getenv("CARD_HOLDER", "ADMIN")
DEFAULT_MARKUP = float(os.getenv("DEFAULT_MARKUP_PERCENT", 10))
