import asyncio
import random
import traceback
from highrise import BaseBot, __main__, CurrencyItem, Item, Position, AnchorPosition, SessionMetadata, User
from highrise.__main__ import BotDefinition
from storage import Storage
from commands import CommandRouter
from emotes import ALL_EMOTE_LIST

class HighriseBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.bot_id = None
        self.owner_id = None
        self.bot_status = False
        self.paused = False
        self.storage = Storage()
        self.bot_position = None
        self.router = CommandRouter(self)
        self.webapi = None
        self.Position = Position
        self._dance_task = None
        self._dance_emote = None
        self._dance_interval = 6.0
        self.allow_public_emote_triggers = True
        self.language = "en"
        self.greet_enabled = True
        self.room_id = None
        self._greet_index = 0
        self._greet_messages_ar = [
            "اهلاً وسهلاً {name}!",
            "نورّت المكان يا {name}!",
            "حياك الله يا {name}!",
            "تشرفنا بوجودك {name}!",
            "مرحباً {name}!",
        ]
        self._greet_messages_en = [
            "Welcome {name}!",
            "Nice to see you, {name}!",
            "Glad you're here, {name}!",
            "Great to have you, {name}!",
            "Hello {name}!",
        ]
        self._greet_dev_ar = "أهلاً بالمطور {name}!"
        self._greet_owner_ar = "أهلاً بصانع البوت {name}!"
        self._greet_dev_en = "Welcome, developer {name}!"
        self._greet_owner_en = "Welcome, bot owner {name}!"
        self._user_loops = {}
        self._follow_task = None
        self._frozen_tasks = {}
        self._follow_target = None
        self._follow_interval = 1.0
        self._flash_task = None
        self._flash_interval = 0.05
        self._announce_task = None
        self._announce_interval = 1800.0
        self._announce_message = None
        self._presence = {}
        self._filter_mute_seconds = 600
        self._default_facing = "FrontRight"
        self._dm_reminder_tasks = {}
        self.lock_user = None
        self.lock_user_id = None

    async def _dm_reminder_loop(self, user_id: str):
        try:
            while not self.storage.has_dmed(user_id):
                if user_id not in self._presence:
                    break
                try:
                    await self.highrise.send_whisper(user_id, "Please DM me 'hello' to unlock commands!")
                except Exception:
                    pass
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"dm_reminder_error: {e}")
        finally:
            self._dm_reminder_tasks.pop(user_id, None)

    async def on_chat(self, user: User, message: str) -> None:
        if getattr(self, "lock_user_id", None):
            if user.id != self.lock_user_id:
                return
        elif getattr(self, "lock_user", None):
            if not (user.username and user.username.strip().lower() == str(self.lock_user).strip().lower()):
                return
        if self.storage.is_banned(user.id) or self.storage.is_muted(user.id) or self.storage.is_frozen(user.id):
            return
        
        if not self.storage.has_dmed(user.id) and message.strip().startswith("!"):
            privileged = (user.id == self.owner_id) or self.storage.is_developer(user.username) or self.storage.is_moderator(user.username)
            if not privileged:
                cmdl = message.strip().lower()
                if cmdl.startswith("!lb") or cmdl.startswith("!stopbot") or cmdl.startswith("!startbot") or cmdl.startswith("!lockbot") or cmdl.startswith("!unlockbot"):
                    pass
                else:
                    if self.router._can_send(user.id, "dm_warn", 30):
                        try:
                            await self.highrise.send_whisper(user.id, "Please DM me 'hello' to use commands!")
                        except Exception:
                            pass
                    return

        try:
            if self.storage.get_filter_enabled():
                is_privileged = (user.id == self.owner_id) or self.storage.is_developer(user.username)
                if not is_privileged:
                    msgl = (message or "").lower()
                    for w in self.storage.get_filter_words():
                        if w and w in msgl:
                            self.storage.mute_user(user.id, self._filter_mute_seconds)
                            try:
                                await self.highrise.moderate_room(user.id, "mute", self._filter_mute_seconds)
                            except Exception:
                                pass
                            try:
                                await self.highrise.send_whisper(user.id, "You have been muted.")
                            except Exception:
                                pass
                            try:
                                self.storage.add_warn(user.id, user.username, "filtered word", w)
                            except Exception:
                                pass
                            return
        except Exception:
            pass
        try:
            msg = (message or "").strip()
            if msg and not msg.startswith("!"):
                self.storage.add_chat_message(user.id, user.username)
        except Exception:
            pass
        if self.allow_public_emote_triggers:
            m = message.strip()
            if m.isdigit():
                idx = int(m)
                if idx == 0:
                    try:
                        await self.highrise.send_emote("idle-loop-sitfloor", user.id)
                    except Exception:
                        pass
                    return
                await self.emote_user_by_index(user.id, idx)
                return
            if m.lower() in ("loopstop", "stop", "توقف") or m.lower() == "stop loop":
                try:
                    await self.stop_user_loop(user.id)
                except Exception as e:
                    print(f"stop_loop_error: {e}")
                return
            if m.lower() in ("لمس",):
                try:
                    await self.highrise.send_emote("emoji-there", user.id)
                except Exception:
                    pass
                return
            if m.lower() in ("عناق",):
                try:
                    await self.highrise.send_emote("emote-hug", user.id)
                except Exception:
                    pass
                return
            if m.lower() in ("ghost", "جوست"):
                try:
                    await self.start_user_loop_code(user.id, "emote-ghost-idle")
                    try:
                        await self.highrise.send_whisper(user.id, "Ghost mode activated")
                    except Exception:
                        pass
                except Exception as e:
                    print(f"ghost_loop_error: {e}")
                return
            if m.lower() in ("rest", "ريست"):
                try:
                    await self.highrise.send_emote("idle-loop-sitfloor", user.id)
                except Exception:
                    pass
                return

            for lbl, code in ALL_EMOTE_LIST:
                if m.lower() == lbl.lower() or m.lower() == lbl.lower().replace(" ", ""):
                    try:
                        await self.start_user_loop_code(user.id, code)
                    except Exception:
                        pass
                    return

            if (self.language in ("both", "ar") and m.lower().startswith("اذهب ")) or (self.language in ("both", "en") and m.lower().startswith("go ")):
                try:
                    if user.id == self.owner_id or self.storage.is_developer(user.username):
                        parts = m.split()
                        if len(parts) >= 2:
                            target = parts[1].replace("@", "")
                            uid = await self.resolve_user_id(target)
                            if uid:
                                msg = await self.set_bot_position(uid)
                                if msg:
                                    try:
                                        await self.highrise.chat(msg)
                                    except Exception:
                                        pass
                            else:
                                try:
                                    await self.highrise.chat("User not found")
                                except Exception:
                                    pass
                    return
                except Exception as e:
                    print(f"goto_error: {e}")
                    return
            if (self.language in ("both", "en") and m.lower().startswith("br ")) or (self.language in ("both", "ar") and m.lower().startswith("جيب ")) or (self.language in ("both", "en") and m.lower().startswith("bring ")):
                try:
                    if user.id == self.owner_id or self.storage.is_developer(user.username):
                        parts = m.split()
                        if len(parts) >= 2:
                            target = parts[1].replace("@", "")
                            uid = await self.resolve_user_id(target)
                            if uid:
                                msg = await self.bring_to_user(uid, user.id)
                                if msg:
                                    try:
                                        await self.highrise.chat(msg)
                                    except Exception:
                                        pass
                            else:
                                try:
                                    await self.highrise.chat("User not found")
                                except Exception:
                                    pass
                    return
                except Exception as e:
                    print(f"bring_error: {e}")
                    return
            if (self.language in ("both", "ar") and m.lower().startswith("بدل ")) or (self.language in ("both", "en") and m.lower().startswith("swap ")):
                try:
                    if user.id == self.owner_id or self.storage.is_developer(user.username):
                        parts = m.split()
                        if len(parts) >= 3:
                            u1 = parts[1].replace("@", "")
                            u2 = parts[2].replace("@", "")
                            msg = await self.swap_users(u1, u2)
                            if msg:
                                try:
                                    await self.highrise.chat(msg)
                                except Exception:
                                    pass
                    return
                except Exception as e:
                    print(f"swap_error: {e}")
                    return
            if m.lower().startswith("/equip"):
                ok = False
                if user.id == self.owner_id or self.storage.is_developer(user.username):
                    parts = m.split()
                    preset = parts[1].lower() if len(parts) > 1 else "black"
                    items = []
                    if preset == "black":
                        items = [
                            Item(type="clothing", amount=1, id="body-flesh", account_bound=False, active_palette=27),
                            Item(type="clothing", amount=1, id="eye-n_basic2018malesquaresleepy", account_bound=False, active_palette=7),
                            Item(type="clothing", amount=1, id="eyebrow-n_basic2018newbrows07", account_bound=False, active_palette=0),
                            Item(type="clothing", amount=1, id="nose-n_basic2018newnose05", account_bound=False, active_palette=0),
                            Item(type="clothing", amount=1, id="mouth-basic2018chippermouth", account_bound=False, active_palette=-1),
                            Item(type="clothing", amount=1, id="bag-n_room32019sweaterwrapblack", account_bound=False, active_palette=-1),
                            Item(type="clothing", amount=1, id="shirt-n_starteritems2019tankblack", account_bound=False, active_palette=-1),
                            Item(type="clothing", amount=1, id="shorts-n_starteritems2019longshortsblack", account_bound=False, active_palette=-1),
                        ]
                        try:
                            await self.highrise.set_outfit(outfit=items)
                            ok = True
                        except Exception:
                            ok = False
                if ok:
                    try:
                        await self.highrise.chat("تم تجهيز ملابس سوداء")
                    except Exception:
                        pass
                else:
                    try:
                        await self.highrise.chat("فشل تجهيز الملابس أو ليس لديك صلاحية")
                    except Exception:
                        pass
                return
            if m.lower().startswith("!outfit1"):
                if user.id == self.owner_id or self.storage.is_developer(user.username):
                    requested_ids = [
                        "pants-n_onesiedailies2017blackpants",
                        "shirt-n_onesiedailies2017blacktop",
                        "hat-n_onesiedailies2017cathood_3",
                        "skirt-n_schoolreportertightskirt",
                        "freckle-n_registrationavatars2023contour",
                        "eye-n_aprilfoolsinvisible2020eyes",
                        "mouth-n_aprilfoolsinvisible2020mouth",
                        "eyebrow-n_aprilfoolsinvisible2020eyebrows",
                    ]
                    base_items = [Item(type="clothing", amount=1, id=i, account_bound=False, active_palette=-1) for i in requested_ids]
                    applied = False
                    try:
                        await self.highrise.set_outfit(outfit=base_items)
                        applied = True
                    except Exception:
                        applied = False
                    await asyncio.sleep(0.5)
                    verified_ids = []
                    try:
                        resp = None
                        if hasattr(self.highrise, "get_my_outfit"):
                            resp = await self.highrise.get_my_outfit()
                        elif hasattr(self.highrise, "get_outfit"):
                            resp = await self.highrise.get_outfit(self.bot_id)
                        elif hasattr(self.highrise, "get_user_outfit"):
                            resp = await self.highrise.get_user_outfit(self.bot_id)
                        if resp and hasattr(resp, "outfit"):
                            verified_ids = [getattr(it, "id", "") for it in resp.outfit]
                    except Exception:
                        pass
                    missing = [iid for iid in requested_ids if iid not in verified_ids]
                    if missing:
                        try:
                            items_with_body = [Item(type="clothing", amount=1, id="body-flesh", account_bound=False, active_palette=27)] + base_items
                            await self.highrise.set_outfit(outfit=items_with_body)
                            await asyncio.sleep(0.5)
                            resp2 = None
                            if hasattr(self.highrise, "get_my_outfit"):
                                resp2 = await self.highrise.get_my_outfit()
                            elif hasattr(self.highrise, "get_outfit"):
                                resp2 = await self.highrise.get_outfit(self.bot_id)
                            elif hasattr(self.highrise, "get_user_outfit"):
                                resp2 = await self.highrise.get_user_outfit(self.bot_id)
                            if resp2 and hasattr(resp2, "outfit"):
                                verified_ids = [getattr(it, "id", "") for it in resp2.outfit]
                                missing = [iid for iid in requested_ids if iid not in verified_ids]
                        except Exception:
                            pass
                    applied_count = len([iid for iid in requested_ids if iid in verified_ids])
                    if applied_count == len(requested_ids):
                        try:
                            await self.highrise.chat("Outfit1 applied")
                        except Exception:
                            pass
                    elif applied_count > 0:
                        try:
                            await self.highrise.chat("Outfit1 partially applied: " + ", ".join([iid for iid in requested_ids if iid in verified_ids]) + ". Missing: " + ", ".join(missing))
                        except Exception:
                            pass
                    else:
                        try:
                            await self.highrise.chat("Failed to apply outfit")
                        except Exception:
                            pass
                    return
                try:
                    await self.highrise.chat("Failed to apply outfit or unauthorized")
                except Exception:
                    pass
                return
            if m.lower().startswith("!outfit2"):
                if user.id == self.owner_id or self.storage.is_developer(user.username):
                    requested_ids = [
                        "eye-n_basic2018malesquaresleepy",
                        "eyebrow-n_basic2018newbrows07",
                        "nose-n_basic2018newnose05",
                        "mouth-basic2018chippermouth",
                        "bag-n_room32019sweaterwrapblack",
                        "shirt-n_starteritems2019tankblack",
                        "shorts-n_starteritems2019longshortsblack",
                    ]
                    base_items = [Item(type="clothing", amount=1, id=i, account_bound=False, active_palette=-1) for i in requested_ids]
                    try:
                        await self.highrise.set_outfit(outfit=base_items)
                        await asyncio.sleep(0.5)
                        resp = None
                        if hasattr(self.highrise, "get_my_outfit"):
                            resp = await self.highrise.get_my_outfit()
                        elif hasattr(self.highrise, "get_outfit"):
                            resp = await self.highrise.get_outfit(self.bot_id)
                        elif hasattr(self.highrise, "get_user_outfit"):
                            resp = await self.highrise.get_user_outfit(self.bot_id)
                        verified_ids = [getattr(it, "id", "") for it in (resp.outfit if resp and hasattr(resp, "outfit") else [])]
                        missing = [iid for iid in requested_ids if iid not in verified_ids]
                        if missing:
                            items_with_body = [Item(type="clothing", amount=1, id="body-flesh", account_bound=False, active_palette=27)] + base_items
                            await self.highrise.set_outfit(outfit=items_with_body)
                        await self.highrise.chat("Outfit2 applied")
                    except Exception:
                        try:
                            await self.highrise.chat("Failed to apply outfit")
                        except Exception:
                            pass
                    return
                try:
                    await self.highrise.chat("Failed to apply outfit or unauthorized")
                except Exception:
                    pass
                return
            if m.lower().startswith("!outfit3"):
                if user.id == self.owner_id or self.storage.is_developer(user.username):
                    requested_ids = [
                        "eye-n_aprilfoolsinvisible2020eyes",
                        "mouth-n_aprilfoolsinvisible2020mouth",
                        "eyebrow-n_aprilfoolsinvisible2020eyebrows",
                        "shirt-n_starteritems2019tankblack",
                        "pants-n_onesiedailies2017blackpants",
                        "hat-n_onesiedailies2017cathood_3",
                    ]
                    base_items = [Item(type="clothing", amount=1, id=i, account_bound=False, active_palette=-1) for i in requested_ids]
                    try:
                        await self.highrise.set_outfit(outfit=base_items)
                        await asyncio.sleep(0.5)
                        items_with_body = [Item(type="clothing", amount=1, id="body-flesh", account_bound=False, active_palette=27)] + base_items
                        await self.highrise.set_outfit(outfit=items_with_body)
                        await self.highrise.chat("Outfit3 applied")
                    except Exception:
                        try:
                            await self.highrise.chat("Failed to apply outfit")
                        except Exception:
                            pass
                    return
                try:
                    await self.highrise.chat("Failed to apply outfit or unauthorized")
                except Exception:
                    pass
                return
            if m.lower().startswith("loop "):
                parts = m.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    idx = int(parts[1])
                    secs = self._parse_duration(parts[2]) if len(parts) > 2 else None
                    await self.start_user_loop(user.id, idx, secs)
                    return
            if m.lower() in ("loopstop", "stop loop"):
                await self.stop_user_loop(user.id)
                return
        resp = await self.router.handle(user.id, message, user.username)
        if resp:
            try:
                if isinstance(resp, list):
                    for r in resp:
                        await self.highrise.chat(r)
                        await asyncio.sleep(0.5)
                else:
                    await self.highrise.chat(resp)
            except Exception:
                pass

    async def on_whisper(self, user: User, message: str) -> None:
        if getattr(self, "lock_user_id", None):
            if user.id != self.lock_user_id:
                return
        elif getattr(self, "lock_user", None):
            if not (user.username and user.username.strip().lower() == str(self.lock_user).strip().lower()):
                return
        try:
            print(f"{user.username} whispered: {message}")
        except Exception:
            pass
        try:
            mlow = (message or "").strip().lower()
            if (mlow.startswith("!stopbot") or mlow.startswith("!lockbot")) and (user.username and user.username.strip().lower() == "ANTAURI"):
                self.paused = True
                self.lock_user = "ANTAURI"
                self.lock_user_id = user.id
                try:
                    if getattr(self, "_dance_task", None) and self._dance_task and not self._dance_task.done():
                        self._dance_task.cancel()
                        try:
                            await self._dance_task
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    for t in list(getattr(self, "_user_loops", {}).values()):
                        if t and not t.done():
                            t.cancel()
                            try:
                                await t
                            except Exception:
                                pass
                    try:
                        self._user_loops.clear()
                    except Exception:
                        pass
                except Exception:
                    pass
                for tname in ("_follow_task", "_flash_task", "_announce_task"):
                    try:
                        t = getattr(self, tname, None)
                        if t and not t.done():
                            t.cancel()
                            try:
                                await t
                            except Exception:
                                pass
                    except Exception:
                        pass
                try:
                    for uid, t in list(getattr(self, "_dm_reminder_tasks", {}).items()):
                        if t and not t.done():
                            t.cancel()
                    try:
                        self._dm_reminder_tasks.clear()
                    except Exception:
                        pass
                except Exception:
                    pass
                try:
                    await self.highrise.send_whisper(user.id, "تم الإيقاف بنجاح")
                except Exception:
                    pass
                return
            if (mlow.startswith("!startbot") or mlow.startswith("!unlockbot")) and (user.username and user.username.strip().lower() == "ANTAURI"):
                self.paused = False
                self.lock_user = None
                self.lock_user_id = None
                try:
                    await self.highrise.send_whisper(user.id, "تم التشغيل بنجاح")
                except Exception:
                    pass
                return
        except Exception:
            pass
        self.storage.add_dm_user(user.id)
        if self.storage.is_banned(user.id) or self.storage.is_muted(user.id) or self.storage.is_frozen(user.id):
            return
        resp = await self.router.handle(user.id, message, user.username)
        if resp:
            try:
                if isinstance(resp, list):
                    for r in resp:
                        await self.highrise.send_whisper(user.id, r)
                        await asyncio.sleep(0.5)
                else:
                    await self.highrise.send_whisper(user.id, resp)
            except Exception:
                pass

    async def on_message(self, user_id: str, conversation_id: str, is_new_conversation: bool) -> None:
        if getattr(self, "lock_user_id", None):
            if user_id != self.lock_user_id:
                return
        else:
            try:
                if getattr(self, "lock_user", None):
                    info = await self.webapi.get_user(user_id) if self.webapi else None
                    uname = getattr(getattr(info, "user", None), "username", None) if info else None
                    if not (uname and uname.strip().lower() == str(self.lock_user).strip().lower()):
                        return
            except Exception:
                pass
        if self.storage.is_banned(user_id) or self.storage.is_muted(user_id) or self.storage.is_frozen(user_id):
            return
        conversation = await self.highrise.get_messages(conversation_id)
        msg_obj = None
        try:
            msgs = getattr(conversation, "messages", []) or []
            if msgs:
                msg_obj = msgs[-1]
        except Exception:
            msg_obj = None
        if not msg_obj:
            return
        message = getattr(msg_obj, "content", None)
        if not isinstance(message, str):
            return
        try:
            info = await self.webapi.get_user(user_id) if self.webapi else None
            uname = getattr(getattr(info, "user", None), "username", None) if info else None
        except Exception:
            uname = None
        try:
            mlow = (message or "").strip().lower()
            if (mlow.startswith("!stopbot") or mlow.startswith("!lockbot")) and (uname and uname.strip().lower() == "ANTAURI"):
                self.paused = True
                self.lock_user = "ANTAURI"
                self.lock_user_id = user_id
                try:
                    await self.highrise.send_message(conversation_id, "تم الإيقاف بنجاح")
                except Exception:
                    pass
                return
            if (mlow.startswith("!startbot") or mlow.startswith("!unlockbot")) and (uname and uname.strip().lower() == "navidfrb"):
                self.paused = False
                self.lock_user = None
                self.lock_user_id = None
                try:
                    await self.highrise.send_message(conversation_id, "تم التشغيل بنجاح")
                except Exception:
                    pass
                return
        except Exception:
            pass
        uname = None
        try:
            info = await self.webapi.get_user(user_id) if self.webapi else None
            u = getattr(info, "user", None)
            uname = getattr(u, "username", None) if u else None
        except Exception:
            uname = None
        try:
            if message and message.strip().lower() == "hello":
                if not self.storage.has_dmed(user_id):
                    self.storage.add_dm_user(user_id)
                    try:
                        await self.highrise.send_message(conversation_id, "You have unlocked commands! Type !help to see what you can do.")
                    except Exception:
                        pass
                    # Stop reminder if running
                    if user_id in self._dm_reminder_tasks:
                        self._dm_reminder_tasks[user_id].cancel()
            
            if (message or "").strip().lower().startswith("!sub"):
                uname = ""
                try:
                    info = await self.webapi.get_user(user_id) if self.webapi else None
                except Exception:
                    info = None
                try:
                    u = getattr(info, "user", None)
                    uname = getattr(u, "username", "") if u else uname
                except Exception:
                    pass
                try:
                    self.storage.add_sub(user_id, uname or "")
                except Exception:
                    pass
                try:
                    self.storage.set_sub_conversation(user_id, conversation_id)
                except Exception:
                    pass
        except Exception:
            pass
        resp = await self.router.handle(user_id, message, uname)
        if resp:
            try:
                if isinstance(resp, list):
                    for r in resp:
                        await self.highrise.send_message(conversation_id, r)
                        await asyncio.sleep(0.5)
                else:
                    await self.highrise.send_message(conversation_id, resp)
            except Exception:
                pass

    async def on_tip(self, sender: User, receiver: User, tip: CurrencyItem | Item) -> None:
        if isinstance(tip, CurrencyItem):
            if receiver.id == self.bot_id:
                self.storage.add_tip(sender.id, sender.username, tip.amount)
                if tip.amount >= 500:
                    await self.highrise.chat(f"Thank you {sender.username} for the generous {tip.amount}g tip!")

    async def on_user_join(self, user: User, position: Position | AnchorPosition) -> None:
        if self.storage.is_banned(user.id):
            try:
                await self.highrise.send_whisper(user.id, "You are banned.")
            except Exception:
                pass
            return
        try:
            self._presence[user.id] = asyncio.get_event_loop().time()
            if not self.storage.has_dmed(user.id):
                if user.id not in self._dm_reminder_tasks:
                    self._dm_reminder_tasks[user.id] = asyncio.create_task(self._dm_reminder_loop(user.id))
        except Exception:
            pass
        if self.greet_enabled:
            msg = None
            idx = self._greet_index
            is_owner = user.id == self.owner_id
            is_dev = self.storage.is_developer(user.username)
            if self.language == "en":
                if is_owner:
                    msg = self._greet_owner_en.replace("{name}", user.username)
                elif is_dev:
                    msg = self._greet_dev_en.replace("{name}", user.username)
                else:
                    custom = self.storage.get_greet_text("en")
                    if custom:
                        msg = custom.replace("{name}", user.username)
                    else:
                        m = self._greet_messages_en[idx % len(self._greet_messages_en)]
                        msg = m.replace("{name}", user.username)
            self._greet_index += 1
            try:
                if self.storage.get_greet_whisper():
                    await self.highrise.send_whisper(user.id, msg)
                else:
                    await self.highrise.chat(msg)
                await asyncio.sleep(1)
                await self.highrise.send_whisper(user.id, "Type !help or !emotelist to see commands.")
            except Exception:
                pass
        # enforce freeze lock on join
        try:
            if self.storage.is_frozen(user.id):
                # ensure monitoring resumes
                await self.start_freeze_monitor(user.id)
        except Exception:
            pass
        
    async def on_user_leave(self, user: User) -> None:
        try:
            start = self._presence.pop(user.id, None)
            if start:
                elapsed = max(0.0, asyncio.get_event_loop().time() - start)
                try:
                    self.storage.add_time_spent(user.id, user.username, elapsed)
                except Exception:
                    pass
            if user.id in self._dm_reminder_tasks:
                self._dm_reminder_tasks[user.id].cancel()
            await self.stop_user_loop(user.id)
        except Exception:
            pass
        return

    async def on_start(self, session_metadata: SessionMetadata) -> None:
        try:
            # In 24.1.0, webapi might be under different attribute or requires manual init
            # Try standard location or check if available
            self.webapi = getattr(self.highrise, "webapi", None)
            if not self.webapi:
                # Some SDK versions don't expose webapi directly on BaseBot.highrise
                # It might be self.web_api or just not initialized.
                # Suppress warning to avoid user confusion if it's just missing in this version
                pass
        except Exception as e:
            print(f"Error setting webapi: {e}")
        
        self.bot_id = session_metadata.user_id
        self.owner_id = session_metadata.room_info.owner_id
        self.room_name = session_metadata.room_info.room_name
        try:
            self.room_id = getattr(session_metadata.room_info, "room_id", None) or getattr(session_metadata.room_info, "id", None)
        except Exception:
            self.room_id = None
        self.storage.add_developer("ANTAURI")
        self.bot_status = True
        
        await self.place_bot()
        asyncio.create_task(self._auto_flush())
        try:
            await self.start_announce(1800.0, "code by RAKA TEAM")
        except Exception:
            pass
        try:
            room_users = await self.highrise.get_room_users()
            now = asyncio.get_event_loop().time()
            for ru, _ in room_users.content:
                self._presence.setdefault(ru.id, now)
        except Exception:
            pass

    def get_top_tippers(self):
        return self.storage.get_top_tippers(10)

    def get_user_tip_amount(self, username):
        return self.storage.get_user_tip_amount_by_username(username)

    async def place_bot(self):
        try:
            self.bot_position = self.storage.load_bot_position()
            if self.bot_position != Position(0, 0, 0, "FrontRight"):
                await self.highrise.teleport(self.bot_id, self.bot_position)
        except Exception as e:
            print(f"Error placing bot: {e}")

    async def set_bot_position(self, user_id) -> None:
        position = None
        try:
            room_users = await self.highrise.get_room_users()
            for room_user, pos in room_users.content:
                if user_id == room_user.id:
                    if isinstance(pos, Position):
                        position = pos
            if position is not None:
                self.storage.save_bot_position(position)
                set_position = Position(position.x, (position.y + 0.0000001), position.z, facing=position.facing)
                await self.highrise.teleport(self.bot_id, set_position)
                await self.highrise.teleport(self.bot_id, position)
                await self.highrise.walk_to(position)
                return "Updated bot position."
            else:
                return "Failed to update bot position."
        except Exception:
            return "Failed to update bot position."

    async def _auto_flush(self):
        while True:
            await asyncio.sleep(1.0)
            try:
                self.storage.flush()
            except Exception as e:
                print(f"Error in auto_flush: {e}")

    async def resolve_user_id(self, username: str):
        username = username.strip().lower()
        try:
            room_users = await self.highrise.get_room_users()
            for room_user, _ in room_users.content:
                if room_user.username.lower() == username:
                    return room_user.id
        except Exception:
            return None
        return None

    async def start_dance(self, emote: str = "dance-floss"):
        if self._dance_task and not self._dance_task.done():
            self._dance_emote = emote
            return "dance already running"
        self._dance_emote = emote
        async def _loop():
            try:
                while True:
                    try:
                        await self.highrise.send_emote(self._dance_emote)
                    except Exception:
                        await asyncio.sleep(2.0)
                    await asyncio.sleep(self._dance_interval)
            except asyncio.CancelledError:
                return
        self._dance_task = asyncio.create_task(_loop())
        return "dance started"

    async def stop_dance(self):
        if self._dance_task and not self._dance_task.done():
            self._dance_task.cancel()
            try:
                await self._dance_task
            except Exception:
                pass
            self._dance_task = None
            return "dance stopped"
        return "dance not running"

    async def emote_by_index(self, index: int):
        from emotes import ALL_EMOTE_LIST
        if index < 1 or index > len(ALL_EMOTE_LIST):
            return
        _, code = ALL_EMOTE_LIST[index - 1]
        try:
            await self.highrise.send_emote(code)
        except Exception:
            pass

    async def emote_user_by_index(self, user_id: str, index: int):
        from emotes import ALL_EMOTE_LIST
        if index < 1 or index > len(ALL_EMOTE_LIST):
            return
        _, code = ALL_EMOTE_LIST[index - 1]
        try:
            await self.highrise.send_emote(code, user_id)
        except Exception:
            pass

    async def start_loop2(self, i1: int, i2: int, interval: float = None):
        from emotes import ALL_EMOTE_LIST
        if i1 < 1 or i1 > len(ALL_EMOTE_LIST):
            return "invalid"
        if i2 < 1 or i2 > len(ALL_EMOTE_LIST):
            return "invalid"
        delay = interval if interval and interval > 0 else self._dance_interval
        async def _loop():
            try:
                while True:
                    await self.emote_by_index(i1)
                    await asyncio.sleep(delay)
                    await self.emote_by_index(i2)
                    await asyncio.sleep(delay)
            except asyncio.CancelledError:
                return
        if self._dance_task and not self._dance_task.done():
            self._dance_task.cancel()
            try:
                await self._dance_task
            except Exception:
                pass
        self._dance_task = asyncio.create_task(_loop())
        return "loop2 started"

    async def start_loop(self, i: int, interval: float = None):
        from emotes import ALL_EMOTE_LIST
        if i < 1 or i > len(ALL_EMOTE_LIST):
            return "invalid"
        delay = interval if interval and interval > 0 else self._dance_interval
        async def _loop():
            try:
                while True:
                    await self.emote_by_index(i)
                    await asyncio.sleep(delay)
            except asyncio.CancelledError:
                return
        if self._dance_task and not self._dance_task.done():
            self._dance_task.cancel()
            try:
                await self._dance_task
            except Exception:
                pass
        self._dance_task = asyncio.create_task(_loop())
        return "loop started"

    def _parse_duration(self, s: str | None):
        if not s:
            return None
        t = s.strip().lower()
        if not t:
            return None
        unit = t[-1]
        try:
            num = float(t[:-1]) if unit in ("s", "m", "h", "d") else float(t)
        except Exception:
            return None
        if unit == "s":
            return float(num)
        if unit == "m":
            return float(num) * 60.0
        if unit == "h":
            return float(num) * 3600.0
        if unit == "d":
            return float(num) * 86400.0
        return float(num)

    async def start_user_loop(self, user_id: str, i: int, interval: float | None = None):
        from emotes import ALL_EMOTE_LIST
        if i < 1 or i > len(ALL_EMOTE_LIST):
            return
        delay = interval if interval and interval > 0 else self._dance_interval
        async def _loop():
            try:
                while True:
                    await self.emote_user_by_index(user_id, i)
                    await asyncio.sleep(delay)
            except asyncio.CancelledError:
                return
        task = self._user_loops.get(user_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except Exception:
                pass
        self._user_loops[user_id] = asyncio.create_task(_loop())

    async def stop_user_loop(self, user_id: str):
        task = self._user_loops.get(user_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except Exception:
                pass
        self._user_loops.pop(user_id, None)

    async def start_user_loop_code(self, user_id: str, code: str, interval: float | None = None):
        delay = interval if interval and interval > 0 else self._dance_interval
        async def _loop():
            try:
                while True:
                    try:
                        await self.highrise.send_emote(code, user_id)
                    except Exception as e:
                        print(f"user_emote_error: {e}")
                        await asyncio.sleep(1.0)
                    await asyncio.sleep(delay)
            except asyncio.CancelledError:
                return
        task = self._user_loops.get(user_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except Exception:
                pass
        self._user_loops[user_id] = asyncio.create_task(_loop())

    async def _get_bot_position(self):
        try:
            room_users = await self.highrise.get_room_users()
            for room_user, pos in room_users.content:
                if room_user.id == self.bot_id and isinstance(pos, Position):
                    return pos
        except Exception:
            pass
        try:
            return self.storage.load_bot_position()
        except Exception:
            return None

    async def _get_user_position(self, user_id: str):
        try:
            room_users = await self.highrise.get_room_users()
            for room_user, pos in room_users.content:
                if room_user.id == user_id and isinstance(pos, Position):
                    return pos
        except Exception:
            return None

    async def start_freeze_monitor(self, user_id: str):
        # record current position if missing
        try:
            if not self.storage.get_freeze_position(user_id):
                pos = await self._get_user_position(user_id)
                if pos:
                    self.storage.set_freeze_position(user_id, pos)
        except Exception:
            pass
        # cancel existing
        try:
            t = self._frozen_tasks.get(user_id)
            if t and not t.done():
                t.cancel()
        except Exception:
            pass
        async def _loop():
            while self.storage.is_frozen(user_id):
                try:
                    fp = self.storage.get_freeze_position(user_id)
                    cur = await self._get_user_position(user_id)
                    if fp and cur and hasattr(cur, "x"):
                        dx = abs(cur.x - fp.x) + abs(cur.y - fp.y) + abs(cur.z - fp.z)
                        if dx > 0.001 or cur.facing != fp.facing:
                            await self.highrise.teleport(user_id, fp)
                    await asyncio.sleep(0.3)
                except Exception:
                    await asyncio.sleep(0.5)
        try:
            self._frozen_tasks[user_id] = asyncio.create_task(_loop())
        except Exception:
            pass

    async def stop_freeze_monitor(self, user_id: str):
        try:
            t = self._frozen_tasks.get(user_id)
            if t and not t.done():
                t.cancel()
            self._frozen_tasks.pop(user_id, None)
        except Exception:
            pass

    async def bring_to_user(self, target_user_id: str, sender_user_id: str):
        pos = await self._get_user_position(sender_user_id)
        if not pos:
            return "Position not found"
        try:
            await self.highrise.teleport(target_user_id, pos)
            return "brought"
        except Exception:
            return "Failed to bring"

    async def swap_users(self, u1: str, u2: str):
        id1 = await self.resolve_user_id(u1)
        id2 = await self.resolve_user_id(u2)
        if not id1 or not id2:
            return "User not found"
        try:
            room_users = await self.highrise.get_room_users()
            pos_map = {}
            for room_user, pos in room_users.content:
                if isinstance(pos, Position):
                    pos_map[room_user.id] = pos
            p1 = pos_map.get(id1)
            p2 = pos_map.get(id2)
            if not p1 or not p2:
                return "Position not found"
            await self.highrise.teleport(id1, p2)
            await self.highrise.teleport(id2, p1)
            return "swapped"
        except Exception:
            return "Failed to swap"

    async def start_follow(self, user_id: str):
        if self._follow_task and not self._follow_task.done():
            self._follow_task.cancel()
            try:
                await self._follow_task
            except Exception:
                pass
        self._follow_target = user_id
        async def _loop():
            try:
                while True:
                    pos = await self._get_user_position(user_id)
                    if pos:
                        try:
                            await self.highrise.walk_to(pos)
                        except Exception:
                            try:
                                await self.highrise.teleport(self.bot_id, pos)
                            except Exception:
                                pass
                    await asyncio.sleep(self._follow_interval)
            except asyncio.CancelledError:
                return
        self._follow_task = asyncio.create_task(_loop())
        return "follow started"

    async def start_flash(self, actor_id: str, target_user_id: str | None = None):
        if self._flash_task and not self._flash_task.done():
            self._flash_task.cancel()
            try:
                await self._flash_task
            except Exception:
                pass
        async def _loop():
            try:
                last = None
                while True:
                    pos = await self._get_user_position(actor_id)
                    if pos:
                        try:
                            if last is None:
                                last = pos
                            else:
                                dx = abs(pos.x - last.x) + abs(pos.y - last.y) + abs(pos.z - last.z)
                                changed = dx > 0.05 or (getattr(pos, "facing", None) != getattr(last, "facing", None))
                                if not changed:
                                    pass
                                else:
                                    if target_user_id:
                                        await self.highrise.teleport(target_user_id, pos)
                                    else:
                                        await self.highrise.teleport(self.bot_id, pos)
                                    return
                        except Exception:
                            pass
                    await asyncio.sleep(self._flash_interval)
            except asyncio.CancelledError:
                return
        self._flash_task = asyncio.create_task(_loop())
        return "flash started"

    async def stop_flash(self):
        t = self._flash_task
        if t and not t.done():
            t.cancel()
            try:
                await t
            except Exception:
                pass
        self._flash_task = None
        return "flash stopped"

    async def stop_follow(self):
        t = self._follow_task
        if t and not t.done():
            t.cancel()
            try:
                await t
            except Exception:
                pass
        self._follow_task = None
        self._follow_target = None
        return "follow stopped"

    async def start_announce(self, interval: float, message: str):
        if self._announce_task and not self._announce_task.done():
            self._announce_task.cancel()
            try:
                await self._announce_task
            except Exception:
                pass
        self._announce_interval = max(1.0, float(interval))
        self._announce_message = message
        async def _loop():
            try:
                while True:
                    try:
                        await self.highrise.chat(self._announce_message)
                    except Exception:
                        pass
                    await asyncio.sleep(self._announce_interval)
            except asyncio.CancelledError:
                return
        self._announce_task = asyncio.create_task(_loop())
        return "announce started"

    async def stop_announce(self):
        t = self._announce_task
        if t and not t.done():
            t.cancel()
            try:
                await t
            except Exception:
                pass
        self._announce_task = None
        self._announce_message = None
        return "announce stopped"

    def get_status(self):
        lang = getattr(self, "language", "both")
        greet = "on" if getattr(self, "greet_enabled", True) else "off"
        pub = "on" if getattr(self, "allow_public_emote_triggers", True) else "off"
        dance = "on" if (self._dance_task and not self._dance_task.done()) else "off"
        follow = "on" if (self._follow_task and not self._follow_task.done()) else "off"
        announce = "on" if (self._announce_task and not self._announce_task.done()) else "off"
        filt = "on" if self.storage.get_filter_enabled() else "off"
        return (
            f"language: {lang}\n"
            f"greet: {greet}\n"
            f"public-emotes: {pub}\n"
            f"dance: {dance}\n"
            f"follow: {follow}\n"
            f"announce: {announce}\n"
            f"filter: {filt}\n"
            f"anchor: {self._default_facing}\n"
            f"dance-interval: {self._dance_interval}s"
        )

    async def get_presence_durations(self):
        try:
            room_users = await self.highrise.get_room_users()
            now = asyncio.get_event_loop().time()
            items = []
            for ru, _ in room_users.content:
                if ru.id == self.bot_id:
                    continue
                start = self._presence.get(ru.id)
                if start is None:
                    start = now
                    self._presence[ru.id] = start
                dur = int(now - start)
                items.append((ru.username, dur))
            items.sort(key=lambda x: x[1], reverse=True)
            return items
        except Exception:
            return []

    def set_anchor(self, facing: str):
        self._default_facing = facing

    async def teleport_user_to_vip(self, user_id: str):
        try:
            pos = self.storage.load_vip_position()
            await self.highrise.teleport(user_id, pos)
            return "vip teleported"
        except Exception:
            return "Failed to vip"

    async def run_bot(self, room_id, api_key) -> None:
        backoff = 1
        while True:
            self.bot_status = False  # Reset status for new connection
            try:
                try:
                    self.room_id = room_id
                except Exception:
                    pass
                print(f"Connecting to room {room_id}...")
                # Removed background place_bot task
                definitions = [BotDefinition(self, room_id, api_key)]
                await __main__.main(definitions)
            except Exception as e:
                print(f"Connection lost: {e}")
                traceback.print_exc()
            except KeyboardInterrupt:
                print("Bot stopped by user.")
                break
            
            print(f"Connection closed. Reconnecting in {backoff} seconds...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)