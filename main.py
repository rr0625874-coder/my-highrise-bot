import warnings
warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources.*")
from asyncio import run as arun
from bot import HighriseBot
from config import get_room_id, get_api_key

if __name__ == "__main__":
    room_id = get_room_id()
    api_key = get_api_key()
    arun(HighriseBot().run_bot(room_id, api_key))