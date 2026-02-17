import asyncio
import random
import time

class CommandRouter:
    def __init__(self, bot):
        self.bot = bot
        self._cd = {}

    def _can_send(self, user_id: str, key: str, interval: float = 1.5):
        now = time.monotonic()
        k = f"{user_id}:{key}"
        last = self._cd.get(k, 0.0)
        if now - last < interval:
            return False
        self._cd[k] = now
        return True

    def _make_chunks(self, text: str) -> list[str]:
        lines = text.split("\n")
        chunks = []
        cur = ""
        for ln in lines:
            add = (ln + "\n") if ln else "\n"
            if len(cur) + len(add) > 256:
                if cur:
                    chunks.append(cur.rstrip("\n"))
                    cur = ""
            cur += add
        if cur:
            chunks.append(cur.rstrip("\n"))
        return chunks

    async def handle(self, user_id: str, message: str, username: str | None = None):
        command = message.strip()
        low = command.lower()
        if getattr(self.bot, "lock_user_id", None):
            if user_id != self.bot.lock_user_id:
                return None
        elif getattr(self.bot, "lock_user", None):
            lu = str(self.bot.lock_user).strip().lower()
            if not (username and username.strip().lower() == lu):
                return None
        is_owner = (user_id == self.bot.owner_id) or (username == "ANTAURI") or (username and self.bot.storage.is_owner(username))
        is_mod = bool(username and self.bot.storage.is_moderator(username))
        is_dev = bool(username and (self.bot.storage.is_developer(username) or username == "ANTAURI"))
        is_vip = bool(username and self.bot.storage.is_vip(username))
        if not command.startswith("!"):
            nm = command.strip().lower()
            if nm:
                free_names = ("f1", "f2", "f3")
                if nm in free_names:
                    locpos = self.bot.storage.get_location(nm)
                    if locpos:
                        await self.bot.highrise.teleport(user_id, locpos)
                        return f"teleported to location {nm}"
                if nm == "vip":
                    if not (is_owner or is_dev or is_mod or is_vip):
                        paid = 0
                        if username:
                            paid = self.bot.get_user_tip_amount(username) or 0
                        if paid <= 0:
                            return "Tip the bot first"
                    pos = self.bot.storage.load_vip_position()
                    if not pos:
                        return "Location not found"
                    await self.bot.highrise.teleport(user_id, pos)
                    return "teleported to location vip"
                locpos = self.bot.storage.get_location(nm)
                if locpos:
                    if not (is_owner or is_dev or is_mod or is_vip):
                        paid = 0
                        if username:
                            paid = self.bot.get_user_tip_amount(username) or 0
                        if paid <= 0:
                            return "Tip the bot first"
                    await self.bot.highrise.teleport(user_id, locpos)
                    return f"teleported to location {nm}"
        # Allow only specified commands by role
        public_cmds = ("!emotelist", "!emote", "!love", "!hate", "!buyvip", "!bal", "!balance", "!help", "!userinfo", "!poke", "!hug", "!modlist", "!ownerlist", "!cozynap", "!ghostfloat", "!lb", "!dance")
        owner_cmds = ("!addmod", "!demod", "!addvip", "!devip", "!rmvip", "!wallet", "!tip ", "!tipall ", "!setbot", "!cdress", "!cdrees", "!wlc ", "!setvip", "!set ", "!rloch ", "!ban ", "!unban ", "!summon ", "!h ", "!hall", "!freeze ", "!unfreeze ", "!flash", "!addowner", "!rmowner", "!addaowner", "!inviteall", "!loop", "!tele", "!s")
        if low.startswith("!stopbot") or low.startswith("!lockbot"):
            if username and username.strip().lower() == "ANTAURI":
                self.bot.paused = True
                self.bot.lock_user = "ANTAURI"
                self.bot.lock_user_id = user_id
                try:
                    if getattr(self.bot, "_dance_task", None) and not self.bot._dance_task.done():
                        self.bot._dance_task.cancel()
                        try:
                            await self.bot._dance_task
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    loops = list(getattr(self.bot, "_user_loops", {}).values())
                    for t in loops:
                        if t and not t.done():
                            t.cancel()
                            try:
                                await t
                            except Exception:
                                pass
                    try:
                        self.bot._user_loops.clear()
                    except Exception:
                        pass
                except Exception:
                    pass
                for tname in ("_follow_task", "_flash_task", "_announce_task"):
                    try:
                        t = getattr(self.bot, tname, None)
                        if t and not t.done():
                            t.cancel()
                            try:
                                await t
                            except Exception:
                                pass
                    except Exception:
                        pass
                try:
                    for uid, t in list(getattr(self.bot, "_dm_reminder_tasks", {}).items()):
                        if t and not t.done():
                            t.cancel()
                    try:
                        self.bot._dm_reminder_tasks.clear()
                    except Exception:
                        pass
                except Exception:
                    pass
                return "تم الإيقاف بنجاح"
            return None
        if low.startswith("!startbot") or low.startswith("!unlockbot"):
            if (username and username.strip().lower() == "ANTAURI") or (self.bot.lock_user_id and user_id == self.bot.lock_user_id):
                self.bot.paused = False
                self.bot.lock_user = None
                self.bot.lock_user_id = None
                return "تم التشغيل بنجاح"
            return None
        mod_cmds = ("!wallet", "!setbot", "!addvip ", "!tele ", "!kick ", "!ban ", "!mute ", "!unmute ", "!hall", "!h ", "!freeze ", "!unfreeze ", "!summon ", "!switch ", "!follow", "!sfollow", "!unfollow", "!loop", "!inviteall", "!viplist")
        vip_cmds = ("!summon ", "!tele ", "!hall", "!buyvip")
        def _matches(cmds: tuple[str, ...]):
            return any(low.startswith(p) for p in cmds)
        def _is_emote_alias(cmd: str) -> bool:
            if not cmd.startswith("!"):
                return False
            name = cmd[1:].split()[0].strip().lower()
            if not name:
                return False
            try:
                from emotes import ALL_EMOTE_LIST
                return any(lbl.lower() == name for lbl, _ in ALL_EMOTE_LIST)
            except Exception:
                return False
        def _is_emote_alias_all(cmd: str) -> bool:
            if not cmd.startswith("!"):
                return False
            name = cmd[1:].split()[0].strip().lower()
            if not name.endswith("all"):
                return False
            base = name[:-3].strip()
            if not base:
                return False
            try:
                from emotes import ALL_EMOTE_LIST
                return any(lbl.lower() == base for lbl, _ in ALL_EMOTE_LIST)
            except Exception:
                return False
        if is_owner or is_dev:
            allowed = _matches(public_cmds) or _matches(owner_cmds) or _matches(mod_cmds) or _is_emote_alias(command) or self._is_emote_alias_plain(command) or _is_emote_alias_all(command)
        elif is_mod:
            allowed = _matches(public_cmds) or _matches(mod_cmds) or _is_emote_alias(command) or self._is_emote_alias_plain(command) or _is_emote_alias_all(command)
        elif is_vip:
            allowed = _matches(public_cmds) or _matches(vip_cmds) or _is_emote_alias(command) or self._is_emote_alias_plain(command)
        else:
            allowed = _matches(public_cmds) or _is_emote_alias(command) or self._is_emote_alias_plain(command)
        if not allowed:
            return None

        if self.bot.paused:
            if not (username and username.strip().lower() == "ANTAURI"):
                return None
        if low == "stop" or low == "!stop":
            try:
                await self.bot.stop_user_loop(user_id)
                return None
            except Exception:
                return None

        if low.startswith("!wallet") or low.startswith("!محفظة"):
            return await self._wallet()
        if low.startswith("!set "):
            return await self._set_location(command, user_id)
        if low.startswith("!move ") or low.startswith("!حرك "):
            return await self._move(command)
        if low.startswith("!goto ") or low.startswith("!go "):
            return await self._goto(command)
        if low.startswith("!mute ") or low.startswith("!ميوت "):
            return await self._mute(command)
        if low.startswith("!unmute ") or low.startswith("!فك_الميوت ") or low.startswith("!فك الميوت "):
            return await self._unmute(command)
        if low.startswith("!ban ") or low.startswith("!حظر "):
            return await self._ban(command)
        if low.startswith("!unban ") or low.startswith("!فك_الحظر "):
            return await self._unban(command)
        if low.startswith("!kick ") or low.startswith("!طرد "):
            return await self._kick(command)
        if low.startswith("!emote "):
            if "@" in command:
                return await self._emote_target(command, user_id)
            return await self._emote_self(command, user_id)
        if low.startswith("!relaxed"):
            return await self._emote_label("Relaxed", user_id)
        if low.startswith("!attentive"):
            return await self._emote_label("Attentive", user_id)
        if low.startswith("!sleepy"):
            return await self._emote_label("Sleepy", user_id)
        if low.startswith("!loop "):
            return await self._loop(command, user_id, username)
        if low.startswith("!inviteall"):
            return await self._inviteall(user_id, username)
        if low.startswith("!cozynap"):
            return await self._emote_label("Cozy Nap", user_id)
        if low.startswith("!ghostfloat"):
            return await self._emote_label("Ghost Float", user_id)
        if low.startswith("!dance"):
            return await self._dance(command)
        if low.startswith("!emote loop"):
            return await self._emote_loop(command)
        if low.startswith("!buyvip"):
            return await self._buyvip(command, username)
        if low.startswith("!emotelist"):
            return await self._emotelist(user_id)
        if low.startswith("!modlist"):
            return await self._modlist(user_id)
        if low.startswith("!ownerlist"):
            return await self._ownerlist(user_id)
        if low.startswith("!lb"):
            return await self._lb(user_id)
        if low.startswith("!userinfo"):
            return await self._userinfo(command, user_id)
        if low.startswith("!bal") or low.startswith("!balance") or low.startswith("!blance"):
            return await self._bal(user_id)
        if low.startswith("!help"):
            return await self._help(user_id, is_owner, is_mod, is_vip)
        if low.startswith("!love"):
            return await self._love(command)
        if low.startswith("!hate"):
            return await self._hate(command)
        if low.startswith("!addmod "):
            return await self._addmod(command)
        if low.startswith("!demod "):
            return await self._demod(command)
        if low.startswith("!setbot"):
            return await self._setbot(user_id)
        if low.startswith("!cdress") or low.startswith("!cdrees"):
            return await self._cdress(command)
        if low.startswith("!wlc "):
            return await self._wlc(command)
        if low.startswith("!setvip "):
            return await self._setvip_from_location(command)
        if low == "!setvip":
            return await self._setvip_here(user_id)
        if low.startswith("!tip "):
            return await self._tip(command, user_id)
        if low.startswith("!tipall") or low.startswith("!tip all"):
            return await self._tipall(command)
        if low.startswith("!greet ") or low.startswith("!ترحيب "):
            return await self._greet(command)
        if low.startswith("!swap ") or low.startswith("!بدل "):
            return await self._swap(command)
        if low.startswith("!switch "):
            return await self._swap(command)
        if low.startswith("!rloch "):
            return await self._rloc(command)
        if low.startswith("!summon "):
            return await self._summon(command, user_id)
        if low.startswith("!tele "):
            return await self._tele(command, user_id, is_vip=is_vip, is_privileged=(is_owner or is_dev or is_mod))
        if low.startswith("!flash"):
            return await self._flash(user_id, command)
        if low.startswith("!s"):
            return await self._spam(user_id, command)
        if low == "!hug" or low.startswith("!hug ") or low.startswith("!عناق "):
            return await self._hug(command, user_id)
        if low == "!poke" or low.startswith("!poke ") or low.startswith("!لمس "):
            return await self._poke(command, user_id)
        if low.startswith("!h "):
            return await self._heart(command, is_mod=is_mod, is_owner_or_dev=(is_owner or is_dev))
        if low.startswith("!hall"):
            return await self._heart_all()
        if low.startswith("!freeze"):
            return await self._freeze(command)
        if low.startswith("!unfreeze"):
            return await self._unfreeze(command)
        # dynamic emote alias: !<label> [@username]
        if command.startswith("!") and self._is_emote_alias_safe(command):
            return await self._handle_emote_alias(command, user_id)
        # dynamic emote all: !<label>all
        if command.startswith("!") and _is_emote_alias_all(command):
            if not (is_owner or is_dev or is_mod):
                return "Unauthorized"
            return await self._handle_emote_all(command)
        # dynamic emote alias (plain): <label> [@username]
        if not command.startswith("!") and self._is_emote_alias_plain(command):
            return await self._handle_emote_alias_plain(command, user_id)
        if not command.startswith("!"):
            nm = command.strip().lower()
            if nm:
                if nm == "vip":
                    if not (is_owner or is_dev or is_mod or is_vip):
                        paid = 0
                        if username:
                            paid = self.bot.get_user_tip_amount(username) or 0
                        if paid <= 0:
                            return "Tip the bot first"
                    pos = self.bot.storage.load_vip_position()
                    if not pos:
                        return "Location not found"
                    await self.bot.highrise.teleport(user_id, pos)
                    return "teleported to location vip"
                locpos = self.bot.storage.get_location(nm)
                if locpos:
                    if not (is_owner or is_dev or is_mod or is_vip):
                        paid = 0
                        if username:
                            paid = self.bot.get_user_tip_amount(username) or 0
                        if paid <= 0:
                            return "Tip the bot first"
                    await self.bot.highrise.teleport(user_id, locpos)
                    return f"teleported to location {nm}"
        if low.startswith("!follow"):
            return await self._follow(user_id, command)
        if low.startswith("!sfollow"):
            return await self._unfollow()
        if low.startswith("!unfollow"):
            return await self._unfollow()
        if low.startswith("!addowner ") or low.startswith("!addaowner "):
            return await self._addowner(command)
        if low.startswith("!rmowner "):
            return await self._rmowner(command)
        if low.startswith("!addvip "):
            return await self._addvip(command)
        if low.startswith("!viplist"):
            return await self._viplist()
        if low.startswith("!viploc"):
            return await self._viploc(command, user_id)
        if low.startswith("!vip"):
            return await self._vip(user_id, username)
        if low.startswith("!rmvip "):
            return await self._rmvip(command)
        return None

    def _is_emote_alias_safe(self, command: str) -> bool:
        if not command.startswith("!"):
            return False
        name = command[1:].split()[0].strip().lower()
        if not name:
            return False
        reserved = ("addmod","demod","addvip","devip","rmvip","wallet","tip","tipall","setbot","cdress","cdrees","wlc","setvip","set","rloc","rloch","ban","unban","summon","h","hall","freeze","unfreeze","flash","stopflash","tele","kick","mute","unmute","switch","follow","sfollow","unfollow","emotelist","emote","loop","goto","love","hate","buyvip","modlist","bal","balance","help","inviteall","addowner","rmowner","addaowner","stopbot","startbot","lockbot","unlockbot","s")
        if name in reserved:
            return False
        try:
            from emotes import ALL_EMOTE_LIST
            return any(lbl.lower() == name for lbl, _ in ALL_EMOTE_LIST)
        except Exception:
            return False
    def _is_emote_alias_plain(self, command: str) -> bool:
        if command.startswith("!"):
            return False
        name = command.split()[0].strip().lower()
        if not name:
            return False
        reserved = ("addmod","demod","addvip","devip","rmvip","wallet","tip","tipall","setbot","cdress","cdrees","wlc","setvip","set","rloc","rloch","ban","unban","summon","h","hall","freeze","unfreeze","flash","stopflash","tele","kick","mute","unmute","switch","follow","sfollow","unfollow","emotelist","emote","loop","goto","love","hate","buyvip","modlist","bal","balance","help","inviteall","addowner","rmowner","addaowner","stopbot","startbot","stop","s")
        if name in reserved:
            return False
        try:
            from emotes import ALL_EMOTE_LIST
            return any(lbl.lower() == name for lbl, _ in ALL_EMOTE_LIST)
        except Exception:
            return False

    async def _handle_emote_alias(self, command: str, actor_id: str):
        parts = command.split()
        if not parts:
            return None
        label = parts[0][1:].strip()
        target_id = actor_id
        if len(parts) >= 2 and parts[1].startswith("@"):
            uname = parts[1].replace("@", "").strip()
            uid = await self.bot.resolve_user_id(uname)
            if not uid:
                return "User not found"
            target_id = uid
        from emotes import ALL_EMOTE_LIST
        for l, code in ALL_EMOTE_LIST:
            if l.lower() == label.lower():
                try:
                    await self.bot.highrise.send_emote(code, target_id)
                    try:
                        msg = f"{l} running. Type stop to end"
                        await self.bot.highrise.send_whisper(actor_id, msg)
                    except Exception:
                        pass
                    return None
                except Exception:
                    return "Failed to emote"
        return "Emote not found"
    async def _handle_emote_alias_plain(self, command: str, actor_id: str):
        parts = command.split()
        if not parts:
            return None
        label = parts[0].strip()
        target_id = actor_id
        if len(parts) >= 2 and parts[1].startswith("@"):
            uname = parts[1].replace("@", "").strip()
            uid = await self.bot.resolve_user_id(uname)
            if not uid:
                return "User not found"
            target_id = uid
        from emotes import ALL_EMOTE_LIST
        for l, code in ALL_EMOTE_LIST:
            if l.lower() == label.lower():
                try:
                    await self.bot.highrise.send_emote(code, target_id)
                    try:
                        msg = f"{l} running. Type stop to end"
                        await self.bot.highrise.send_whisper(actor_id, msg)
                    except Exception:
                        pass
                    return None
                except Exception:
                    return "Failed to emote"
        return "Emote not found"
    async def _handle_emote_all(self, command: str):
        parts = command.split()
        if not parts:
            return None
        raw = parts[0][1:].strip().lower()
        base = raw[:-3]
        from emotes import ALL_EMOTE_LIST
        code = None
        for l, c in ALL_EMOTE_LIST:
            if l.lower() == base:
                code = c
                break
        if not code:
            return "Emote not found"
        try:
            room_users = await self.bot.highrise.get_room_users()
        except Exception:
            return "Failed to get users"
        sent = 0
        for ru, _ in room_users.content:
            if ru.id == self.bot.bot_id:
                continue
            try:
                await self.bot.highrise.send_emote(code, ru.id)
                sent += 1
                await asyncio.sleep(0.1)
            except Exception:
                pass
        return f"sent {base} to {sent} users"

    async def _emotelist(self, user_id: str):
        try:
            from emotes import ALL_EMOTE_LIST
            lines = []
            for i, (name, _) in enumerate(ALL_EMOTE_LIST, start=1):
                lines.append(f"{i}. {name}")
            msg = "Emotes:\n" + "\n".join(lines)
            chunks = self._make_chunks(msg)
            for ch in chunks:
                try:
                    await self.bot.highrise.send_whisper(user_id, ch)
                except Exception:
                    pass
                await asyncio.sleep(0.3)
            return None
        except Exception:
            return "Failed to list emotes"



    async def _help(self, user_id: str, is_owner: bool, is_mod: bool, is_vip: bool):
        try:
            chunks = []
            # User Commands
            msg = (
                "User Commands:\n"
                "!bal / !balance - Check balance\n"
                "!emotelist - List emotes\n"
                "!cozynap / !ghostfloat - Special emotes\n"
                "!buyvip 1week 300 - Buy VIP\n"
                "!love/hate @user - React\n"
                "!hug/poke @user - Interaction\n"
                "!userinfo @user - User stats\n"
                "!modlist - Online mods\n"
                "!help - Show this menu"
            )
            chunks.extend(self._make_chunks(msg))
            
            # Mod/Owner Commands
            if is_mod or is_owner:
                msg = (
                    "Mod Commands:\n"
                    "!mute/unmute @user\n"
                    "!ban/unban @user\n"
                    "!kick @user\n"
                    "!loop @user <emote> | stop\n"
                    "!viplist | !inviteall\n"
                    "!tele @user | !summon @user\n"
                    "!freeze/unfreeze @user\n"
                    "!follow/sfollow @user"
                )
                chunks.extend(self._make_chunks(msg))
            
            if is_owner:
                msg = (
                    "Owner Commands:\n"
                    "!addmod/demod @user\n"
                    "!addvip/rmvip @user\n"
                    "!addowner/rmowner @user\n"
                    "!wallet | !tip @user | !tipall\n"
                    "!setbot | !wlc <text>\n"
                    "!set <loc> | !rloc | !setvip\n"
                    "!cdress | !flash"
                )
                chunks.extend(self._make_chunks(msg))

            # New Features
            msg = (
                "New:\n"
                "- Hourly 'Code by RAKA TEAM'\n"
                "- DM 'hello' to unlock cmds\n"
                "- !loop @user stop\n"
                "- !addowner / !rmowner"
            )
            chunks.extend(self._make_chunks(msg))
            # send via whisper regardless of input channel
            for ch in chunks:
                try:
                    await self.bot.highrise.send_whisper(user_id, ch)
                except Exception:
                    pass
                await asyncio.sleep(0.3)
            return None
        except Exception:
            return "Failed"

    async def _inviteall(self, user_id: str, username: str):
        is_owner = (user_id == self.bot.owner_id) or (username == "ANTAURI") or (username and self.bot.storage.is_owner(username))
        is_mod = bool(username and self.bot.storage.is_moderator(username))
        if not (is_owner or is_mod):
            return "Unauthorized"
        return await self._invite()

    async def _lang(self, command: str):
        try:
            parts = command.split()
            if len(parts) < 2:
                return "Usage: !lang ar|en|both"
            val = parts[1].lower()
            if val not in ("ar", "en", "both"):
                return "Usage: !lang ar|en|both"
            self.bot.language = val
            if val == "ar":
                return "تم تعيين اللغة: العربية"
            if val == "en":
                return "Language set: English"
            return "Language set: both"
        except Exception:
            return "Failed to set language"

    async def _tip(self, command: str, actor_id: str):
        try:
            if actor_id != self.bot.owner_id:
                return "Unauthorized"
            parts = command.split()
            if len(parts) < 3:
                return "Usage: !tip @username amount"
            target = parts[1].strip()
            amount_s = parts[2].strip()
            try:
                amount = int(float(amount_s))
            except Exception:
                return "Invalid amount"
            if amount <= 0:
                return "Invalid amount"
            bot_wallet = await self.bot.highrise.get_wallet()
            try:
                bot_amount = bot_wallet.content[0].amount
            except Exception:
                bot_amount = 0
                for currency in bot_wallet.content:
                    if getattr(currency, "type", "") == "gold":
                        bot_amount = getattr(currency, "amount", 0) or 0
                        break
            bars_dictionary = {
                10000: "gold_bar_10k",
                5000: "gold_bar_5000",
                1000: "gold_bar_1k",
                500: "gold_bar_500",
                100: "gold_bar_100",
                50: "gold_bar_50",
                10: "gold_bar_10",
                5: "gold_bar_5",
                1: "gold_bar_1",
            }
            tip_list = []
            remaining = amount
            for bar in sorted(bars_dictionary.keys(), reverse=True):
                if remaining >= bar:
                    count = remaining // bar
                    remaining = remaining % bar
                    for _ in range(count):
                        tip_list.append(bars_dictionary[bar])
            if not tip_list:
                return "Invalid amount"
            tip_string = ",".join(tip_list)
            client = self.bot.highrise
            async def tip_one(uid: str):
                if hasattr(client, "tip_user"):
                    await client.tip_user(uid, tip_string)
                    return True
                return False
            uname = target.replace("@", "")
            uid = await self.bot.resolve_user_id(uname)
            if not uid:
                return "User not found"
            if bot_amount <= amount:
                return "Not enough funds"
            ok = await tip_one(uid)
            if not ok:
                return "Tipping not supported"
            return f"tipped {uname} {amount}g"
        except Exception:
            return "Failed to tip"

    async def _wallet(self):
        wallet = await self.bot.highrise.get_wallet()
        for currency in wallet.content:
            if currency.type == "gold":
                return f"I have {currency.amount}g in my wallet."
        return "No gold in wallet."

    def _top(self):
        tippers = self.bot.get_top_tippers()
        lines = []
        for i, (_, user) in enumerate(tippers):
            lines.append(f"{i + 1}. {user['username']} ({user['total_tips']}g)")
        return "Top Tippers:\n" + "\n".join(lines) if lines else "No tips yet."

    def _get(self, command: str):
        username = command.split(" ", 1)[1].replace("@", "")
        amt = self.bot.get_user_tip_amount(username)
        if amt is not None:
            return f"{username} has tipped {amt}g"
        return f"{username} hasn't tipped."

    async def _move(self, command: str):
        try:
            _, args = command.split(" ", 1)
            parts = args.split()
            x = float(parts[0])
            y = float(parts[1])
            z = float(parts[2])
            facing = parts[3] if len(parts) > 3 else getattr(self.bot, "_default_facing", "FrontRight")
            pos = self.bot.Position(x, y, z, facing)
            await self.bot.highrise.teleport(self.bot.bot_id, pos)
            return "Moved."
        except Exception:
            return "Usage: !move x y z facing"

    async def _say(self, command: str):
        text = command.split(" ", 1)[1]
        try:
            await self.bot.highrise.chat(text)
            return None
        except Exception:
            return "Failed to chat."

    async def _roll(self):
        n = random.randint(1, 6)
        if self.bot.language == "ar":
            return f"نرد: {n}"
        return f"Roll: {n}"

    async def _coin(self):
        val = random.choice(["Heads", "Tails"])
        if self.bot.language == "ar":
            ar = "ملك" if val == "Heads" else "كتابه"
            return f"عملة: {ar}"
        return f"Coin: {val}"

    # rps command removed per request

    async def _sub(self, user_id: str, username: str | None):
        try:
            self.bot.storage.add_sub(user_id, username or "")
            if self.bot.language == "ar":
                return "تم الاشتراك"
            if self.bot.language == "en":
                return "Subscribed"
            return "Subscription successful"
        except Exception:
            return "Failed to subscribe"
    async def _numinvite(self):
        try:
            subs = self.bot.storage.get_subs()
            n = len(subs or [])
            if self.bot.language == "ar":
                return f"عدد المشتركين: {n}"
            return f"Subscribers: {n}"
        except Exception:
            return "Failed to count subscribers"

    def _stats(self):
        users = self.bot.storage.data.get("users", {})
        total = sum(u["total_tips"] for u in users.values())
        return f"tippers: {len(users)}, total: {total}g"

    async def _goto(self, command: str):
        try:
            parts = command.split()
            if len(parts) < 2:
                return "Usage: !go username"
            target = parts[1].replace("@", "").strip()
            uid = await self.bot.resolve_user_id(target)
            if not uid:
                return "User not found"
            return await self.bot.set_bot_position(uid)
        except Exception:
            return "Failed to go"

    async def _info(self, command: str):
        try:
            parts = command.split()
            if len(parts) < 2:
                owner_name = None
                try:
                    room_users = await self.bot.highrise.get_room_users()
                    for ru, _ in room_users.content:
                        if ru.id == self.bot.owner_id:
                            owner_name = ru.username
                            break
                except Exception:
                    owner_name = None
                rules = self.bot.storage.get_rules()
                owner_str = owner_name or str(self.bot.owner_id)
                return f"Room owner: {owner_str}\nRules: {rules if rules else '-'}"
            username = parts[1].replace("@", "").strip()
            if not username:
                owner_name = None
                try:
                    room_users = await self.bot.highrise.get_room_users()
                    for ru, _ in room_users.content:
                        if ru.id == self.bot.owner_id:
                            owner_name = ru.username
                            break
                except Exception:
                    owner_name = None
                rules = self.bot.storage.get_rules()
                owner_str = owner_name or str(self.bot.owner_id)
                return f"Room owner: {owner_str}\nRules: {rules if rules else '-'}"
            uid = await self.bot.resolve_user_id(username)
            if not uid:
                return "User not found"
            try:
                info = await self.bot.webapi.get_user(uid)
            except Exception as e:
                print(f"info_get_error: {e}")
                return "Failed to fetch info"
            u = getattr(info, "user", None)
            if not u:
                return "User not found"
            followers = getattr(u, "num_followers", 0) or 0
            friends = getattr(u, "num_friends", 0) or 0
            following = getattr(u, "num_following", 0) or 0
            joined_at = getattr(u, "joined_at", None)
            try:
                joined_str = joined_at.strftime("%d/%m/%Y %H:%M:%S") if joined_at else "-"
            except Exception:
                joined_str = str(joined_at) if joined_at else "-"
            last_attr = getattr(u, "last_online_in", None) or getattr(u, "last_online_at", None)
            try:
                last_login = last_attr.strftime("%d/%m/%Y %H:%M:%S") if last_attr else "Last login not available"
            except Exception:
                last_login = str(last_attr) if last_attr else "Last login not available"
            posts_res = await self.bot.webapi.get_posts(author_id=user_id)
            num_posts = 0
            most_likes = 0
            try:
                while True:
                    for p in getattr(posts_res, "posts", []) or []:
                        likes = getattr(p, "num_likes", 0) or 0
                        if likes > most_likes:
                            most_likes = likes
                        num_posts += 1
                    last_id = getattr(posts_res, "last_id", None)
                    if not last_id:
                        break
                    posts_res = await self.bot.webapi.get_posts(author_id=user_id, starts_after=last_id)
            except Exception:
                pass
            msg = (
                f"User: {username}\n"
                f"Number of followers: {followers}\n"
                f"Number of friends: {friends}\n"
                f"Number of following: {following}\n"
                f"Joined at: {joined_str}\n"
                f"Last login: {last_login}\n"
                f"Number of posts: {num_posts}\n"
                f"Most likes in a post: {most_likes}"
            )
            try:
                await self.bot.highrise.chat(msg)
                return None
            except Exception:
                return "Failed to send info"
        except Exception:
            return "Failed to fetch info"

    def _parse_duration(self, s: str) -> int:
        s = s.strip().lower()
        if not s:
            return 0
        unit = s[-1]
        num = float(s[:-1]) if unit in ["s", "m", "h", "d"] else float(s)
        if unit == "s":
            return int(num)
        if unit == "m":
            return int(num * 60)
        if unit == "h":
            return int(num * 3600)
        if unit == "d":
            return int(num * 86400)
        return int(num)

    async def _mute(self, command: str):
        try:
            _, rest = command.split(" ", 1)
            parts = rest.split()
            username = parts[0].replace("@", "")
            seconds = self._parse_duration(parts[1]) if len(parts) > 1 else 0
            uid = await self.bot.resolve_user_id(username)
            if not uid:
                return "User not found"
            self.bot.storage.mute_user(uid, seconds or 600)
            try:
                await self.bot.highrise.moderate_room(uid, "mute", seconds or 600)
            except Exception:
                pass
            return f"muted {username}"
        except Exception:
            return "Usage: !mute @username 10m"

    async def _unmute(self, command: str):
        try:
            parts = command.split()
            if len(parts) < 2:
                return "Usage: !unmute @username"
            idx = 1
            if parts[0] == "!فك" and len(parts) >= 3 and parts[1].startswith("الميوت"):
                idx = 2
            username = parts[idx].replace("@", "").strip()
            uid = await self.bot.resolve_user_id(username)
            if not uid:
                return "User not found"
            self.bot.storage.unmute_user(uid)
            return f"unmuted {username}"
        except Exception:
            return "Usage: !unmute @username"

    async def _ban(self, command: str):
        try:
            _, rest = command.split(" ", 1)
            parts = rest.split()
            username = parts[0].replace("@", "")
            seconds = self._parse_duration(parts[1]) if len(parts) > 1 else 0
            uid = await self.bot.resolve_user_id(username)
            if not uid:
                return "User not found"
            self.bot.storage.ban_user(uid, seconds or 3600)
            try:
                await self.bot.highrise.moderate_room(uid, "ban", seconds or 3600)
            except Exception:
                pass
            try:
                await self.bot.highrise.send_whisper(uid, "You are banned.")
            except Exception:
                pass
            return f"banned {username}"
        except Exception:
            return "Usage: !ban @username 1h"

    async def _unban(self, command: str):
        try:
            username = command.split(" ", 1)[1].replace("@", "").strip()
            uid = await self.bot.resolve_user_id(username)
            if not uid:
                return "User not found"
            self.bot.storage.unban_user(uid)
            return f"unbanned {username}"
        except Exception:
            return "Usage: !unban @username"

    async def _kick(self, command: str):
        try:
            username = command.split(" ", 1)[1].replace("@", "").strip()
            uid = await self.bot.resolve_user_id(username)
            if not uid:
                return "User not found"
            try:
                await self.bot.highrise.moderate_room(uid, "kick", 0)
            except Exception:
                pass
            try:
                await self.bot.highrise.send_whisper(uid, "You are requested to leave.")
            except Exception:
                pass
            return f"kicked {username}"
        except Exception:
            return "Usage: !kick @username"

    async def _dance(self, command: str):
        parts = command.split()
        emote = parts[1] if len(parts) > 1 else "dance-floss"
        return await self.bot.start_dance(emote)

    async def _rest(self, command: str):
        return await self.bot.start_dance("idle-loop-sitfloor")

    async def _ghost(self, command: str):
        return await self.bot.start_dance("emote-ghost-idle")

    async def _stopdance(self):
        return await self.bot.stop_dance()

    async def _emote(self, command: str):
        parts = command.split()
        if len(parts) < 2:
            return "Usage: !emote <n|name>"
        arg = parts[1]
        if arg.isdigit():
            await self.bot.emote_by_index(int(arg))
            return None
        name = arg
        from emotes import ALL_EMOTE_LIST
        for label, code in ALL_EMOTE_LIST:
            if label.lower() == name.lower() or code.lower() == name.lower():
                try:
                    await self.bot.highrise.send_emote(code)
                    return None
                except Exception:
                    return "Failed to emote"
        return "Emote not found"

    async def _emote_loop(self, command: str):
        try:
            parts = command.split()
            if len(parts) < 3:
                return "Usage: !emote loop n [seconds]"
            if parts[1].lower() != "loop":
                return "Usage: !emote loop n [seconds]"
            n = int(parts[2]) if parts[2].isdigit() else None
            secs = float(parts[3]) if len(parts) > 3 else None
            if not n:
                return "Usage: !emote loop n [seconds]"
            return await self.bot.start_loop(n, secs)
        except Exception:
            return "Failed to loop"

    async def _loop(self, command: str, user_id: str, username: str | None = None):
        parts = command.split()
        if len(parts) < 2:
            return "Usage: !loop n [seconds] | !loop @user emote"
        
        if parts[1].startswith("@"):
            # Check permissions
            is_owner = (user_id == self.bot.owner_id) or (username == "ANTAURI")
            is_mod = bool(username and self.bot.storage.is_moderator(username))
            if not (is_owner or is_mod):
                return "Unauthorized"
            
            target_name = parts[1].replace("@", "").strip()
            target_id = await self.bot.resolve_user_id(target_name)
            if not target_id:
                return "User not found"
            
            if len(parts) < 3:
                return "Usage: !loop @user emote | !loop @user stop"
            
            arg2 = parts[2].lower()
            if arg2 == "stop":
                await self.bot.stop_user_loop(target_id)
                return f"Loop stopped for {target_name}"
            
            from emotes import ALL_EMOTE_LIST
            emote_code = None
            for lbl, code in ALL_EMOTE_LIST:
                if lbl.lower() == arg2 or code == arg2:
                    emote_code = code
                    break
            if not emote_code:
                return "Emote not found"
            
            interval = None
            if len(parts) >= 4:
                interval = self.bot._parse_duration(parts[3])
            await self.bot.start_user_loop_code(target_id, emote_code, interval)
            return f"Looping {arg2} on {target_name}"

        # Actor self loop: support index or label
        arg1 = parts[1].lower()
        interval = None
        if len(parts) >= 3:
            interval = self.bot._parse_duration(parts[2])
        if arg1.isdigit():
            return await self.bot.start_user_loop(user_id, int(arg1), interval)
        # try label
        from emotes import ALL_EMOTE_LIST
        emote_code = None
        for lbl, code in ALL_EMOTE_LIST:
            if lbl.lower() == arg1 or code == arg1:
                emote_code = code
                break
        if not emote_code:
            return "Emote not found"
        await self.bot.start_user_loop_code(user_id, emote_code, interval)
        return f"Looping {arg1}"

    async def _greet(self, command: str):
        parts = command.split()
        if len(parts) < 2:
            return "Usage: !greet on|off|set <text>"
        val = parts[1].lower()
        if val == "on":
            self.bot.greet_enabled = True
            return "greet on" if self.bot.language != "ar" else "تم تشغيل الترحيب"
        if val == "off":
            self.bot.greet_enabled = False
            return "greet off" if self.bot.language != "ar" else "تم إيقاف الترحيب"
        if val == "set":
            text = command.split(parts[1], 1)[1].strip() if len(parts) > 2 else ""
            if not text:
                return "Usage: !greet set <text>" if self.bot.language != "ar" else "الاستخدام: !greet set <نص>"
            # set for current language; if both, set for both
            lang = getattr(self.bot, "language", "both")
            if lang == "both":
                self.bot.storage.set_greet_text("ar", text)
                self.bot.storage.set_greet_text("en", text)
            else:
                self.bot.storage.set_greet_text(lang, text)
            return "greet text updated" if self.bot.language != "ar" else "تم تحديث نص الترحيب"
        return "Usage: !greet on|off|set <text>" if self.bot.language != "ar" else "الاستخدام: !greet on|off|set <نص>"

    async def _adddev(self, command: str):
        username = command.split(" ", 1)[1].replace("@", "").strip()
        if not username:
            return "Usage: !adddev @username"
        self.bot.storage.add_developer(username)
        return "dev added"

    async def _rmdev(self, command: str):
        username = command.split(" ", 1)[1].replace("@", "").strip()
        if not username:
            return "Usage: !rmdev @username"
        self.bot.storage.remove_developer(username)
        return "dev removed"

    async def _swap(self, command: str):
        try:
            parts = command.split()
            if len(parts) < 3:
                return "Usage: !swap @user1 @user2"
            u1 = parts[1].replace("@", "").strip()
            u2 = parts[2].replace("@", "").strip()
            id1 = await self.bot.resolve_user_id(u1)
            id2 = await self.bot.resolve_user_id(u2)
            if not id1 or not id2:
                return "User not found"
            try:
                room_users = await self.bot.highrise.get_room_users()
                pos_map = {}
                for room_user, pos in room_users.content:
                    if hasattr(pos, "x"):
                        pos_map[room_user.id] = pos
                p1 = pos_map.get(id1)
                p2 = pos_map.get(id2)
                if not p1 or not p2:
                    return "Position not found"
                await self.bot.highrise.teleport(id1, p2)
                await self.bot.highrise.teleport(id2, p1)
                return "swapped"
            except Exception:
                return "Failed to swap"
        except Exception:
            return "Failed to swap"

    async def _follow(self, user_id: str, command: str):
        parts = command.split()
        target_id = user_id
        if len(parts) >= 2:
            uname = parts[1].replace("@", "").strip()
            if uname:
                uid = await self.bot.resolve_user_id(uname)
                if not uid:
                    return "User not found"
                target_id = uid
        return await self.bot.start_follow(target_id)

    async def _mutelist(self):
        try:
            mutes = self.bot.storage.data.get("mutes", {})
            if not mutes:
                return "No muted users."
            try:
                room_users = await self.bot.highrise.get_room_users()
                id2name = {ru.id: ru.username for ru, _ in room_users.content}
            except Exception:
                id2name = {}
            def fmt_secs(s: int):
                m = s // 60
                ss = s % 60
                h = m // 60
                mm = m % 60
                if h:
                    return f"{h}h {mm}m {ss}s"
                if m:
                    return f"{mm}m {ss}s"
                return f"{ss}s"
            now = int(asyncio.get_event_loop().time())
            lines = []
            for uid, until in mutes.items():
                rem = max(0, until - int(__import__("time").time()))
                name = id2name.get(uid)
                if not name:
                    users = self.bot.storage.data.get("users", {})
                    name = users.get(uid, {}).get("username", uid)
                lines.append(f"{name} ({fmt_secs(rem)})")
            return "Muted users:\n" + "\n".join(lines)
        except Exception:
            return "Failed to list mutes"

    async def _announce(self, command: str):
        try:
            parts = command.split()
            if len(parts) < 2:
                return "Usage: !announce start 10m <text> | !announce stop"
            if parts[1].lower() == "stop":
                return await self.bot.stop_announce()
            if parts[1].lower() == "start":
                if len(parts) < 4:
                    return "Usage: !announce start 10m <text>"
                interval = self._parse_duration(parts[2])
                if interval <= 0:
                    return "Invalid interval"
                text = command.split(parts[2], 1)[1].strip()
                return await self.bot.start_announce(float(interval), text)
            return "Usage: !announce start 10m <text> | !announce stop"
        except Exception:
            return "Failed to announce"

    def _status(self):
        try:
            return self.bot.get_status()
        except Exception:
            return "Failed to get status"

    async def _where(self, command: str, user_id: str | None = None):
        try:
            parts = command.split()
            if len(parts) < 2:
                uid = user_id
                if not uid:
                    return "Usage: !where @username"
                uname = None
            else:
                uname = parts[1].replace("@", "").strip()
                uid = await self.bot.resolve_user_id(uname)
            if not uid:
                return "User not found"
            pos = await self.bot._get_user_position(uid)
            if not pos:
                return "Position not found"
            who = uname if uname else "you"
            return f"{who}: x={pos.x:.2f}, y={pos.y:.2f}, z={pos.z:.2f}, facing={pos.facing}"
        except Exception:
            return "Failed to get position"

    async def _here(self):
        try:
            pos = await self.bot._get_bot_position()
            if not pos:
                return "Position not found"
            return f"here: x={pos.x:.2f}, y={pos.y:.2f}, z={pos.z:.2f}, facing={pos.facing}"
        except Exception:
            return "Failed to get position"

    async def _users(self, command: str):
        try:
            items = await self.bot.get_presence_durations()
            try:
                pc = command.split()
                n = int(pc[1]) if len(pc) > 1 and pc[1].isdigit() else 10
            except Exception:
                n = 10
            n = max(1, min(50, n))
            def fmt_secs(s: int):
                m = s // 60
                ss = s % 60
                h = m // 60
                mm = m % 60
                if h:
                    return f"{h}h {mm}m {ss}s"
                if m:
                    return f"{mm}m {ss}s"
                return f"{ss}s"
            lines = []
            for i, (name, dur) in enumerate(items[:n]):
                lines.append(f"{i+1}. {name} ({fmt_secs(dur)})")
            return "Top presence:\n" + ("\n".join(lines) if lines else "No users")
        except Exception:
            return "Failed to list users"

    async def _filter(self, command: str):
        try:
            parts = command.split()
            if len(parts) < 2:
                return "Usage: !filter on|off | !filter add <word> | !filter rm <word>"
            sub = parts[1].lower()
            if sub == "on":
                self.bot.storage.set_filter_enabled(True)
                return "filter enabled"
            if sub == "off":
                self.bot.storage.set_filter_enabled(False)
                return "filter disabled"
            if sub == "list":
                words = self.bot.storage.get_filter_words()
                return "filter words:\n" + ("\n".join(words) if words else "None")
            if sub == "add" and len(parts) >= 3:
                w = parts[2].lower()
                self.bot.storage.add_filter_word(w)
                return f"added {w}"
            if sub == "rm" and len(parts) >= 3:
                w = parts[2].lower()
                self.bot.storage.remove_filter_word(w)
                return f"removed {w}"
            return "Usage: !filter on|off | !filter add <word> | !filter rm <word>"
        except Exception:
            return "Failed to set filter"

    async def _warn(self, command: str):
        try:
            parts = command.split()
            if len(parts) < 2:
                return "Usage: !warn @username [reason]"
            uname = parts[1].replace("@", "").strip()
            uid = await self.bot.resolve_user_id(uname)
            if not uid:
                return "User not found"
            reason = command.split(parts[1], 1)[1].strip() if len(parts) > 2 else "warned"
            self.bot.storage.add_warn(uid, uname, reason)
            return f"warned {uname}"
        except Exception:
            return "Failed to warn"

    async def _warnlist(self, command: str):
        try:
            parts = command.split()
            if len(parts) < 2:
                return "Usage: !warnlist @username"
            uname = parts[1].replace("@", "").strip()
            uid = await self.bot.resolve_user_id(uname)
            if not uid:
                return "User not found"
            wl = self.bot.storage.get_warns(uid)
            if not wl:
                return f"no warns for {uname}"
            def fmt(ts: int):
                try:
                    import datetime
                    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    return str(ts)
            lines = []
            for i, w in enumerate(wl, 1):
                lines.append(f"{i}. {fmt(w.get('time', 0))} | {w.get('reason','')} | {w.get('word','')}")
            return "warns:\n" + "\n".join(lines)
        except Exception:
            return "Failed to list warns"

    async def _warnclear(self, command: str):
        try:
            parts = command.split()
            if len(parts) < 2:
                return "Usage: !warnclear @username"
            uname = parts[1].replace("@", "").strip()
            uid = await self.bot.resolve_user_id(uname)
            if not uid:
                return "User not found"
            self.bot.storage.clear_warns(uid)
            return f"warns cleared for {uname}"
        except Exception:
            return "Failed to clear warns"


    async def _rules(self, command: str):
        try:
            parts = command.split()
            if len(parts) < 2:
                return "Usage: !rules set <text> | !rules show"
            sub = parts[1].lower()
            if sub == "set":
                text = command.split(parts[1], 1)[1].strip() if len(parts) > 2 else ""
                self.bot.storage.set_rules(text)
                return "rules updated"
            if sub == "show":
                t = self.bot.storage.get_rules()
                return ("Rules:\n" + t) if t else "No rules"
            return "Usage: !rules set <text> | !rules show"
        except Exception:
            return "Failed to set rules"

    async def _anchor(self, command: str):
        try:
            parts = command.split()
            if len(parts) < 2:
                return "Usage: !anchor FrontRight|FrontLeft"
            facing = parts[1].strip()
            allowed = ["FrontRight", "FrontLeft", "BackRight", "BackLeft"]
            if facing not in allowed:
                return "Invalid facing"
            self.bot.set_anchor(facing)
            return f"anchor set: {facing}"
        except Exception:
            return "Failed to set anchor"

    async def _unfollow(self):
        return await self.bot.stop_follow()
    async def _addvip(self, command: str):
        try:
            parts = command.split()
            if len(parts) < 2:
                return "Usage: !addvip @username"
            uname = parts[1].replace("@", "").strip()
            if not uname:
                return "Usage: !addvip @username"
            self.bot.storage.add_vip(uname)
            return f"added vip: {uname}"
        except Exception:
            return "Failed to add vip"

    async def _viplist(self):
        try:
            vips = self.bot.storage.get_vips()
            return "VIPs:\n" + ("\n".join(vips) if vips else "None")
        except Exception:
            return "Failed to list vips"

    async def _modlist(self, user_id: str):
        try:
            mods = self.bot.storage.get_moderators()
            msg = "Moderators:\n" + ("\n".join(mods) if mods else "None")
            return self._make_chunks(msg)
        except Exception:
            return "Failed to list mods"

    async def _ownerlist(self, user_id: str):
        try:
            owners = self.bot.storage.get_owners()
            msg = "Owners:\n" + ("\n".join(owners) if owners else "None")
            return self._make_chunks(msg)
        except Exception:
            return "Failed to list owners"
    async def _lb(self, user_id: str):
        try:
            tops = self.bot.storage.get_top_chatters(20)
            lines = []
            for i, (_, uname, cnt) in enumerate(tops[:10], 1):
                lines.append(f"{i}. {uname}: {cnt} messages")
            msg = "Top chatters:\n" + ("\n".join(lines) if lines else "No data")
            return self._make_chunks(msg)
        except Exception:
            return "Failed to show leaderboard"
    async def _bal(self, user_id: str):
        try:
            amt = self.bot.storage.get_user_tip_amount_by_id(user_id)
            if getattr(self.bot, "language", "en") == "ar":
                return f"إجمالي الذهب الذي أرسلته للبوت: {amt}g"
            return f"Total gold tipped to bot: {amt}g"
        except Exception:
            return "Failed to get tipped amount"

    async def _viploc(self, command: str, user_id: str):
        try:
            parts = command.split()
            if len(parts) == 1 or (len(parts) == 2 and parts[1].lower() == "here"):
                pos = await self.bot._get_user_position(user_id)
                if not pos:
                    return "Position not found"
                self.bot.storage.set_vip_location(pos)
                return "vip location set"
            if len(parts) >= 4:
                x = float(parts[1]); y = float(parts[2]); z = float(parts[3])
                facing = parts[4] if len(parts) > 4 else getattr(self.bot, "_default_facing", "FrontRight")
                pos = self.bot.Position(x, y, z, facing)
                self.bot.storage.set_vip_location(pos)
                return "vip location set"
            return "Usage: !viploc [x y z facing|here]"
        except Exception:
            return "Failed to set vip location"

    async def _vip(self, user_id: str, username: str | None):
        try:
            if not username:
                return "Unauthorized"
            if not (self.bot.storage.is_developer(username) or self.bot.storage.is_vip(username)):
                return "Unauthorized"
            return await self.bot.teleport_user_to_vip(user_id)
        except Exception:
            return "Failed to vip"

    async def _invite(self):
        try:
            room_id = "654e13931e51b0781c97e30a"
            subs = self.bot.storage.get_subs()
            if not subs:
                if self.bot.language == "ar":
                    return "لا يوجد مشتركين"
                return "No subscribers"
            convs = None
            try:
                convs = await self.bot.highrise.get_conversations(False, None)
            except Exception:
                convs = None
            conv_map = {}
            if convs:
                for c in getattr(convs, "conversations", []) or []:
                    u = getattr(c, "user", None)
                    uid = getattr(u, "id", None) if u else getattr(c, "user_id", None)
                    cid = getattr(c, "id", None) or getattr(c, "conversation_id", None)
                    if uid and cid:
                        conv_map[uid] = cid
            sent = 0
            for s in subs:
                uid = s.get("id")
                cid = s.get("conversation_id") if "conversation_id" in s else conv_map.get(uid)
                if not cid:
                    continue
                try:
                    await self.bot.highrise.send_message(cid, "", "invite", room_id)
                    sent += 1
                except Exception:
                    pass
            if self.bot.language == "ar":
                return f"تم إرسال دعوة إلى {sent} مشترك"
            return f"Sent invite to {sent} subscribers"
        except Exception:
            return "Failed to invite"
    async def _rmvip(self, command: str):
        try:
            parts = command.split()
            if len(parts) < 2:
                return "Usage: !rmvip @username"
            uname = parts[1].replace("@", "").strip()
            self.bot.storage.remove_vip(uname)
            return f"removed vip: {uname}"
        except Exception:
            return "Failed to remove vip"

    async def _hug(self, command: str, actor_id: str | None = None):
        try:
            parts = command.split()
            targets = []
            if len(parts) >= 2:
                for tok in parts[1:]:
                    uname = tok.replace("@", "").strip()
                    if not uname:
                        continue
                    uid = await self.bot.resolve_user_id(uname)
                    if uid:
                        targets.append((uname, uid))
            if not targets:
                if actor_id:
                    try:
                        await self.bot.highrise.send_emote("emote-hug", actor_id)
                        return None
                    except Exception:
                        return "Failed to hug"
                return "User not found"
            ok_any = False
            for uname, uid in targets[:2]:
                try:
                    await self.bot.highrise.send_emote("emote-hug", uid)
                    ok_any = True
                except Exception:
                    pass
            if ok_any:
                return None
            return "Failed to hug"
        except Exception:
            return "Failed to hug"

    async def _poke(self, command: str, actor_id: str | None = None):
        try:
            parts = command.split()
            if len(parts) < 2:
                if actor_id:
                    try:
                        await self.bot.highrise.send_emote("emoji-there", actor_id)
                        return None
                    except Exception:
                        return "Failed to poke"
                return "Failed to poke"
            uname = parts[1].replace("@", "").strip()
            uid = await self.bot.resolve_user_id(uname)
            if not uid:
                return "User not found"
            try:
                await self.bot.highrise.send_emote("emoji-there", uid)
                return None
            except Exception:
                return "Failed to poke"
        except Exception:
            return "Failed to poke"

    # wave command removed per request

    async def _userinfo(self, command: str, actor_id: str | None = None):
        try:
            parts = command.split()
            if len(parts) < 2:
                uname = None
            else:
                uname = parts[1].replace("@", "").strip()
            import json
            import urllib.request
            u = {}
            if uname:
                def _f():
                    url = f"https://webapi.highrise.game/users/{uname}"
                    with urllib.request.urlopen(url) as r:
                        return json.loads(r.read().decode("utf-8"))
                data = await asyncio.to_thread(_f)
                u = data.get("user") or {}
            elif actor_id and getattr(self.bot, "webapi", None):
                info = await self.bot.webapi.get_user(actor_id)
                usr = getattr(info, "user", None)
                u = {
                    "username": getattr(usr, "username", "-"),
                    "num_followers": getattr(usr, "num_followers", 0) or 0,
                    "num_friends": getattr(usr, "num_friends", 0) or 0,
                    "num_following": getattr(usr, "num_following", 0) or 0,
                    "joined_at": getattr(usr, "joined_at", None),
                    "last_online_at": getattr(usr, "last_online_at", None) or getattr(usr, "last_online_in", None),
                }
            else:
                u = {"username": uname or "-", "num_followers": 0, "num_friends": 0, "num_following": 0}
            uname = u.get("username", uname or "-") or (uname or "-")
            followers = u.get("num_followers", 0) or 0
            friends = u.get("num_friends", 0) or 0
            following = u.get("num_following", 0) or 0
            joined_at = u.get("joined_at")
            last = u.get("last_online_at") or u.get("last_online_in")
            uid = await self.bot.resolve_user_id(uname)
            online = False
            try:
                online = bool(uid and uid in self.bot._presence)
                if not online:
                    ru = await self.bot.highrise.get_room_users()
                    for room_user, _ in getattr(ru, "content", []) or []:
                        if uid and room_user.id == uid:
                            online = True
                            break
            except Exception:
                pass
            tips_amt = self.bot.get_user_tip_amount(uname) or 0
            is_vip = self.bot.storage.is_vip(uname)
            is_dev = self.bot.storage.is_developer(uname)
            if self.bot.language == "ar":
                msg = (
                    f"المستخدم: {uname}\n"
                    f"اونلاين: {'نعم' if online else 'لا'}\n"
                    f"متابعون: {followers}\n"
                    f"اصدقاء: {friends}\n"
                    f"متابع: {following}\n"
                    f"انضم: {joined_at or '-'}\n"
                    f"آخر ظهور: {last or '-'}\n"
                    f"اجمالي الاكراميات: {tips_amt}g\n"
                    f"VIP: {'نعم' if is_vip else 'لا'} | Dev: {'نعم' if is_dev else 'لا'}"
                )
            else:
                msg = (
                    f"User: {uname}\n"
                    f"Online: {'yes' if online else 'no'}\n"
                    f"Followers: {followers}\n"
                    f"Friends: {friends}\n"
                    f"Following: {following}\n"
                    f"Joined: {joined_at or '-'}\n"
                    f"Last login: {last or '-'}\n"
                    f"Total tips: {tips_amt}g\n"
                    f"VIP: {'yes' if is_vip else 'no'} | Dev: {'yes' if is_dev else 'no'}"
                )
            try:
                await self.bot.highrise.chat(msg)
                return None
            except Exception:
                return "Failed to send user info"
        except Exception:
            return "Failed to fetch user info"

    async def _setbot(self, actor_id: str):
        return await self.bot.set_bot_position(actor_id)

    async def _cdress(self, command: str):
        parts = command.split()
        target = parts[1].strip() if len(parts) > 1 else ""
        try:
            # owner-only safety
            # routing layer already restricts, but double-check if needed elsewhere
            # Clone outfit from @username or apply preset fallback
            if target.startswith("@"):
                uname = target.replace("@", "").strip()
                # Try room resolve first
                uid = await self.bot.resolve_user_id(uname)
                if not uid:
                    # Try web API to resolve user id by username
                    try:
                        import json, urllib.request
                        url = f"https://webapi.highrise.game/users/{uname}"
                        data = json.loads(urllib.request.urlopen(url).read().decode("utf-8"))
                        u = data.get("user") or {}
                        uid = u.get("id") or u.get("user_id")
                    except Exception:
                        uid = None
                if not uid:
                    return "User not found"
                # Fetch outfit for user id
                outfit_resp = None
                try:
                    if hasattr(self.bot.highrise, "get_user_outfit"):
                        outfit_resp = await self.bot.highrise.get_user_outfit(uid)
                    elif hasattr(self.bot.highrise, "get_outfit"):
                        outfit_resp = await self.bot.highrise.get_outfit(uid)
                except Exception:
                    outfit_resp = None
                items = []
                try:
                    from highrise import Item
                    if outfit_resp and hasattr(outfit_resp, "outfit"):
                        # Some SDKs allow passing outfit_resp.outfit directly
                        try:
                            await self.bot.highrise.set_outfit(outfit=outfit_resp.outfit)
                            return f"Outfit applied from {uname}"
                        except Exception:
                            # Fallback: rebuild items list from IDs
                            ids = [getattr(it, "id", "") for it in outfit_resp.outfit]
                            items = [Item(type="clothing", amount=1, id=i, account_bound=False, active_palette=-1) for i in ids if i]
                    if not items:
                        # Fallback body + empty
                        items = [Item(type="clothing", amount=1, id="body-flesh", account_bound=False, active_palette=27)]
                    # Ensure body present
                    has_body = any(getattr(it, "id", "") == "body-flesh" for it in items)
                    if not has_body:
                        items = [Item(type="clothing", amount=1, id="body-flesh", account_bound=False, active_palette=27)] + items
                    req = {"body", "eye", "eyebrow", "nose", "mouth", "upper", "lower"}
                    present = set()
                    for it in items:
                        cid = getattr(it, "id", "")
                        cat = cid.split("-", 1)[0] if cid else ""
                        if cat in ("eye", "eyebrow", "nose", "mouth", "body"):
                            present.add(cat)
                        elif cat in ("shirt", "top", "hoodie", "coat", "jacket", "sweater", "upper"):
                            present.add("upper")
                        elif cat in ("shorts", "pants", "trousers", "jeans", "skirt", "leggings", "lower"):
                            present.add("lower")
                    missing = req - present
                    if "eye" in missing:
                        items.append(Item(type="clothing", amount=1, id="eye-n_basic2018malesquaresleepy", account_bound=False, active_palette=7))
                    if "eyebrow" in missing:
                        items.append(Item(type="clothing", amount=1, id="eyebrow-n_basic2018newbrows07", account_bound=False, active_palette=0))
                    if "nose" in missing:
                        items.append(Item(type="clothing", amount=1, id="nose-n_basic2018newnose05", account_bound=False, active_palette=0))
                    if "mouth" in missing:
                        items.append(Item(type="clothing", amount=1, id="mouth-basic2018chippermouth", account_bound=False, active_palette=-1))
                    if "upper" in missing:
                        items.append(Item(type="clothing", amount=1, id="shirt-n_starteritems2019tankblack", account_bound=False, active_palette=-1))
                    if "lower" in missing:
                        items.append(Item(type="clothing", amount=1, id="shorts-n_starteritems2019longshortsblack", account_bound=False, active_palette=-1))
                    await self.bot.highrise.set_outfit(outfit=items)
                    return f"Outfit applied from {uname}"
                except Exception:
                    return "Failed to apply outfit"
            # preset fallback
            preset = target.lower() if target else "black"
            if preset == "black":
                from highrise import Item
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
                await self.bot.highrise.set_outfit(outfit=items)
                return "Outfit applied"
            return "Unknown preset"
        except Exception:
            return "Failed to change outfit"

    async def _wlc(self, command: str):
        parts = command.split()
        if len(parts) < 2:
            return "Usage: !wlc <text>"
        text = command.split(" ", 1)[1].strip()
        self.bot.storage.set_greet_text("en", text)
        self.bot.greet_enabled = True
        self.bot.storage.set_greet_whisper(True)
        return "welcome whisper set"

    async def _setvip_from_location(self, command: str):
        try:
            parts = command.split()
            if len(parts) < 2:
                return "Usage: !setvip <location>"
            locname = parts[1].strip()
            pos = self.bot.storage.get_location(locname)
            if not pos:
                return "Location not found"
            self.bot.storage.set_vip_location(pos)
            try:
                self.bot.storage.set_location("vip", pos)
            except Exception:
                pass
            return "vip location set"
        except Exception:
            return "Failed to set vip location"

    async def _setvip_here(self, actor_id: str):
        try:
            pos = await self.bot._get_user_position(actor_id)
            if not pos:
                return "Position not found"
            self.bot.storage.set_vip_location(pos)
            try:
                self.bot.storage.set_location("vip", pos)
            except Exception:
                pass
            return "vip location set"
        except Exception:
            return "Failed to set vip location"
    async def _set_location(self, command: str, actor_id: str):
        parts = command.split()
        if len(parts) < 2:
            return "Usage: !set <location>"
        name = parts[1].strip().lower()
        pos = await self.bot._get_user_position(actor_id)
        if not pos:
            return "Position not found"
        self.bot.storage.set_location(name, pos)
        return f"saved location {name}"

    async def _rloc(self, command: str):
        parts = command.split()
        if len(parts) < 2:
            return "Usage: !rloch <location>"
        name = parts[1].strip().lower()
        self.bot.storage.remove_location(name)
        return f"removed location {name}"

    async def _tele(self, command: str, actor_id: str, is_vip: bool = False, is_privileged: bool = False):
        try:
            parts = command.split()
            if len(parts) == 2:
                arg = parts[1].strip()
                uname = arg.replace("@", "")
                uid = await self.bot.resolve_user_id(uname)
                if uid:
                    pos = await self.bot._get_user_position(uid)
                    if not pos:
                        return "Position not found"
                    await self.bot.highrise.teleport(actor_id, pos)
                    return f"teleported to {uname}"
                # fallback: treat as saved location
                key = arg.lower()
                if key == "vip":
                    if not (is_vip or is_privileged):
                        paid = 0
                        if username:
                            paid = self.bot.get_user_tip_amount(username) or 0
                        if paid <= 0:
                            return "Tip the bot first"
                    pos = self.bot.storage.load_vip_position()
                    if pos:
                        await self.bot.highrise.teleport(actor_id, pos)
                        return "teleported to location vip"
                loc = self.bot.storage.get_location(key)
                if loc:
                    if not (is_vip or is_privileged):
                        paid = 0
                        if username:
                            paid = self.bot.get_user_tip_amount(username) or 0
                        if paid <= 0:
                            return "Tip the bot first"
                    await self.bot.highrise.teleport(actor_id, loc)
                    return f"teleported to location {key}"
                return "User or location not found"
            if len(parts) >= 3:
                uname = parts[1].replace("@", "").strip()
                locname = parts[2].strip()
                uid = await self.bot.resolve_user_id(uname)
                if not uid:
                    return "User not found"
                if locname.lower() == "vip":
                    if not (is_vip or is_privileged):
                        return "VIP only location"
                    pos = self.bot.storage.load_vip_position()
                else:
                    pos = self.bot.storage.get_location(locname)
                if not pos:
                    return "Location not found"
                await self.bot.highrise.teleport(uid, pos)
                return f"teleported {uname} to {locname}"
            return "Usage: !tele @username [location]"
        except Exception:
            return "Failed to teleport"

    async def _summon(self, command: str, actor_id: str):
        try:
            parts = command.split()
            if len(parts) < 2:
                return "Usage: !summon @username"
            uname = parts[1].replace("@", "").strip()
            uid = await self.bot.resolve_user_id(uname)
            if not uid:
                return "User not found"
            msg = await self.bot.bring_to_user(uid, actor_id)
            return msg or "brought"
        except Exception:
            return "Failed to summon"

    async def _heart(self, command: str, is_mod: bool = False, is_owner_or_dev: bool = False):
        parts = command.split()
        if len(parts) < 2:
            return "Usage: !h @username [count]"
        uname = parts[1].replace("@", "").strip()
        count = 10
        if len(parts) >= 3 and parts[2].isdigit():
            req = int(parts[2])
            if req < 10 or req > 100:
                return " عدد 10 واكتر عدد 100 ولا يمكن اكتر"
            count = req
        uid = await self.bot.resolve_user_id(uname)
        if not uid:
            return "User not found"
        sent = 0
        for _ in range(count):
            try:
                await self.bot.highrise.react("heart", uid)
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                break
        return f"sent {sent} heart(s) to {uname}"

    async def _heart_all(self):
        try:
            room_users = await self.bot.highrise.get_room_users()
            sent = 0
            for ru, _ in room_users.content:
                if ru.id == self.bot.bot_id:
                    continue
                try:
                    await self.bot.highrise.react("heart", ru.id)
                    sent += 1
                    await asyncio.sleep(0.2)
                except Exception:
                    pass
            return f"sent hearts to {sent} users"
        except Exception:
            return "Failed to heart all"

    

    async def _emote_target(self, command: str, actor_id: str):
        parts = command.split()
        if len(parts) < 3:
            return "Usage: !emote <name> @username"
        name = parts[1].strip()
        uname = parts[2].replace("@", "").strip()
        uid = await self.bot.resolve_user_id(uname)
        if not uid:
            return "User not found"
        from emotes import ALL_EMOTE_LIST
        for label, code in ALL_EMOTE_LIST:
            if label.lower() == name.lower() or code.lower() == name.lower():
                try:
                    await self.bot.highrise.send_emote(code, uid)
                    try:
                        msg = f"{label} running. Type stop to end"
                        await self.bot.highrise.send_whisper(actor_id, msg)
                    except Exception:
                        pass
                    return None
                except Exception:
                    return "Failed to emote"
        return "Emote not found"

    async def _emote_self(self, command: str, actor_id: str):
        parts = command.split()
        if len(parts) < 2:
            try:
                from emotes import ALL_EMOTE_LIST
                dances = [code for _, code in ALL_EMOTE_LIST if code.startswith("dance-")]
                pool = dances if dances else [code for _, code in ALL_EMOTE_LIST]
                if not pool:
                    return "No emotes available"
                code = random.choice(pool)
                await self.bot.highrise.send_emote(code, actor_id)
                try:
                    lbl = None
                    for l, c in ALL_EMOTE_LIST:
                        if c.lower() == code.lower():
                            lbl = l
                            break
                    msg = f"{lbl or 'Emote'} running. Type stop to end emote"
                    await self.bot.highrise.send_whisper(actor_id, msg)
                except Exception:
                    pass
                return None
            except Exception:
                return "Failed to emote"
        arg = parts[1]
        if arg.isdigit():
            await self.bot.emote_by_index(int(arg))
            try:
                await self.bot.highrise.send_whisper(actor_id, "Emote running. Type stop to end")
            except Exception:
                pass
            return None
        name = arg.strip()
        from emotes import ALL_EMOTE_LIST
        for label, code in ALL_EMOTE_LIST:
            if label.lower() == name.lower() or code.lower() == name.lower():
                try:
                    await self.bot.highrise.send_emote(code, actor_id)
                    try:
                        msg = f"{label} running. Type stop to end"
                        await self.bot.highrise.send_whisper(actor_id, msg)
                    except Exception:
                        pass
                    return None
                except Exception:
                    return "Failed to emote"
        return "Emote not found"

    async def _flash(self, actor_id: str, command: str):
        parts = command.split()
        target_uid = actor_id
        if len(parts) >= 2 and parts[1].startswith("@"):
            uname = parts[1].replace("@", "").strip()
            uid = await self.bot.resolve_user_id(uname)
            if not uid:
                return "User not found"
            target_uid = uid
        return await self.bot.start_flash(actor_id, target_uid)

    async def _spam(self, actor_id: str, command: str):
        if actor_id != self.bot.owner_id:
            return "Unauthorized"
        parts = command.split()
        if len(parts) < 2:
            return "Usage: !s <seconds>"
        try:
            duration = int(float(parts[1].strip()))
        except Exception:
            return "Invalid seconds"
        if duration <= 0:
            return "Invalid seconds"
        duration = min(duration, 600)
        start = asyncio.get_event_loop().time()
        sent = 0
        words_pool = ["hello","vip","gold","love","wow","nice","cool","fast","fun","room","bot","navid","dance","gg","ok","hey","yo"]
        target = max(1, int(round(duration * 0.7)))
        interval = max(0.1, duration / target)
        while True:
            now = asyncio.get_event_loop().time()
            if now - start >= duration or sent >= target:
                break
            msg = f"hello {random.randint(1, 99999)} {random.choice(words_pool)}"
            try:
                await self.bot.highrise.chat(msg)
                sent += 1
            except Exception:
                await asyncio.sleep(0.1)
            await asyncio.sleep(interval)
        return f"spam done ({sent} messages)"

    
    async def _emote_label(self, label: str, actor_id: str):
        from emotes import ALL_EMOTE_LIST
        for l, code in ALL_EMOTE_LIST:
            if l.lower() == label.lower():
                try:
                    await self.bot.highrise.send_emote(code, actor_id)
                    return None
                except Exception:
                    return "Failed to emote"
        return "Emote not found"

    async def _buyvip(self, command: str, username: str | None):
        try:
            parts = command.split()
            if len(parts) < 3:
                return "Usage: !buyvip 1week 300 | !buyvip 1month 800"
            period = parts[1].lower()
            amount = int(parts[2])
            if period not in ("1week", "1month"):
                return "Usage: !buyvip 1week 300 | !buyvip 1month 800"
            required = 300 if period == "1week" else 800
            if amount < required:
                return f"Minimum {required}g required"
            if not username:
                return "Unauthorized"
            tips = self.bot.get_user_tip_amount(username) or 0
            if tips < amount:
                return "Tip the bot first, then buy VIP"
            days = 7 if period == "1week" else 30
            until = int(time.time()) + days * 24 * 3600
            self.bot.storage.set_vip_expiry(username, until)
            return f"VIP granted for {days} days"
        except Exception:
            return "Failed to buy VIP"

    async def _tipall(self, command: str):
        try:
            parts = command.split()
            if len(parts) < 2:
                return "Usage: !tipall amount"
            amount = int(float(parts[1]))
            if amount <= 0:
                return "Invalid amount"
            bot_wallet = await self.bot.highrise.get_wallet()
            try:
                bot_amount = bot_wallet.content[0].amount
            except Exception:
                bot_amount = 0
                for currency in bot_wallet.content:
                    if getattr(currency, "type", "") == "gold":
                        bot_amount = getattr(currency, "amount", 0) or 0
                        break
            bars_dictionary = {
                10000: "gold_bar_10k",
                5000: "gold_bar_5000",
                1000: "gold_bar_1k",
                500: "gold_bar_500",
                100: "gold_bar_100",
                50: "gold_bar_50",
                10: "gold_bar_10",
                5: "gold_bar_5",
                1: "gold_bar_1",
            }
            fees_dictionary = {
                10000: 1000,
                5000: 500,
                1000: 100,
                500: 50,
                100: 10,
                50: 5,
                10: 1,
                5: 1,
                1: 1,
            }
            tip_list = []
            total = 0
            remaining = amount
            for bar in sorted(bars_dictionary.keys(), reverse=True):
                if remaining >= bar:
                    count = remaining // bar
                    remaining = remaining % bar
                    for _ in range(count):
                        tip_list.append(bars_dictionary[bar])
                        total += bar + fees_dictionary[bar]
            if not tip_list:
                return "Invalid amount"
            tip_string = ",".join(tip_list)
            room_users = await self.bot.highrise.get_room_users()
            recipients = [ru.id for ru, _ in room_users.content if ru.id != self.bot.bot_id]
            needed = amount * len(recipients)
            if bot_amount <= needed:
                return "Not enough funds"
            if not hasattr(self.bot.highrise, "tip_user"):
                return "Tipping not supported"
            tipped = 0
            for uid in recipients:
                await self.bot.highrise.tip_user(uid, tip_string)
                tipped += 1
                await asyncio.sleep(0.2)
            return f"tipped {tipped} users"
        except Exception:
            return "Failed to tip all"

    async def _freeze(self, command: str):
        parts = command.split()
        if len(parts) < 2:
            return "Usage: !freeze @username"
        uname = parts[1].replace("@", "").strip()
        uid = await self.bot.resolve_user_id(uname)
        if not uid:
            return "User not found"
        try:
            pos = await self.bot._get_user_position(uid)
            if pos:
                self.bot.storage.set_freeze_position(uid, pos)
            self.bot.storage.set_frozen(uid, True)
            years10 = 10 * 365 * 24 * 3600
            self.bot.storage.mute_user(uid, years10)
            try:
                await self.bot.highrise.moderate_room(uid, "mute", years10)
            except Exception:
                pass
            await self.bot.start_freeze_monitor(uid)
            return f"froze {uname}"
        except Exception:
            return "Failed to freeze"

    async def _unfreeze(self, command: str):
        parts = command.split()
        if len(parts) < 2:
            return "Usage: !unfreeze @username"
        uname = parts[1].replace("@", "").strip()
        uid = await self.bot.resolve_user_id(uname)
        if not uid:
            return "User not found"
        try:
            self.bot.storage.set_frozen(uid, False)
            self.bot.storage.unmute_user(uid)
            await self.bot.stop_freeze_monitor(uid)
            try:
                self.bot.storage.clear_freeze_position(uid)
            except Exception:
                pass
            return f"unfroze {uname}"
        except Exception:
            return "Failed to unfreeze"

    async def _addmod(self, command: str):
        username = command.split(" ", 1)[1].replace("@", "").strip()
        if not username:
            return "Usage: !addmod @username"
        self.bot.storage.add_moderator(username)
        return "moderator added"

    async def _demod(self, command: str):
        username = command.split(" ", 1)[1].replace("@", "").strip()
        if not username:
            return "Usage: !demod @username"
        self.bot.storage.remove_moderator(username)
        return "moderator removed"

    async def _ban_permanent(self, command: str):
        try:
            username = command.split(" ", 1)[1].replace("@", "").strip()
            uid = await self.bot.resolve_user_id(username)
            if not uid:
                return "User not found"
            years10 = 10 * 365 * 24 * 3600
            self.bot.storage.ban_user(uid, years10)
            try:
                await self.bot.highrise.moderate_room(uid, "ban", years10)
            except Exception:
                pass
            return f"banned {username} permanently"
        except Exception:
            return "Usage: !ban @username"

    async def _love(self, command: str):
        try:
            parts = command.split()
            if len(parts) < 3:
                return "Usage: !love @user1 @user2"
            u1 = parts[1].replace("@", "").strip()
            u2 = parts[2].replace("@", "").strip()
            id1 = await self.bot.resolve_user_id(u1)
            id2 = await self.bot.resolve_user_id(u2)
            if not id1 or not id2:
                return "User not found"
            await self.bot.highrise.send_emote("emote-heartshape", id1)
            await self.bot.highrise.send_emote("emote-heartshape", id2)
            return None
        except Exception:
            return "Failed to love"

    async def _hate(self, command: str):
        try:
            parts = command.split()
            if len(parts) < 2:
                return "Usage: !hate @username"
            u = parts[1].replace("@", "").strip()
            uid = await self.bot.resolve_user_id(u)
            if not uid:
                return "User not found"
            await self.bot.highrise.send_emote("emoji-angry", uid)
            return None
        except Exception:
            return "Failed to hate"

    async def _addowner(self, command: str):
        try:
            parts = command.split()
            if len(parts) < 2:
                return "Usage: !addowner @username"
            username = parts[1].replace("@", "").strip()
            if not username:
                return "Usage: !addowner @username"
            self.bot.storage.add_owner(username)
            return f"owner added: {username}"
        except Exception:
            return "Failed to add owner"

    async def _rmowner(self, command: str):
        try:
            parts = command.split()
            if len(parts) < 2:
                return "Usage: !rmowner @username"
            username = parts[1].replace("@", "").strip()
            if not username:
                return "Usage: !rmowner @username"
            if username.lower() == "navidfrb":
                return "Cannot remove main owner"
            self.bot.storage.remove_owner(username)
            return f"owner removed: {username}"
        except Exception:
            return "Failed to remove owner"