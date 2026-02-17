from json import load, dump
import os
import time
from highrise import Position

DEFAULT_DATA = '{"users": {}, "bot_position": {"x": 0, "y": 0, "z": 0, "facing": "FrontRight"}, "mutes": {}, "bans": {}, "developers": [], "moderators": [], "owners": [], "filter": {"enabled": false, "words": []}, "warns": {}, "vips": [], "vip_expiry": {}, "viploc": {"x": 9.0, "y": 0.35, "z": 10.0, "facing": "FrontRight"}, "locations": {}, "subs": [], "greet_whisper": true, "greet_text_en": "", "freeze_pos": {}, "frozen": {}}'

class Storage:
    def __init__(self, file_path: str = "./data.json"):
        self.file_path = file_path
        self._data = None
        self._dirty = False
        self._ensure_file()
        self._load()

    @property
    def data(self):
        return self._data

    @property
    def dirty(self):
        return self._dirty

    def _ensure_file(self):
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w") as f:
                f.write(DEFAULT_DATA)

    def _load(self):
        with open(self.file_path, "r") as f:
            self._data = load(f)
        self._data.setdefault("users", {})
        self._data.setdefault("bot_position", {"x": 0, "y": 0, "z": 0, "facing": "FrontRight"})
        self._data.setdefault("mutes", {})
        self._data.setdefault("bans", {})
        self._data.setdefault("developers", [])
        self._data.setdefault("moderators", [])
        self._data.setdefault("owners", [])
        self._data.setdefault("rules_text", "")
        self._data.setdefault("greet_text_en", "")
        self._data.setdefault("filter", {"enabled": False, "words": []})
        self._data.setdefault("warns", {})
        self._data.setdefault("vips", [])
        self._data.setdefault("vip_expiry", {})
        self._data.setdefault("viploc", {"x": 9.0, "y": 0.35, "z": 10.0, "facing": "FrontRight"})
        self._data.setdefault("locations", {})
        self._data.setdefault("subs", [])
        self._data.setdefault("greet_whisper", True)
        self._data.setdefault("freeze_pos", {})
        self._data.setdefault("frozen", {})
        self._data.setdefault("dm_users", [])
        users = self._data.setdefault("users", {})
        for uid, u in list(users.items()):
            u.setdefault("time_spent", 0)
            u.setdefault("chat_count", 0)
            users[uid] = u
        self._data["users"] = users

    def add_dm_user(self, user_id: str):
        if user_id not in self._data["dm_users"]:
            self._data["dm_users"].append(user_id)
            self._dirty = True

    def has_dmed(self, user_id: str):
        return user_id in self._data["dm_users"]

    def get_balance(self, user_id: str):
        users = self._data.get("users", {})
        return users.get(user_id, {}).get("balance", 0)

    def set_balance(self, user_id: str, amount: int):
        users = self._data.get("users", {})
        if user_id not in users:
            users[user_id] = {"username": "Unknown", "total_tips": 0, "balance": 0}
        users[user_id]["balance"] = amount
        self._data["users"] = users
        self._dirty = True

    def transfer_balance(self, sender_id: str, receiver_id: str, amount: int):
        if amount <= 0:
            return False
        sender_bal = self.get_balance(sender_id)
        if sender_bal < amount:
            return False
        self.set_balance(sender_id, sender_bal - amount)
        receiver_bal = self.get_balance(receiver_id)
        self.set_balance(receiver_id, receiver_bal + amount)
        return True


    def flush(self):
        if not self._dirty:
            return
        with open(self.file_path, "w") as f:
            dump(self._data, f)
        self._dirty = False

    def _now(self):
        return int(time.time())

    def add_tip(self, user_id: str, username: str, amount: int):
        users = self._data.get("users", {})
        user = users.get(user_id, {"total_tips": 0, "username": username, "balance": 0})
        user["total_tips"] = int(user.get("total_tips", 0)) + int(amount or 0)
        user["balance"] = int(user.get("balance", 0)) + int(amount or 0)
        user["username"] = username
        users[user_id] = user
        self._data["users"] = users
        self._dirty = True
    def get_user_tip_amount_by_id(self, user_id: str) -> int:
        users = self._data.get("users", {})
        return int(users.get(user_id, {}).get("total_tips", 0))
    def add_time_spent(self, user_id: str, username: str, seconds: float):
        users = self._data.get("users", {})
        user = users.get(user_id, {"total_tips": 0, "username": username, "balance": 0, "time_spent": 0})
        user["time_spent"] = float(user.get("time_spent", 0)) + max(0.0, float(seconds or 0))
        user["username"] = username
        users[user_id] = user
        self._data["users"] = users
        self._dirty = True
    def add_chat_message(self, user_id: str, username: str):
        users = self._data.get("users", {})
        user = users.get(user_id, {"total_tips": 0, "username": username, "balance": 0, "time_spent": 0, "chat_count": 0})
        user["chat_count"] = int(user.get("chat_count", 0)) + 1
        user["username"] = username
        users[user_id] = user
        self._data["users"] = users
        self._dirty = True
    def get_top_chatters(self, n: int = 10):
        users = self._data.get("users", {})
        arr = []
        for uid, u in users.items():
            arr.append((uid, u.get("username", "Unknown"), int(u.get("chat_count", 0))))
        arr.sort(key=lambda x: x[2], reverse=True)
        return arr[:n]
    def get_top_time_spent(self, n: int = 10):
        users = self._data.get("users", {})
        arr = []
        for uid, u in users.items():
            arr.append((uid, u.get("username", "Unknown"), float(u.get("time_spent", 0))))
        arr.sort(key=lambda x: x[2], reverse=True)
        return arr[:n]

    def get_top_tippers(self, n: int = 10):
        users = self._data.get("users", {})
        sorted_tippers = sorted(users.items(), key=lambda x: x[1]["total_tips"], reverse=True)
        return sorted_tippers[:n]

    def get_user_tip_amount_by_username(self, username: str):
        users = self._data.get("users", {})
        for _, user_data in users.items():
            if user_data["username"].lower() == username.lower():
                return user_data["total_tips"]
        return None

    def save_bot_position(self, position: Position):
        self._data["bot_position"] = {
            "x": position.x,
            "y": position.y,
            "z": position.z,
            "facing": position.facing,
        }
        self._dirty = True

    def load_bot_position(self) -> Position:
        pos = self._data.get("bot_position", {"x": 0, "y": 0, "z": 0, "facing": "FrontRight"})
        return Position(pos["x"], pos["y"], pos["z"], pos["facing"])


    def mute_user(self, user_id: str, seconds: int):
        until = self._now() + max(0, int(seconds))
        self._data["mutes"][user_id] = until
        self._dirty = True

    def unmute_user(self, user_id: str):
        self._data["mutes"].pop(user_id, None)
        self._dirty = True

    def is_muted(self, user_id: str) -> bool:
        until = self._data.get("mutes", {}).get(user_id)
        if not until:
            return False
        if self._now() > until:
            self.unmute_user(user_id)
            return False
        return True

    def ban_user(self, user_id: str, seconds: int):
        until = self._now() + max(0, int(seconds))
        self._data["bans"][user_id] = until
        self._dirty = True

    def unban_user(self, user_id: str):
        self._data["bans"].pop(user_id, None)
        self._dirty = True

    def is_banned(self, user_id: str) -> bool:
        until = self._data.get("bans", {}).get(user_id)
        if not until:
            return False
        if self._now() > until:
            self.unban_user(user_id)
            return False
        return True

    def add_developer(self, username: str):
        username = username.strip()
        devs = self._data.get("developers", [])
        if username not in devs:
            devs.append(username)
            self._data["developers"] = devs
            self._dirty = True

    def remove_developer(self, username: str):
        username = username.strip()
        devs = self._data.get("developers", [])
        if username in devs:
            devs.remove(username)
            self._data["developers"] = devs
            self._dirty = True

    def is_developer(self, username: str) -> bool:
        username = username.strip().lower()
        return any(u.lower() == username for u in self._data.get("developers", []))

    def add_moderator(self, username: str):
        username = username.strip()
        mods = self._data.get("moderators", [])
        if username and username not in mods:
            mods.append(username)
            self._data["moderators"] = mods
            self._dirty = True

    def remove_moderator(self, username: str):
        username = username.strip()
        mods = self._data.get("moderators", [])
        if username in mods:
            mods.remove(username)
            self._data["moderators"] = mods
            self._dirty = True

    def is_moderator(self, username: str) -> bool:
        username = username.strip().lower()
        return any(u.lower() == username for u in self._data.get("moderators", []))
    
    def get_moderators(self):
        return list(self._data.get("moderators", []))

    def add_owner(self, username: str):
        username = username.strip()
        owners = self._data.get("owners", [])
        if username and username not in owners:
            owners.append(username)
            self._data["owners"] = owners
            self._dirty = True

    def remove_owner(self, username: str):
        username = username.strip()
        owners = self._data.get("owners", [])
        if username in owners:
            owners.remove(username)
            self._data["owners"] = owners
            self._dirty = True

    def is_owner(self, username: str) -> bool:
        username = username.strip().lower()
        return any(u.lower() == username for u in self._data.get("owners", []))

    def get_owners(self):
        return list(self._data.get("owners", []))

    def add_vip(self, username: str):
        username = username.strip()
        vips = self._data.get("vips", [])
        if username and username not in vips:
            vips.append(username)
            self._data["vips"] = vips
            self._dirty = True
        # default: no expiry update here

    def remove_vip(self, username: str):
        username = username.strip()
        vips = self._data.get("vips", [])
        if username in vips:
            vips.remove(username)
            self._data["vips"] = vips
            self._dirty = True
        self._data.get("vip_expiry", {}).pop(username, None)

    def is_vip(self, username: str) -> bool:
        username = username.strip().lower()
        if not any(u.lower() == username for u in self._data.get("vips", [])):
            return False
        expiry = self._data.get("vip_expiry", {}).get(username)
        if not expiry:
            return True
        return self._now() < int(expiry)

    def get_vips(self):
        return list(self._data.get("vips", []))

    def set_vip_expiry(self, username: str, until_ts: int):
        username = username.strip().lower()
        vips = self._data.get("vips", [])
        if not any(u.lower() == username for u in vips):
            vips.append(username)
            self._data["vips"] = vips
        self._data.setdefault("vip_expiry", {})[username] = int(until_ts)
        self._dirty = True

    def set_vip_location(self, position: Position):
        self._data["viploc"] = {
            "x": position.x,
            "y": position.y,
            "z": position.z,
            "facing": position.facing,
        }
        self._dirty = True

    def load_vip_position(self) -> Position:
        pos = self._data.get("viploc", {"x": 9.0, "y": 0.35, "z": 10.0, "facing": "FrontRight"})
        return Position(pos["x"], pos["y"], pos["z"], pos["facing"])

    def set_location(self, name: str, position: Position):
        name = (name or "").strip().lower()
        if not name:
            return
        self._data.setdefault("locations", {})[name] = {
            "x": position.x,
            "y": position.y,
            "z": position.z,
            "facing": position.facing,
        }
        self._dirty = True

    def remove_location(self, name: str):
        name = (name or "").strip().lower()
        locs = self._data.get("locations", {})
        if name in locs:
            locs.pop(name, None)
            self._data["locations"] = locs
            self._dirty = True

    def get_location(self, name: str) -> Position | None:
        name = (name or "").strip().lower()
        loc = self._data.get("locations", {}).get(name)
        if not loc:
            return None
        return Position(loc["x"], loc["y"], loc["z"], loc["facing"])

    def list_locations(self):
        return list(self._data.get("locations", {}).keys())

    def set_filter_enabled(self, enabled: bool):
        f = self._data.get("filter", {})
        f["enabled"] = bool(enabled)
        self._data["filter"] = f
        self._dirty = True

    def get_filter_enabled(self) -> bool:
        return bool(self._data.get("filter", {}).get("enabled", False))

    def add_filter_word(self, word: str):
        word = (word or "").strip().lower()
        if not word:
            return
        f = self._data.get("filter", {})
        words = list(f.get("words", []))
        if word not in words:
            words.append(word)
        f["words"] = words
        self._data["filter"] = f
        self._dirty = True

    def remove_filter_word(self, word: str):
        word = (word or "").strip().lower()
        f = self._data.get("filter", {})
        words = list(f.get("words", []))
        if word in words:
            words.remove(word)
        f["words"] = words
        self._data["filter"] = f
        self._dirty = True

    def get_filter_words(self):
        return list(self._data.get("filter", {}).get("words", []))

    def add_warn(self, user_id: str, username: str, reason: str, word: str | None = None):
        warns = self._data.get("warns", {})
        wl = list(warns.get(user_id, []))
        wl.append({"username": username, "reason": reason, "word": word or "", "time": self._now()})
        warns[user_id] = wl
        self._data["warns"] = warns
        self._dirty = True

    def get_warns(self, user_id: str):
        return list(self._data.get("warns", {}).get(user_id, []))

    def clear_warns(self, user_id: str):
        warns = self._data.get("warns", {})
        if user_id in warns:
            warns.pop(user_id, None)
            self._data["warns"] = warns
            self._dirty = True

    def set_rules(self, text: str):
        self._data["rules_text"] = str(text or "").strip()
        self._dirty = True

    def get_rules(self) -> str:
        return str(self._data.get("rules_text", ""))

    def set_greet_text(self, lang: str, text: str):
        key = "greet_text_en"
        self._data[key] = str(text or "").strip()
        self._dirty = True

    def get_greet_text(self, lang: str) -> str:
        return str(self._data.get("greet_text_en", ""))

    def set_greet_whisper(self, enabled: bool):
        self._data["greet_whisper"] = bool(enabled)
        self._dirty = True

    def get_greet_whisper(self) -> bool:
        return bool(self._data.get("greet_whisper", True))

    def add_sub(self, user_id: str, username: str):
        subs = list(self._data.get("subs", []))
        exists = any(s.get("id") == user_id for s in subs)
        if not exists:
            subs.append({"id": user_id, "username": username})
            self._data["subs"] = subs
            self._dirty = True

    def remove_sub(self, user_id: str):
        subs = list(self._data.get("subs", []))
        subs = [s for s in subs if s.get("id") != user_id]
        self._data["subs"] = subs
        self._dirty = True

    def get_subs(self):
        return list(self._data.get("subs", []))

    def set_sub_conversation(self, user_id: str, conversation_id: str):
        subs = list(self._data.get("subs", []))
        updated = False
        for s in subs:
            if s.get("id") == user_id:
                s["conversation_id"] = conversation_id
                updated = True
                break
        if updated:
            self._data["subs"] = subs
            self._dirty = True

    def set_freeze_position(self, user_id: str, position: Position):
        self._data.setdefault("freeze_pos", {})[user_id] = {
            "x": position.x,
            "y": position.y,
            "z": position.z,
            "facing": position.facing,
        }
        self._dirty = True

    def get_freeze_position(self, user_id: str) -> Position | None:
        fp = self._data.get("freeze_pos", {}).get(user_id)
        if not fp:
            return None
        return Position(fp["x"], fp["y"], fp["z"], fp["facing"])

    def clear_freeze_position(self, user_id: str):
        fps = self._data.get("freeze_pos", {})
        if user_id in fps:
            fps.pop(user_id, None)
            self._data["freeze_pos"] = fps
            self._dirty = True

    def set_frozen(self, user_id: str, frozen: bool = True):
        fz = self._data.get("frozen", {})
        if frozen:
            fz[user_id] = True
        else:
            fz.pop(user_id, None)
        self._data["frozen"] = fz
        self._dirty = True

    def is_frozen(self, user_id: str) -> bool:
        return bool(self._data.get("frozen", {}).get(user_id, False))
