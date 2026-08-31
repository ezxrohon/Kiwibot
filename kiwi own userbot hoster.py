import asyncio, logging, os, random, sys, tempfile, time, threading, base64, math
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import (
    ChatWriteForbiddenError, FloodWaitError, ChatAdminRequiredError,
    UserAdminInvalidError, UserNotParticipantError, UserBlockedError
)
from telethon.tl.functions.channels import (
    EditAdminRequest, EditTitleRequest, EditBannedRequest,
    InviteToChannelRequest, GetParticipantsRequest, LeaveChannelRequest,
    DeleteChannelRequest
)
from telethon.tl.functions.messages import (
    EditChatTitleRequest, EditChatAdminRequest, SetTypingRequest,
    ReadHistoryRequest, DeleteHistoryRequest
)
from telethon.tl.types import (
    ChatAdminRights, ChatBannedRights, Channel, Chat,
    ChannelParticipantsSearch, ChannelParticipantsAdmins,
    SendMessageTypingAction, SendMessageCancelAction
)
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
from telethon.tl.functions.contacts import BlockRequest, UnblockRequest
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

API_ID    = 33856248
API_HASH  = "27bd3006cfb0c0b38bf209132dd6fe1d"
BOT_TOKEN = "8998013378:AAEOe98rLtQ2cHG5lRp5PHo82NwffJFpycw"
OWNER_ID  = 7207873383
SESSION_NAME = "kiwi_session"

START_TIME   = datetime.now()
BOT_VERSION  = "𝙭𝙚𝙣𝙜𝙨-𝙣𝙚𝙬-𝙠𝙞𝙬𝙞"
P            = r"\."

logging.basicConfig(level=logging.WARNING, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("kiwiBot")

userbot_thread  = None
userbot_loop    = None
userbot_client  = None
userbot_running = False

# ════════════════════════════════════════════════════
#  ANTI-BAN — MAX SPEED
# ════════════════════════════════════════════════════

BASE_RAID  = 0.06
BASE_REPLY = 0.04
LAST_FLOOD = 0

def antiban(base=0.06):
    global LAST_FLOOD
    if time.time() < LAST_FLOOD:
        return random.uniform(0.3, 0.7)
    return max(0.04, min(base + random.uniform(-0.02, 0.05), 0.18))

def set_flood(wait):
    global LAST_FLOOD
    LAST_FLOOD = time.time() + wait

async def safe_delete(msg, delay=0.15):
    try:
        await asyncio.sleep(delay)
        await msg.delete()
    except Exception:
        pass

async def _handle_flood(e):
    set_flood(e.seconds)
    await asyncio.sleep(min(e.seconds, 30))

# ════════════════════════════════════════════════════
#  STATE STORAGE
# ════════════════════════════════════════════════════

raid_tasks         = {}
nc_tasks           = {}
cudega_tasks       = {}
rep_targets        = {}
reply_pools        = {}
reply_kiwi          = {}
reply_extreme      = {}
purge_targets      = {}
raid_reply_targets = {}
spamreply_tasks    = {}
tagall_tasks       = {}
typing_tasks       = {}
online_tasks       = {}
autoreact_chats    = {}   # {chat_id: emoji_list}
antipm_active      = {}   # {user_id: True}
autodel_chats      = {}   # {chat_id: seconds}
selfpurge_tasks    = {}
rndy_chats         = set()
tts_voice          = "en-US-AriaNeural"
warn_data          = {}   # {chat_id: {user_id: count}}
afk_mode           = {"active": False, "reason": "TBH, TOO BUSY IN MY LIFE!!"}
flood_mode_tasks   = {}

# ════════════════════════════════════════════════════
#  TEXT LISTS
# ════════════════════════════════════════════════════

FASTNC_TEXTS = [
    "🎐","💋","✨","🍂","🍀","🪐","〽️","✴️","💠","🥀","❄️",
    "🎗️","🎏","🪢","🐚","🫧","🦋","🪅","📍","🪄","🧸","🎋"
]
kiwi_EMOJIS = [
    "💕","💞","💟","💝","💘","💖","💓","💗","💌","💢","💥","💤","💦","💨",
    "🕉️","☪️","✝️","☮️","🕳️","💫","☸️","✡️","🔯","🪯","🕎","☯️","☦️",
    "🛐","⛎","♈","♉","♊","♐","♏","♎","♍","♌","♋","♑","♒","🆔",
    "⚕️","♾️","🈸","🈚","🈶","🈹","🈳","⚛️","🈺","🈷️","✴️","🉑","💮",
]
NCCUD_TEXTS = [
    "𝙏𝙚𝙧𝙞 𝙩𝙤 𝙢𝙖𝙖 𝙧𝙣𝙙𝙞","𝙩𝙚𝙧𝙞 𝙗𝙪𝙖 𝙠𝙞 𝙘𝙝𝙪𝙩","𝙩𝙚𝙧𝙞 𝙢𝙖𝙖 𝙠𝙖 𝙗𝙝𝙤𝙨𝙙𝙖","𝙘𝙝𝙪𝙙𝙖𝙞 𝙠𝙝𝙖","𝙡𝙪𝙣 𝙥𝙚 𝙣𝙖𝙖𝙘𝙝","𝙢𝙪𝙝 𝙢𝙖𝙞 𝙡𝙚","𝙩𝙪 𝙢𝙖𝙖 𝙘𝙝𝙪𝙙𝙖","𝙩𝙪 𝙗𝙚𝙝𝙚𝙣 𝙘𝙝𝙪𝙙𝙖","𝙩𝙪 𝙙𝙖𝙙𝙞 𝙘𝙝𝙪𝙙𝙖","𝙩𝙪 𝙣𝙖𝙣𝙞 𝙘𝙝𝙪𝙙𝙖","𝙩𝙪 𝙗𝙖𝙖𝙥 𝙘𝙝𝙪𝙙𝙖"
]
OPNC_TEXTS = [
    "જ⁀➴ 👑 ⁀➴ ⚡︎ ⁀➴ 👑 ⁀➴ ✨ ⁀➴ 🔥 ⁀➴ 👑",
    "⋆🌷🫧💭₊˚ෆִ໋🌷͙֒₊˚*ੈ♡⸝⸝🪐༘⋆‧₊˚🖇️✩ ₊˚🎧⊹♡",
    "𓊆ྀི🤍𓊇ྀི(っ҂° ཀ•)っ🕊️⊹˚.·:*¨༺ ☣ ༻¨*:·✃𓄧꒷꒦🎀",
    "𓂃 ࣪˖ ִֶָ🐇་༘࿐⋆⭒˚.⋆🪐 ⋆⭒˚.⋆ִֶָ. ..𓂃 ࣪ ִֶָ🦋་༘",
    "⚡︎🌃𓍙.ೃ࿔*:･⁺‧₊˚ ཐི⋆♱⋆ཋྀ ˚₊‧⁺°🥂⋆.ೃ🍾",
    "ೀ⋅⁀➴🌻✨જ⁀➴.⋅˚🎀⊹♡₊‧🌻✨🎀⊹♡",
    "𓂀 ☥ 𓋹 𓁈 𓆣 𓂀 ☥ 𓋹 𓁈 𓆣 𓂀 ☥ 𓋹",
    "💀 ⚚ ☠︎︎ ⛧¨༺ ☣ ༻¨💀 ⚚ ☠︎︎ ⛧",
    "🔱 ⚡︎ 👑 ⛧ 🔱 ⚡︎ 👑 ⛧ 🔱 ⚡︎ 👑",
    "🌊 🐚 𓇼 ✨ 🫧 🌊 🐚 𓇼 ✨ 🫧",
    "🩸 ☠︎︎ ⚚ 𖤓 🩸 ☠︎︎ ⚚ 𖤓 🩸 ☠︎︎",
]
RNDY_TEXTS = [
    "🥴 ɴʜɪ sᴜɴᴜɢᴀ ᴛᴇʀɪ ᴍᴀʏᴀᴠɪ ᴠᴀɪʏsʜʏᴀ ᴋᴇ ʟᴀᴅᴋᴇ😖",
    "🤮 ᴛᴜ ʟᴀᴅᴇɢᴀ ɢᴏʟ ɢᴀᴘᴘᴇ ᴡᴀʟᴇ ᴋᴇ ʟᴀᴅᴋᴇ😂",
    "😂👏🏻 ᴛᴇʀɪ ᴍᴀᴀ ᴋɪ ᴄʜᴀᴅᴅɪ ᴄʜᴜʀᴀ ʟɪ😹",
    "🪱 ᴛᴜ ʟᴀssɪ ᴮᴷᴸ🪱",
    "🌚 ᴛᴇʀɪ ʙʜᴇɴ ᴋᴀ ʙʀᴀ sɪᴢᴇ ʙᴀᴛᴀ ᴊʟᴅɪ🌚",
    "♾️ ᴛᴇʀᴇ ᵀᴼᵀᴬʟ ʙᴀᴀᴘ ɢɪɴ ᴋᴇ ʙᴀᴛᴀ♾️",
    "💦 ᴛᴇʀɪ ʙʜᴇɴ sᴘᴇʀᴍ ᴄᴏʟʟᴇᴄᴛᴏʀ💦",
    "🃏 ᴄʜᴀᴘᴘᴀʟ ᴄʜᴏʀ🤡",
    "🤭 ᴛᴇʀɪ ʙᴜᴀ sᴇx ᴡᴏʀᴋᴇʀ🤭",
    "No matter what you replied Just तेरी मां रंडी","ᴀᴘɴɪ ᴍᴀᴀ ʜᴜᴍsᴇ ʙʜɪ ᴄʜᴜᴅᴡᴀᴏ ᴋᴀʙʜɪ😖😝😍🥰🥰🥰","ᴛᴇʀɪ ᴍᴋᴄ ᴍᴀɪ ⁿɪⁿᴊᵃʜᴀᴛᴏʀɪ  **ᗪIᑎᘜ ᗪIᑎᘜ** ","ᴋɪᴡɪ ᴀʙʙᴀ ᴋɪ ɢᴜʟᴀᴀᴍɪ ᴋʀ🦶🦶🦶","ᴛᴇʀɪ ᴛᴏ ᴍᴀᴀ ʀɴᴅɪʏᴏ ᴋɪ ʀᴀɴɪ ʜᴀɪ👑👑👑","ᴀʀᴇ ᴛᴏʜᴀʀɪ ʙᴇʜᴇɴ ᴋɪ ᴄʜᴜᴛ ᴘᴇ ᴋᴜᴅ ᴋᴇ ᴇᴋ ʟᴀᴀᴛ ᴍᴀʀᴜ🐺","Lᴜɴ ᴘᴇ ᴛᴜ ᴏʀ ᴛᴇʀɪ ʙᴜᴀ ᴏᴋ?!🦁🦁🦁🦁🦁",
]
REP_TEXTS = [
"𝐊ʏᴀ 𝐑ᴇ 𝐑ᴀɴᴅɪᴋᴇ 𝐂ᴏᴏʟ 𝐁ᴀɴᴇɢᴀ 𝐓ᴜ 𝐂ʜᴀʟ 𝐀ʙ 𝐂ʜᴜᴅ 𝐀ᴘɴᴇ 𝐁ᴀᴀᴘ 𝙆𝙄𝙒𝙄 𝐒ᴇ - 🦢💘",
        "𝐓ᴇʀɪɪ 𝐌ᴀᴀ 𝐌ᴀʀʀ 𝐆ᴀʏɪ 𝐘ᴀᴀʀ - 𝐉ᴀɪ 𝙆𝙄𝙒𝙄 ! 🌙",
        "acha beta 😂🔥👊🏻 ? coi na me toh HATER codunga 😹💔🔥😆👊🏻💥",
        "chudke bhaga kaise 😂💥🤣🤘🏻",
        "ne toh 𝙆𝙄𝙒𝙄 ka lun muh me lelia 😂🙏🏻😂🙏🏻",
        "try maa सूर्य☀ nikalte hi pel du 😹🔥💔",
        "mkl lun te vaj 😂✊🏻💦",
        "𝗧ᴍᴋ𝗕 pe 𝙆𝙄𝙒𝙄 ka hamla 😂⚔🔥💥",
        "𝐂ʜʟ 𝐇ᴀʀᴍᴢᴀᴅ𝐈 𝐊ᴇ लड़के 💛🤍🩵",
        "oi 𝐓ᴇʀɪ 𝐌‌ᴀᴀ गुलाम ₰🖤",
        "chl rndyce chud ke dikha 😂💥🤣🔥",
        "𝐊ɪ 𝐌ᴀᴀ 𝐌ᴀʀʀ 𝐆ᴀʏɪ naacho 💃🏻💃🏻🕺🏻🎶😂😆💞🔥 !",
        "tera baap bass 𝙆𝙄𝙒𝙄 hai 😂🎀",
        "try maa hagte hue paad mari -#😹🔥🥀",
        "𝐓ᴇʀɪ 𝐌ᴜᴍᴍʏ 𝐂ʜᴏᴅ 𝐃ɪ 𝙆𝙄𝙒𝙄 𝐍ᴇ 𝐁ᴡᴀʜᴀʜᴀʜᴀ ⚜","तेरे मां के दूदू के बीच मेरा lund fas gaya oops 🤪（ ͜.🍆 ͜.）",
        "𝐓ᴇʀʏ 𝐁ʜᴇ𝐍 𝐊ᴇ ( ͜. ㅅ ͜. )🥛 ʏᴜᴍᴍʏ ",
        "𓂃☁︎ 𓂃𝐒ɪᴅᴇ 𝐇ᴀᴛ 𝐆ᴜʟᴀᴍ 𝐓ᴇʀʏ 𝐌ᴀᴀ 𝐊ᴏ 𝐂ʜᴏᴅɴᴇ  मेरी रेलगाड़ी आ रही .-'🚂-'.ᯓᡣ𐭩______ 𓂃☁︎ 𓂃",
        "⋆⭒˚.⋆🔭 𝐒ʜᴜᴛ 𝐔ᴘ 𝐑ᴀɴᴅɪᴋᴇ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ɪ 𝐂ʜᴜᴅᴀɪ 𝐄ɴᴊᴏʏ 𝐊ʀ 𝐑ᴀʜᴀ 𝐓ᴇʟᴇ𝐒ᴄᴏᴘᴇ 𝐒ᴇ⋆⭒˚.⋆🔭", "⋆｡ﾟ☁︎｡𝐂ʏᴜ 𝐑ᴇ मदरचोद 𝙆𝙄𝙒𝙄 बाप के सामने 𝐅ʏᴛᴇʀ 𝐁ᴀɴᴇɢᴀ ⋆𓂃 ོ☼𓂃 😂🔥",
        "नहीं नहीं तेरी मां को 𝐒ɪʀғ 𝙆𝙄𝙒𝙄 बाप चोद सकता है ִֶָ𓂃 ࣪ ִֶָ👑་༘࿐ sᴀᴍᴊʜᴀ ʀᴀɴᴅɪᴋᴇ ???",
        "तेरी मां का 𝐒ᴛʏʟɪsʜ भोसड़ा 😱",
        "𝑻𝒆𝒓𝒚 𝒎𝒂𝒂 𝒓𝒂𝒏𝒅𝒂𝒍 𝒉 𝒃𝒂𝒔 𝒃𝒂𝒂𝒕 𝒌𝒉𝒂𝒕𝒂𝒎 😡🔥",
        "सोच तेरी बहन को 𝙆𝙄𝙒𝙄 बाप का गुलाम चोद रहा 😎🔥",
        "Hello hello?? Oxygen aarahi है? रण्डी पुत्र 🧘🏻",
        "Shut up रंडीके वरना दुनिया यही बोलेगी तेरी बहन 𝙆𝙄𝙒𝙄 /~👑 बाप से सही chudi 🥵🔥",
        "ᴛᴜ ᴏʀ ᴛᴇʀɪ ᴍᴀᴀ ᴅᴏɴᴏ 𝙆𝙄𝙒𝙄 बाप के ʟɴᴅ sᴇ ᴋᴀʙʜɪ ᴜᴛʜ ɴʜɪ ᴘᴀʏᴇ 😂🔥","𓂃˖˳·˖ ִֶָ ⋆❤️͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚❤️ ݁˖⭑.ᐟ",
        "𓂃˖˳·˖ ִֶָ ⋆🧡͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚🧡 ݁˖⭑.ᐟ",
        "𓂃˖˳·˖ ִֶָ ⋆💛͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💛 ݁˖⭑.ᐟ",
        "𓂃˖˳·˖ ִֶָ ⋆💚͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💚 ݁˖⭑.ᐟ",
        "𓂃˖˳·˖ ִֶָ ⋆💙͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💙 ݁˖⭑.ᐟ","𝐎ყᴇ 𝐁ᴇᴛꪖ 𝐓ʀყ 𝐌ㄖ𝐌 𝐑ᴀɴᴅყ ❤️‍🔥❤️‍🩹🤍🖤💖💛💙💔",
    "{𝙆𝙄𝙒𝙄 𝗫 भगवान🔥} 𝘒𝘈 हुक्म है 𝘈𝘈𝘗𝘒𝘖 𝘓𝘜𝘕ꪻ☄️ 𝘜𝘛𝘛𝘌 𝘝𝘈𝘑𝘈𝘠𝘈 𝘑𝘈𝘈𝘠𝘌 जय 𝙆𝙄𝙒𝙄 𝗫 भगवान!",
    "𓂃˖˳·˖ ִֶָ ⋆🖤͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚🖤 ݁˖⭑.ᐟ",
    "𝐂ʜᴀʟ 𝐇ᴀʀᴍᴢᴀᴅ𝐈 𝐊ᴇ लड़के 🤍☁🍃",
    "𝗧𝗘𝗥𝗜 𝗠𝗔𝗔 𝗥𝗔𝗡𝗗𝗜 🤢🔫ﾟ｡✧･ﾟ:*⋆｡ﾟ｡🛰 　°·　　　•　° ★　• ☄ ‎ ‎ ‎ ‎ ‎ ‎",
    "ꪮყꫀ ƁꫀƬᴀ 𝐊ꪖꪖꪀ 𝐊ʜꪮꪶᴋꫀ sꪊꪀ ƬꫀƦᎥ ɱᴀᴀ ƦᴀꪀƊᎥ 👂🏻💛👂🏻🩵👂🏻💚👂🏻?",
    "क्या रे 𝐙ᴏᴍᴀᴛᴏ 𝐁ᴏʏ 𝐒ᴘᴍᴍᴇʀ बनेगा 𝐓ᴍᴋᴄ मारू 🤢🖕🏻",
    "ꪶ  𝗟𝗡𝗗 𝗖𝗛𝗨𝗦 ꪻ♡︎ ❤️‍🔥🥱😂",
    "𝐁ᴀᴀ𝐏 𝐊ᴏ 𝐑ᴇᴘʟ𝐘 𝐁ᴀᴅ𝐈 𝐓ᴇ𝐙 𝐃ᴇʀ𝐀 𝐇ᴀ𝐈",
    "ƬꫀƦᎥ बहन की चूत ӇᎥꪀƊᎥ ɱꫀ चोद के बजाऊ कमज़ोर 😂🎀",
    "चुप ɬꫀƦﺃ ოꪖꪖ ƦꪖꪀƊყ ♡ ❤️‍🔥¿",
    " 𝑆𝑙ꪖꪜꫀ ♡︎🦋",
    "ƬꫀƦᎥ Ɓꫀꪀ ᥴi भोसड़ी beta 👍🏿👍🏿💛",
    "ƬꫀƦᎥ माँ चुद कर क्या क्या करती रहती हैँ दिन भर रन्डीगिकी‽ 😆👑",
    "ƬꫀƦᎥ माँ meri गर्लफ्रेंड 😄🔥💘",
    "ƬꫀƦᎥ भुआ सेक्सी 𝐒ყ cudti ए 😂👌🏿🔥",
    "ƬꫀƦᎥ मोम ×2 cudi रण्डी 𝐂ꫀ लड़के 🙌🏿😂🔥",
    "याद कर ƬꫀƦᎥ आख़री चुदायी बेटा 🙌🏿🔥",
    " ƬꫀƦᎥ Ɓꫀʜꫀꪀ 𝐊ɪ ᥴʜꪊᴛ 𝐇ᴀᴛʜ Ɗꫀ𝐊ꫀ Ƥʜᴀᴀᴅ Ɗꫀꪀɢꫀ 𝙆𝙄𝙒𝙄 𝗫 भगवान🦅🤞🏿🔥",
]
CUDEGA_TEMPLATES = [
    ("━━━━━━━━ 💗᪲᪲᪲ ✝ 𝐀ɴᴛᴀ𝐑 𝐌ᴀɴ𝐓ᴀʀ 𝐒ʜ𝐀ɪ𝐓ᴀɴ𝐈 𝐊ʜᴏ𝐏ᴀ𝐃𝐀 "
     "{name} 𝐆ᴀ𝐑ɪ𝐁 𝐊ɪ 𝐀ᴍᴍ𝐈 𝐊ᴀ 𝐊ᴀ𝐋𝐀 𝐁ʜᴏs𝐃ᴀ ━━━━━━━━\n") * 10,
    ("🦅 𝐌αᴛᴋҽ 𝐌ҽ 𝐍ʜι 𝐓ʜα 𝐏αɳι 💦 {name} 🕷 "
     "𝐊ι 𝐌αα 𝐁αнαη 𝐑αη∂ιуσ 𝐊ι 𝐑αηι 🧊❤️‍🔥🥵\n") * 8,
    ("𝘼𝙉𝙏𝘼𝙍 𝙈𝘼𝙉𝙏𝘼𝙍 𝙎𝙃𝘼𝙄𝙏𝘼𝙉𝙄 𝙆𝙃𝙊𝙋𝘿𝘼 "
     "{name}⚡⚡ 𝙆𝙄 𝙈𝘼 𝙆𝘼 𝙆𝘼𝙇𝘼 𝘽𝙃𝙊𝙎𝘿𝘼\n") * 12,
    ("🔥💀 {name} ᴋɪ ᴍᴀᴀ ʙʜᴏsᴅɪᴋᴇ ᴛᴇʀɪ ᴀᴜᴋᴀᴛ ᴋʏᴀ ʜᴀɪ ᴄʜᴜᴛɪʏᴇ 💀🔥\n") * 15,
    ("⚡ {name} ᴋɪ ᴍᴀᴀ ᴋᴀ ᴋᴀʟᴀ ʙʜᴏsᴅᴀ ᴛᴜ ᴋʏᴀ ᴄʜᴇᴇᴢ ʜᴀɪ ꜱᴀᴀʟᴇ 🤡\n") * 10,
("⚡ {name} Teri maa rndiii_______
{name} teri maa ka balatkar/_______\n") * 10,
]
RAID_POOL = [
    "𝙏𝙍𝙔 𝙈𝘼 𝙆𝙊 🥵","𝘼𝙐𝙆𝘼𝙏 𝙈𝙀 𝙍𝙀𝙃 𝙇𝙊𝘿𝙀",
    "𝙏𝙀𝙍𝘼 𝘽𝘼𝘼𝙋 𝙃𝙐 𝙈𝘼𝙄","𝘾𝙃𝘼𝙇 𝙉𝙄𝙆𝘼𝙇 𝘽𝙃𝙊𝙎𝘿𝙄𝙆𝙀",
    "𝙏𝙀𝙍𝙄 𝙈𝘼 𝙆𝘼 𝙋𝘼𝙏𝙄 𝙃𝘼𝙄","𝘽𝙃𝘼𝘼𝙂 𝙈𝘼𝙏 𝙋𝙄𝙇𝙇𝙀 𝙊𝙔𝙀",
]
DEFAULT_REACT_EMOJIS = ["🔥","💀","😈","⚡","🤡","💯","😂","🥵","👑","🗿"]

# ════════════════════════════════════════════════════
#  DECORATED HELP TEXT
# ════════════════════════════════════════════════════

HELP_TEXT = """
𝙋𝙪𝙧𝙫𝙖𝙣𝙘𝙝𝙖𝙡 𝙭 𝙠𝙚𝙣𝙜𝙨 シ︎

⏤͟͟͞͞★꙰⃤𝜩🦕𝜩🦕𝜩 𝙉𝙘 𝙡𝙤𝙤𝙥𝙨 𝜩🦕𝜩🦕𝜩⏤͟͟͞͞★꙰⃤

`.fastnc <name>`     — Emoji loop
`.kiwiemojis <name>` — Heart emojis loop
`.nccud <name>`      — Abusive text loop
`.opnc <name>`       — Decorative loop
`.stopnc`            — Name change band

⏤͟͟͞͞★꙰⃤𝜩🐺𝜩🐺𝜩 𝙎𝙥𝙖𝙢𝙨 𝜩🐺𝜩🐺𝜩⏤͟͟͞͞★꙰⃤

`.cudega <name>`     — Template spam (non-stop loop)
`.stopcudega`        — Cudega band
`.raid <msg>`        — Endless spam loop
`.stopraid`          — Raid band
`.flood <msg> <n>`   — N messages ASAP
`.spam <msg> <n>`    — N baar bhejo (fast)
`.raidreply`         — (Reply) Target ko non-stop insult loop
`.stopraidreply`     — Raid reply band
`.spamreply <msg>`   — (Reply) Target ko non-stop spam loop
`.stopspamreply`     — Spam reply band
`.replyextreme <msg> <n>` — N baar reply
`.stopextreme`       — Extreme band


⏤͟͟͞͞★꙰⃤𝜩🌒𝜩🌒𝜩 𝘼.𝙍 𝙏𝙤𝙤𝙡 𝜩🌘𝜩🌘𝜩⏤͟͟͞͞★꙰⃤

`.rndy`              — Saari msgs pe auto gali (non-stop)
`.stoprndy`          — Rndy band
`.rep`               — (Reply) Abusive loop on target (non-stop)
`.stoprep`           — Rep band
`.replykiwi <msg>`    — (Reply) Fixed reply loop (non-stop)
`.stopkiwi`           — kiwi band
`.replypool <a|b|c>` — Pool se random reply
`.stoppool`          — Pool band
`.afk <reason>`      — AFK mode on (auto reply to mentions)
`.stopafk`           — AFK band
`.antipm <msg>`      — Auto reply to PM (non-stop)
`.stopantipm`        — AntiPM band
`.autoreact`         — Auto react to incoming msgs
`.stopautoreact`     — AutoReact band

⏤͟͟͞͞★꙰⃤𝜩〽️𝜩〽️𝜩 𝙂𝙧𝙤𝙪𝙥 𝜩〽️𝜩〽️𝜩⏤͟͟͞͞★꙰⃤

`.add <user>`        — Add + Promote
`.promote <user>`    — Sirf promote
`.demote <user>`     — Admin rights hatao
`.remadmin`          — (Reply) Admin remove
`.promoall`          — Sabko admin
`.kickall`           — Sabko kick
`.nikal <user>`      — Specific kick
`.ban <user>`        — Ban karo
`.unban <user>`      — Unban karo
`.mute <user>`       — Mute karo
`.unmute <user>`     — Unmute karo
`.warn <user>`       — Warn (3=auto ban)
`.warns <user>`      — Warns check
`.resetwarns <user>` — Warns reset
`.pin`               — (Reply) Pin msg
`.unpin`             — Last pin hatao
`.unpinall`          — Saare pins hatao
`.pinspam <msg> <n>` — N baar pin spam
`.nuke`              — Sabko ban (NUKE)
`.kickme`            — Group chhodo
`.listadmins`        — Admins list
`.members`           — Member count
`.chatinfo`          — Group full info
`.title <title>`     — (Reply) Admin title
`.inviteall <link>`  — Sabko invite karo

⏤͟͟͞͞★꙰⃤𝜩👾𝜩👾𝜩  𝙏𝙖𝙜𝙨  𝜩👾𝜩👾𝜩⏤͟͟͞͞★꙰⃤

`.tagall <msg>`      — Sabko tag loop
`.stoptagall`        — Tag band
`.everyone <msg>`    — Ek baar sabko tag
`.broadcast <msg>`   — Saare members ko DM
`.massdm <msg>`      — Group members ko DM loop

⏤͟͟͞͞★꙰⃤𝜩👑𝜩👑𝜩  𝙋𝙧𝙤𝙛𝙞𝙡𝙚  𝜩👑𝜩👑𝜩⏤͟͟͞͞★꙰⃤

`.setname <first> <last>` — Naam change
`.setbio <text>`     — Bio set
`.setpic`            — (Reply) Profile pic
`.delpic`            — Profile pic delete
`.username <name>`   — Username change

⏤͟͟͞͞★꙰⃤𝜩☁️𝜩☁️𝜩 𝙎𝙩𝙚𝙖𝙡𝙩𝙝 𝜩☁️𝜩☁️𝜩⏤͟͟͞͞★꙰⃤

`.faketyping`        — Typing status loop
`.stopfaketyping`    — Typing band
`.fakeonline`        — Online status loop
`.stopfakeonline`    — Online band
`.ghostping`         — (Reply) Ghost ping
`.markread`          — Chat messages mark as read
`.selfpurge <n>`     — Apne last N msgs delete

⏤͟͟͞͞★꙰⃤𝜩🕸️𝜩🕸️𝜩 𝙐𝙩𝙞𝙡𝙞𝙩𝙞𝙚𝙨 𝜩🕸️𝜩🕸️𝜩⏤͟͟͞͞★꙰⃤ 

`.ping`              — Speed check
`.alive`             — Status + uptime
`.id`                — User/Chat ID
`.info`              — (Reply) Full user info
`.purge`             — (Reply) User msgs delete
`.stoppurge`         — Purge band
`.del`               — (Reply) Delete msg
`.copy`              — (Reply) Copy msg
`.forward <chatid>`  — (Reply) Forward msg
`.autodel <secs>`    — Auto delete own msgs
`.stopautodel`       — AutoDel band
`.block <user>`      — User block
`.unblock <user>`    — User unblock
`.speed <sec>`       — Delay set
`.stopall`           —  Sabkuch band

⏤͟͟͞͞★꙰⃤𝜩🌛𝜩🌛𝜩𝙏𝙚𝙭𝙩 𝙩𝙤𝙤𝙡𝙨𝜩🌜𝜩🌜𝜩⏤͟͟͞͞★꙰⃤

`.mock <text>`       — mOcKiNg text
`.vp <text>`         — Ｖａｐｏｒwave
`.tiny <text>`       — ᵗⁱⁿʸ text
`.reverse <text>`    — Reverse text
`.upper <text>`      — UPPERCASE
`.lower <text>`      — lowercase
`.b64 <text>`        — Base64 encode
`.unb64 <text>`      — Base64 decode
`.char <text>`       — Character count
`.calc <expr>`       — Calculator
`.repeat <msg> <n>`  — N baar bhejo
`.ascii <text>`      — ASCII art

⏤͟͟͞͞★꙰⃤𝜩🎙️𝜩🎙️𝜩 𝙏𝙏𝙎 𝜩🎙️𝜩🎙️𝜩⏤͟͟͞͞★꙰⃤

`.tts <text>`        — Voice note
`.ttsreply`          — Reply ko voice note
`.ttsvoice <name>`   — Voice change
`.ttslist`           — Voices list

⏤͟͟͞͞★꙰⃤𝜩😝𝜩😝𝜩  𝙁𝙪𝙣  𝜩😝𝜩😝𝜩⏤͟͟͞͞★꙰⃤

`.dice`              — Dice roll
`.flip`              — Coin flip
`.8ball <q>`         — Magic 8 ball
`.roast`             — Random roast
`.ship <u1> <u2>`    — Shipping percent

.𝙨𝙩𝙤𝙥𝙖𝙡𝙡 𝙩𝙤 𝙨𝙩𝙤𝙥 𝙖𝙡𝙡 (𝙥𝙧𝙞𝙢𝙚 𝙘𝙤𝙢𝙢𝙖𝙣𝙙)"""

MENU_TEXT = """╔═══════════════════════════════╗
║ ⚡ 𝗣𝗨𝗥𝗩𝗔𝗡𝗖𝗛𝗔𝗟𝗜  𝘃𝟴.𝟬 — 1ˢᵗ⚡ ║
╚═══════════════════════════════╝
🎭 **NAME** → `.fastnc` `.kiwiemojis` `.nccud` `.opnc` `.stopnc`
🔥 **SPAM** → `.cudega` `.raid` `.flood` `.spam` `.raidreply` `.spamreply`
💬 **REPLY** → `.rndy` `.rep` `.replykiwi` `.replypool` `.afk` `.antipm`
👑 **GROUP** → `.promoall` `.kickall` `.nikal` `.ban` `.mute` `.warn` `.nuke`
📣 **TAG** → `.tagall` `.everyone` `.broadcast` `.massdm`
🎭 **PROFILE** → `.setname` `.setbio` `.setpic` `.username`
🕵️ **STEALTH** → `.faketyping` `.fakeonline` `.ghostping` `.markread`
🔧 **TEXT** → `.mock` `.vp` `.tiny` `.reverse` `.b64` `.calc` `.ascii`
🎙 **TTS** → `.tts` `.ttsreply` `.ttsvoice`
🎲 **FUN** → `.dice` `.flip` `.8ball` `.roast` `.ship`
🧰 **UTILS** → `.ping` `.alive` `.id` `.info` `.purge` `.del` `.forward`
⛔ `.stopall` | 📋 `.help` — Full list"""

# ════════════════════════════════════════════════════
#  USERBOT HANDLER SETUP
# ════════════════════════════════════════════════════

def setup_userbot_handlers(client):

    # ─── HELP / MENU ─────────────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}(help|menu)$"))
    async def help_cmd(event):
        await event.edit(MENU_TEXT if event.pattern_match.group(1) == "menu" else HELP_TEXT)

    # ─── PING / ALIVE / ID / INFO ────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}ping$"))
    async def ping_cmd(event):
        t = time.perf_counter()
        await event.edit("⚡")
        ms = (time.perf_counter() - t) * 1000
        await event.edit(f"**🏓 PONG!**\n`{ms:.2f}ms`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}alive$"))
    async def alive_cmd(event):
        uptime = datetime.now() - START_TIME
        h, rem = divmod(int(uptime.total_seconds()), 3600)
        m, s   = divmod(rem, 60)
        await event.edit(
            f"╔══ ⚡ 𝗣𝗨𝗥𝗩𝗔𝗡𝗖𝗛𝗔𝗟𝗜 𝙭𝙠𝙚𝙣𝙜𝙨 𝗔𝗟𝗜𝗩𝗘 ⚡ ══╗\n"
            f"**Ver:** `{BOT_VERSION}`\n"
            f"**Up:** `{h}h {m}m {s}s`\n"
            f"**Raids:** `{len(raid_tasks)}`\n"
            f"**Cudega:** `{len(cudega_tasks)}`\n"
            f"**Rndy:** `{len(rndy_chats)}`\n"
            f"**Rep Targets:** `{sum(len(v) for v in rep_targets.values())}`\n"
            f"**AutoReact:** `{len(autoreact_chats)}`\n"
            f"**AFK:** `{afk_mode['active']}`\n"
            f"╚═══════════════════╝"
        )

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}id$"))
    async def id_cmd(event):
        reply = await event.get_reply_message()
        if reply and reply.sender_id:
            user = await reply.get_sender()
            name = getattr(user, 'first_name', 'Unknown')
            await event.edit(f"**👤 {name}**\n**User ID:** `{reply.sender_id}`\n**Chat ID:** `{event.chat_id}`")
        else:
            await event.edit(f"**💬 Chat ID:** `{event.chat_id}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}info$"))
    async def info_cmd(event):
        reply = await event.get_reply_message()
        if not reply: return await safe_delete(event)
        user = await reply.get_sender()
        if not user: return await event.edit("❌ User info nahi mili")
        name  = getattr(user, 'first_name', '') or ''
        last  = getattr(user, 'last_name', '') or ''
        uname = f"@{user.username}" if getattr(user, 'username', None) else "None"
        await event.edit(
            f"╔══ 📋 𝗨𝗦𝗘𝗥 𝗜𝗡𝗙𝗢 ══╗\n"
            f"**Name:** `{name} {last}`\n"
            f"**ID:** `{user.id}`\n"
            f"**Username:** {uname}\n"
            f"**Bot:** `{getattr(user,'bot',False)}`\n"
            f"**Verified:** `{getattr(user,'verified',False)}`\n"
            f"**Scam:** `{getattr(user,'scam',False)}`\n"
            f"**Fake:** `{getattr(user,'fake',False)}`\n"
            f"**Premium:** `{getattr(user,'premium',False)}`\n"
            f"╚═══════════════════╝"
        )

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}chatinfo$"))
    async def chatinfo_cmd(event):
        try:
            chat  = await client.get_entity(event.chat_id)
            title = getattr(chat, 'title', 'N/A')
            count = getattr(chat, 'participants_count', 'N/A')
            cid   = event.chat_id
            uname = f"@{chat.username}" if getattr(chat, 'username', None) else "None"
            mega  = getattr(chat, 'megagroup', False)
            bcast = getattr(chat, 'broadcast', False)
            await event.edit(
                f"╔══ 💬 𝐂𝐡𝐚𝐭 𝐢𝐧𝐟𝐨 ══╗\n"
                f"**Title:** `{title}`\n"
                f"**ID:** `{cid}`\n"
                f"**Username:** {uname}\n"
                f"**Members:** `{count}`\n"
                f"**Supergroup:** `{mega}`\n"
                f"**Channel:** `{bcast}`\n"
                f"╚═════════════════╝"
            )
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    # ─── GROUP NAME CHANGERS (FIXED) ─────────────────
    async def name_loop(chat_id, base_name, texts, interval=0.75):
        idx = 0
        try:
            entity = await client.get_entity(chat_id)
            while True:
                new_name = f"{base_name} {texts[idx % len(texts)]}"
                try:
                    if isinstance(entity, Channel):
                        await client(EditTitleRequest(entity, new_name))
                    else:
                        await client(EditChatTitleRequest(chat_id, new_name))
                except FloodWaitError as e:
                    await _handle_flood(e)
                except Exception as e:
                    log.warning(f"NC: {e}")
                    await asyncio.sleep(1.5)
                await asyncio.sleep(interval)
                idx += 1
        except asyncio.CancelledError:
            pass

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}fastnc\s+(.+)"))
    async def fastnc_cmd(event):
        chat = event.chat_id
        if chat in nc_tasks: nc_tasks[chat].cancel()
        nc_tasks[chat] = asyncio.create_task(name_loop(chat, event.pattern_match.group(1).strip(), FASTNC_TEXTS, 0.75))
        await safe_delete(event)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}kiwiemojis\s+(.+)"))
    async def kiwiemojis_cmd(event):
        chat = event.chat_id
        if chat in nc_tasks: nc_tasks[chat].cancel()
        nc_tasks[chat] = asyncio.create_task(name_loop(chat, event.pattern_match.group(1).strip(), kiwi_EMOJIS, 0.65))
        await safe_delete(event)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}nccud\s+(.+)"))
    async def nccud_cmd(event):
        chat = event.chat_id
        if chat in nc_tasks: nc_tasks[chat].cancel()
        nc_tasks[chat] = asyncio.create_task(name_loop(chat, event.pattern_match.group(1).strip(), NCCUD_TEXTS, 0.85))
        await safe_delete(event)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}opnc\s+(.+)"))
    async def opnc_cmd(event):
        chat = event.chat_id
        if chat in nc_tasks: nc_tasks[chat].cancel()
        nc_tasks[chat] = asyncio.create_task(name_loop(chat, event.pattern_match.group(1).strip(), OPNC_TEXTS, 0.80))
        await safe_delete(event)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}stopnc$"))
    async def stopnc_cmd(event):
        t = nc_tasks.pop(event.chat_id, None)
        if t: t.cancel()
        await safe_delete(event)

    # ─── RNDY (non-stop) ─────────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}rndy$"))
    async def rndy_cmd(event):
        rndy_chats.add(event.chat_id)
        await safe_delete(event)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}stoprndy$"))
    async def stoprndy_cmd(event):
        rndy_chats.discard(event.chat_id)
        await safe_delete(event)

    @client.on(events.NewMessage(incoming=True))
    async def rndy_listener(event):
        if event.chat_id not in rndy_chats: return
        if not event.message or not event.message.text: return
        try:
            await asyncio.sleep(antiban(BASE_REPLY))
            await event.reply(random.choice(RNDY_TEXTS))
        except Exception: pass

    # ─── REP (non-stop loop) ─────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}rep$"))
    async def rep_cmd(event):
        reply = await event.get_reply_message()
        if not reply or not reply.sender_id: return await safe_delete(event)
        rep_targets.setdefault(event.chat_id, set()).add(reply.sender_id)
        await safe_delete(event)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}stoprep$"))
    async def stoprep_cmd(event):
        reply = await event.get_reply_message()
        if reply and reply.sender_id:
            rep_targets.get(event.chat_id, set()).discard(reply.sender_id)
        else:
            rep_targets.pop(event.chat_id, None)
        await safe_delete(event)

    @client.on(events.NewMessage(incoming=True))
    async def rep_listener(event):
        chat = event.chat_id
        if chat not in rep_targets: return
        if event.sender_id not in rep_targets[chat]: return
        try:
            await asyncio.sleep(antiban(BASE_REPLY))
            await event.reply(random.choice(REP_TEXTS))
        except Exception: pass

    # ─── CUDEGA (non-stop loop) ───────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}cudega\s+(.+)"))
    async def cudega_cmd(event):
        name = event.pattern_match.group(1).strip()
        chat = event.chat_id
        if chat in cudega_tasks: cudega_tasks[chat].cancel()
        async def _loop():
            idx = 0
            try:
                while True:
                    txt = CUDEGA_TEMPLATES[idx % len(CUDEGA_TEMPLATES)].replace("{name}", name)
                    try:
                        await client.send_message(chat, txt[:4096])
                        await asyncio.sleep(antiban(BASE_RAID))
                    except FloodWaitError as e:
                        await _handle_flood(e)
                    except ChatWriteForbiddenError:
                        break
                    except Exception as e:
                        log.warning(f"cudega: {e}")
                        await asyncio.sleep(1)
                    idx += 1
            except asyncio.CancelledError:
                pass
        cudega_tasks[chat] = asyncio.create_task(_loop())
        await safe_delete(event)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}stopcudega$"))
    async def stopcudega_cmd(event):
        t = cudega_tasks.pop(event.chat_id, None)
        if t: t.cancel()
        await safe_delete(event)

    # ─── RAID ────────────────────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}raid\s+(.+)"))
    async def raid_cmd(event):
        msg  = event.pattern_match.group(1)
        chat = event.chat_id
        if chat in raid_tasks: raid_tasks[chat].cancel()
        async def _loop():
            try:
                while True:
                    try:
                        await client.send_message(chat, msg)
                        await asyncio.sleep(antiban(BASE_RAID))
                    except FloodWaitError as e:
                        await _handle_flood(e)
                    except ChatWriteForbiddenError:
                        break
                    except Exception:
                        await asyncio.sleep(0.8)
            except asyncio.CancelledError:
                pass
        raid_tasks[chat] = asyncio.create_task(_loop())
        await safe_delete(event)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}stopraid$"))
    async def stopraid_cmd(event):
        t = raid_tasks.pop(event.chat_id, None)
        if t: t.cancel()
        await safe_delete(event)

    # ─── FLOOD (burst N msgs fast) ───────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}flood\s+(.+?)\s+(\d+)$"))
    async def flood_cmd(event):
        msg   = event.pattern_match.group(1)
        count = min(int(event.pattern_match.group(2)), 200)
        chat  = event.chat_id
        await safe_delete(event)
        for _ in range(count):
            try:
                await client.send_message(chat, msg)
                await asyncio.sleep(antiban(0.05))
            except FloodWaitError as e:
                await _handle_flood(e)
            except Exception:
                break

    # ─── SPAM (burst N times) ────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}spam\s+(.+?)\s+(\d+)$"))
    async def spam_cmd(event):
        msg   = event.pattern_match.group(1)
        count = min(int(event.pattern_match.group(2)), 500)
        chat  = event.chat_id
        await safe_delete(event)
        for _ in range(count):
            try:
                await client.send_message(chat, msg)
                await asyncio.sleep(antiban(BASE_RAID))
            except FloodWaitError as e:
                await _handle_flood(e)
            except Exception:
                break

    # ─── RAID REPLY (non-stop) ────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}raidreply$"))
    async def raidreply_cmd(event):
        reply = await event.get_reply_message()
        if not reply or not reply.sender_id: return await safe_delete(event)
        raid_reply_targets.setdefault(event.chat_id, set()).add(reply.sender_id)
        await safe_delete(event)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}stopraidreply$"))
    async def stopraidreply_cmd(event):
        reply = await event.get_reply_message()
        if reply and reply.sender_id:
            raid_reply_targets.get(event.chat_id, set()).discard(reply.sender_id)
        else:
            raid_reply_targets.pop(event.chat_id, None)
        await safe_delete(event)

    @client.on(events.NewMessage(incoming=True))
    async def raidreply_listener(event):
        chat = event.chat_id
        if chat not in raid_reply_targets: return
        if event.sender_id not in raid_reply_targets[chat]: return
        try:
            await asyncio.sleep(antiban(BASE_REPLY))
            await event.reply(random.choice(RAID_POOL))
        except Exception: pass

    # ─── SPAM REPLY (loop) ───────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}spamreply\s+(.+)"))
    async def spamreply_cmd(event):
        msg   = event.pattern_match.group(1)
        reply = await event.get_reply_message()
        if not reply or not reply.sender_id: return await safe_delete(event)
        key = (event.chat_id, reply.sender_id)
        if key in spamreply_tasks: spamreply_tasks[key].cancel()
        chat = event.chat_id
        async def _loop():
            try:
                while True:
                    try:
                        await client.send_message(chat, msg)
                        await asyncio.sleep(antiban(BASE_RAID))
                    except FloodWaitError as e:
                        await _handle_flood(e)
                    except Exception:
                        await asyncio.sleep(0.8)
            except asyncio.CancelledError:
                pass
        spamreply_tasks[key] = asyncio.create_task(_loop())
        await safe_delete(event)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}stopspamreply$"))
    async def stopspamreply_cmd(event):
        keys = [k for k in spamreply_tasks if k[0] == event.chat_id]
        for k in keys:
            t = spamreply_tasks.pop(k, None)
            if t: t.cancel()
        await safe_delete(event)

    # ─── EXTREME ─────────────────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}replyextreme\s+(.+?)\s+(\d+)$"))
    async def extreme_cmd(event):
        msg   = event.pattern_match.group(1)
        count = int(event.pattern_match.group(2))
        reply = await event.get_reply_message()
        if not reply or not reply.sender_id: return await safe_delete(event)
        reply_extreme.setdefault(event.chat_id, {})[reply.sender_id] = {'msg': msg, 'limit': count}
        await safe_delete(event)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}stopextreme$"))
    async def stopextreme_cmd(event):
        reply_extreme.pop(event.chat_id, None)
        await safe_delete(event)

    @client.on(events.NewMessage(incoming=True))
    async def extreme_listener(event):
        chat = event.chat_id
        if chat not in reply_extreme: return
        uid = event.sender_id
        if uid not in reply_extreme[chat]: return
        data = reply_extreme[chat][uid]
        if data['limit'] <= 0:
            reply_extreme[chat].pop(uid, None)
            return
        try:
            await asyncio.sleep(antiban(BASE_REPLY))
            await event.reply(data['msg'])
            reply_extreme[chat][uid]['limit'] -= 1
        except Exception: pass

    # ─── REPLY kiwi (non-stop) ────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}replykiwi\s+(.+)"))
    async def replykiwi_cmd(event):
        msg   = event.pattern_match.group(1)
        reply = await event.get_reply_message()
        if not reply or not reply.sender_id: return await safe_delete(event)
        reply_kiwi.setdefault(event.chat_id, {})[reply.sender_id] = msg
        await safe_delete(event)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}stopkiwi$"))
    async def stopkiwi_cmd(event):
        reply = await event.get_reply_message()
        if reply and reply.sender_id:
            reply_kiwi.get(event.chat_id, {}).pop(reply.sender_id, None)
        else:
            reply_kiwi.pop(event.chat_id, None)
        await safe_delete(event)

    @client.on(events.NewMessage(incoming=True))
    async def kiwi_listener(event):
        chat = event.chat_id
        if chat not in reply_kiwi: return
        uid = event.sender_id
        if uid not in reply_kiwi[chat]: return
        try:
            await asyncio.sleep(antiban(BASE_REPLY))
            await event.reply(reply_kiwi[chat][uid])
        except Exception: pass

    # ─── REPLY POOL (non-stop) ────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}replypool\s+(.+)"))
    async def pool_cmd(event):
        reply_pools[event.chat_id] = event.pattern_match.group(1).split("|")
        await safe_delete(event)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}stoppool$"))
    async def stoppool_cmd(event):
        reply_pools.pop(event.chat_id, None)
        await safe_delete(event)

    @client.on(events.NewMessage(incoming=True))
    async def pool_listener(event):
        if event.chat_id not in reply_pools: return
        try:
            await asyncio.sleep(antiban(BASE_REPLY))
            await event.reply(random.choice(reply_pools[event.chat_id]))
        except Exception: pass

    # ─── AFK MODE ────────────────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}afk(?:\s+(.+))?$"))
    async def afk_cmd(event):
        reason = event.pattern_match.group(1) or "AFK hoon"
        afk_mode["active"] = True
        afk_mode["reason"] = reason
        await event.edit(f"💤 **AFK mode on:** `{reason}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}stopafk$"))
    async def stopafk_cmd(event):
        afk_mode["active"] = False
        await safe_delete(event)

    @client.on(events.NewMessage(incoming=True))
    async def afk_listener(event):
        if not afk_mode["active"]: return
        me = await client.get_me()
        if event.mentioned or (hasattr(event.message, 'is_private') and event.message.is_private):
            try:
                await event.reply(f"💤 **Main AFK hoon:** `{afk_mode['reason']}`")
            except Exception: pass

    # ─── ANTI PM ─────────────────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}antipm\s+(.+)"))
    async def antipm_cmd(event):
        msg = event.pattern_match.group(1)
        antipm_active["msg"] = msg
        antipm_active["on"] = True
        await safe_delete(event)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}stopantipm$"))
    async def stopantipm_cmd(event):
        antipm_active["on"] = False
        await safe_delete(event)

    @client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
    async def antipm_listener(event):
        if not antipm_active.get("on"): return
        try:
            await event.reply(antipm_active.get("msg", "Auto reply"))
        except Exception: pass

    # ─── AUTO REACT ──────────────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}autoreact(?:\s+(.+))?$"))
    async def autoreact_cmd(event):
        raw = event.pattern_match.group(1)
        emojis = raw.split() if raw else DEFAULT_REACT_EMOJIS
        autoreact_chats[event.chat_id] = emojis
        await safe_delete(event)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}stopautoreact$"))
    async def stopautoreact_cmd(event):
        autoreact_chats.pop(event.chat_id, None)
        await safe_delete(event)

    @client.on(events.NewMessage(incoming=True))
    async def autoreact_listener(event):
        chat = event.chat_id
        if chat not in autoreact_chats: return
        if not event.message: return
        try:
            from telethon.tl.functions.messages import SendReactionRequest
            from telethon.tl.types import ReactionEmoji
            emoji = random.choice(autoreact_chats[chat])
            await client(SendReactionRequest(
                peer=chat,
                msg_id=event.id,
                reaction=[ReactionEmoji(emoticon=emoji)]
            ))
        except Exception: pass

    # ─── FAKE TYPING (loop) ──────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}faketyping$"))
    async def faketyping_cmd(event):
        chat = event.chat_id
        if chat in typing_tasks: typing_tasks[chat].cancel()
        async def _loop():
            try:
                while True:
                    try:
                        await client(SetTypingRequest(chat, SendMessageTypingAction()))
                        await asyncio.sleep(4)
                    except Exception:
                        await asyncio.sleep(2)
            except asyncio.CancelledError:
                try:
                    await client(SetTypingRequest(chat, SendMessageCancelAction()))
                except Exception: pass
        typing_tasks[chat] = asyncio.create_task(_loop())
        await safe_delete(event)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}stopfaketyping$"))
    async def stopfaketyping_cmd(event):
        t = typing_tasks.pop(event.chat_id, None)
        if t: t.cancel()
        await safe_delete(event)

    # ─── FAKE ONLINE (loop) ──────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}fakeonline$"))
    async def fakeonline_cmd(event):
        if "online" in online_tasks:
            online_tasks["online"].cancel()
        async def _loop():
            from telethon.tl.functions.account import UpdateStatusRequest
            try:
                while True:
                    try:
                        await client(UpdateStatusRequest(offline=False))
                        await asyncio.sleep(25)
                    except Exception:
                        await asyncio.sleep(5)
            except asyncio.CancelledError:
                try:
                    from telethon.tl.functions.account import UpdateStatusRequest
                    await client(UpdateStatusRequest(offline=True))
                except Exception: pass
        online_tasks["online"] = asyncio.create_task(_loop())
        await safe_delete(event)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}stopfakeonline$"))
    async def stopfakeonline_cmd(event):
        t = online_tasks.pop("online", None)
        if t: t.cancel()
        await safe_delete(event)

    # ─── MARK READ ───────────────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}markread$"))
    async def markread_cmd(event):
        try:
            await client(ReadHistoryRequest(peer=event.chat_id, max_id=0))
            await safe_delete(event)
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    # ─── SELF PURGE ──────────────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}selfpurge(?:\s+(\d+))?$"))
    async def selfpurge_cmd(event):
        limit = int(event.pattern_match.group(1) or 50)
        chat  = event.chat_id
        await event.delete()
        me = await client.get_me()
        async for msg in client.iter_messages(chat, from_user=me.id, limit=limit):
            try:
                await msg.delete()
                await asyncio.sleep(0.04)
            except Exception: pass

    # ─── AUTO DELETE OWN MSGS ────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}autodel\s+(\d+)$"))
    async def autodel_cmd(event):
        secs = int(event.pattern_match.group(1))
        autodel_chats[event.chat_id] = secs
        await event.edit(f"🗑 **AutoDel:** `{secs}s` pe delete")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}stopautodel$"))
    async def stopautodel_cmd(event):
        autodel_chats.pop(event.chat_id, None)
        await safe_delete(event)

    @client.on(events.NewMessage(outgoing=True))
    async def autodel_listener(event):
        chat = event.chat_id
        if chat not in autodel_chats: return
        if any(event.text.startswith(f".autodel") or event.text.startswith(".stopautodel")
               for _ in [0]): return
        secs = autodel_chats[chat]
        asyncio.create_task(safe_delete(event, secs))

    # ─── GHOST PING ──────────────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}ghostping$"))
    async def ghostping_cmd(event):
        reply = await event.get_reply_message()
        if not reply or not reply.sender_id: return await safe_delete(event)
        user = await reply.get_sender()
        name = getattr(user, 'first_name', 'User')
        sent = await client.send_message(event.chat_id, f"[{name}](tg://user?id={reply.sender_id}) 👻")
        await safe_delete(event, 0)
        await asyncio.sleep(0.4)
        await sent.delete()

    # ─── REPEAT / FLOOD ──────────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}repeat\s+(.+?)\s+(\d+)$"))
    async def repeat_cmd(event):
        msg   = event.pattern_match.group(1)
        count = min(int(event.pattern_match.group(2)), 200)
        await safe_delete(event)
        for _ in range(count):
            try:
                await client.send_message(event.chat_id, msg)
                await asyncio.sleep(antiban(BASE_RAID))
            except FloodWaitError as e:
                await _handle_flood(e)

    # ─── PURGE ───────────────────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}purge$"))
    async def purge_cmd(event):
        reply = await event.get_reply_message()
        if not reply or not reply.sender_id: return await safe_delete(event)
        uid  = reply.sender_id
        chat = event.chat_id
        await safe_delete(event)
        async for msg in client.iter_messages(chat, from_user=uid, limit=500):
            try:
                await msg.delete()
                await asyncio.sleep(0.03)
            except Exception: pass

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}stoppurge$"))
    async def stoppurge_cmd(event):
        purge_targets.pop(event.chat_id, None)
        await safe_delete(event)

    # ─── COPY / DEL / FORWARD ────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}copy$"))
    async def copy_cmd(event):
        reply = await event.get_reply_message()
        if not reply: return await safe_delete(event)
        await safe_delete(event)
        if reply.text:
            await client.send_message(event.chat_id, reply.text)
        elif reply.media:
            await client.send_file(event.chat_id, reply.media, caption=reply.message or "")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}del$"))
    async def del_cmd(event):
        reply = await event.get_reply_message()
        if reply: await reply.delete()
        await event.delete()

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}forward\s+(-?\d+)"))
    async def forward_cmd(event):
        reply = await event.get_reply_message()
        if not reply: return await safe_delete(event)
        try:
            await client.forward_messages(int(event.pattern_match.group(1)), reply)
            await event.edit("✅ **Forwarded!**")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    # ─── BLOCK / UNBLOCK ─────────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}block\s+(\S+)"))
    async def block_cmd(event):
        target = event.pattern_match.group(1).lstrip("@")
        try:
            user = await client.get_entity(target)
            await client(BlockRequest(user))
            await event.edit(f"🚫 **{target} block ho gaya!**")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}unblock\s+(\S+)"))
    async def unblock_cmd(event):
        target = event.pattern_match.group(1).lstrip("@")
        try:
            user = await client.get_entity(target)
            await client(UnblockRequest(user))
            await event.edit(f"✅ **{target} unblock ho gaya!**")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    # ─── SPEED / STOPALL ─────────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}speed\s+(\d+\.?\d*)$"))
    async def speed_cmd(event):
        custom_speed[event.chat_id] = float(event.pattern_match.group(1))
        await event.edit(f"✅ **Speed:** `{event.pattern_match.group(1)}s`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}stopall$"))
    async def stopall_cmd(event):
        chat = event.chat_id
        for d in [raid_tasks, nc_tasks, cudega_tasks, tagall_tasks, typing_tasks]:
            t = d.pop(chat, None)
            if t: t.cancel()
        for k in [k for k in spamreply_tasks if k[0] == chat]:
            t = spamreply_tasks.pop(k, None)
            if t: t.cancel()
        rndy_chats.discard(chat)
        rep_targets.pop(chat, None)
        reply_pools.pop(chat, None)
        reply_kiwi.pop(chat, None)
        reply_extreme.pop(chat, None)
        raid_reply_targets.pop(chat, None)
        purge_targets.pop(chat, None)
        autoreact_chats.pop(chat, None)
        autodel_chats.pop(chat, None)
        afk_mode["active"] = False
        antipm_active["on"] = False
        t = online_tasks.pop("online", None)
        if t: t.cancel()
        await event.edit("⛔ **Sabkuch band kiya! Ultra kiwi Mode off.**")

    # ─── GROUP MANAGEMENT ────────────────────────────
    async def promote_user(chat_id, user_id, title="Admin"):
        try:
            rights = ChatAdminRights(
                post_messages=True, add_admins=False, invite_users=True,
                change_info=True, ban_users=True, delete_messages=True,
                pin_messages=True, manage_call=True, edit_messages=True
            )
            await client(EditAdminRequest(chat_id, user_id, rights, rank=title))
        except Exception as e:
            log.warning(f"promote: {e}")

    async def demote_user(chat_id, user_id):
        try:
            await client(EditAdminRequest(chat_id, user_id, ChatAdminRights(), rank=""))
        except Exception as e:
            log.warning(f"demote: {e}")

    async def kick_user(chat_id, user_id):
        try:
            ban   = ChatBannedRights(until_date=None, view_messages=True)
            unban = ChatBannedRights(until_date=None)
            await client(EditBannedRequest(chat_id, user_id, ban))
            await asyncio.sleep(0.15)
            await client(EditBannedRequest(chat_id, user_id, unban))
        except Exception as e:
            log.warning(f"kick: {e}")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}add\s+(\S+)"))
    async def add_cmd(event):
        uname = event.pattern_match.group(1).lstrip("@")
        try:
            user = await client.get_entity(uname)
            await client(InviteToChannelRequest(event.chat_id, [user]))
            await promote_user(event.chat_id, user.id)
            await event.edit(f"✅ **Added + Promoted:** `{uname}`")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}promote\s+(\S+)"))
    async def promote_cmd(event):
        uname = event.pattern_match.group(1).lstrip("@")
        try:
            user = await client.get_entity(uname)
            await promote_user(event.chat_id, user.id)
            await event.edit(f"✅ **Promoted:** `{uname}`")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}demote\s+(\S+)"))
    async def demote_cmd(event):
        uname = event.pattern_match.group(1).lstrip("@")
        try:
            user = await client.get_entity(uname)
            await demote_user(event.chat_id, user.id)
            await event.edit(f"✅ **Demoted:** `{uname}`")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}remadmin$"))
    async def remadmin_cmd(event):
        reply = await event.get_reply_message()
        if not reply or not reply.sender_id: return await safe_delete(event)
        try:
            await demote_user(event.chat_id, reply.sender_id)
            await event.edit("✅ **Admin remove kar diya!**")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}promoall$"))
    async def promoall_cmd(event):
        await event.edit("👑 **Sabko promote kar raha hoon...**")
        count = 0
        async for p in client.iter_participants(event.chat_id):
            if p.bot or p.is_self: continue
            try:
                await promote_user(event.chat_id, p.id)
                count += 1
                await asyncio.sleep(0.35)
            except Exception: pass
        await event.edit(f"✅ **{count} promote kiye!** 👑")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}kickall$"))
    async def kickall_cmd(event):
        await event.edit("👢 **Sabko kick kar raha hoon...**")
        count = 0
        async for p in client.iter_participants(event.chat_id):
            if p.bot or p.is_self: continue
            try:
                await kick_user(event.chat_id, p.id)
                count += 1
                await asyncio.sleep(0.2)
            except Exception: pass
        await client.send_message(event.chat_id, f"👢 **{count} kick kiye!**")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}nikal\s+(\S+)"))
    async def nikal_cmd(event):
        target = event.pattern_match.group(1).lstrip("@")
        try:
            user = await client.get_entity(target)
            await kick_user(event.chat_id, user.id)
            await event.edit(f"👢 **{target} kick ho gaya!**")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}ban\s+(\S+)"))
    async def ban_cmd(event):
        target = event.pattern_match.group(1).lstrip("@")
        try:
            user = await client.get_entity(target)
            await client(EditBannedRequest(event.chat_id, user, ChatBannedRights(until_date=None, view_messages=True)))
            await event.edit(f"🔨 **{target} BAN!**")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}unban\s+(\S+)"))
    async def unban_cmd(event):
        target = event.pattern_match.group(1).lstrip("@")
        try:
            user = await client.get_entity(target)
            await client(EditBannedRequest(event.chat_id, user, ChatBannedRights(until_date=None)))
            await event.edit(f"✅ **{target} unban ho gaya!**")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}mute\s+(\S+)"))
    async def mute_cmd(event):
        target = event.pattern_match.group(1).lstrip("@")
        try:
            user = await client.get_entity(target)
            await client(EditBannedRequest(event.chat_id, user, ChatBannedRights(until_date=None, send_messages=True)))
            await event.edit(f"🔇 **{target} mute!**")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}unmute\s+(\S+)"))
    async def unmute_cmd(event):
        target = event.pattern_match.group(1).lstrip("@")
        try:
            user = await client.get_entity(target)
            await client(EditBannedRequest(event.chat_id, user, ChatBannedRights(until_date=None)))
            await event.edit(f"🔊 **{target} unmute!**")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}warn\s+(\S+)"))
    async def warn_cmd(event):
        target = event.pattern_match.group(1).lstrip("@")
        try:
            user = await client.get_entity(target)
            uid  = user.id
            chat = event.chat_id
            warn_data.setdefault(chat, {})
            warn_data[chat][uid] = warn_data[chat].get(uid, 0) + 1
            count = warn_data[chat][uid]
            if count >= 3:
                await client(EditBannedRequest(chat, user, ChatBannedRights(until_date=None, view_messages=True)))
                warn_data[chat].pop(uid, None)
                await event.edit(f"🔨 **{target} — 3 warns, BAN!**")
            else:
                await event.edit(f"⚠️ **{target} warned!** `[{count}/3]`")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}warns\s+(\S+)"))
    async def warns_cmd(event):
        target = event.pattern_match.group(1).lstrip("@")
        try:
            user  = await client.get_entity(target)
            count = warn_data.get(event.chat_id, {}).get(user.id, 0)
            await event.edit(f"⚠️ **{target}:** `{count}/3` warns")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}resetwarns\s+(\S+)"))
    async def resetwarns_cmd(event):
        target = event.pattern_match.group(1).lstrip("@")
        try:
            user = await client.get_entity(target)
            warn_data.get(event.chat_id, {}).pop(user.id, None)
            await event.edit(f"✅ **{target}** warns reset!")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}pin$"))
    async def pin_cmd(event):
        reply = await event.get_reply_message()
        if not reply: return await safe_delete(event)
        try:
            await client.pin_message(event.chat_id, reply.id, notify=False)
            await safe_delete(event)
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}unpin$"))
    async def unpin_cmd(event):
        try:
            await client.unpin_message(event.chat_id)
            await safe_delete(event)
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}unpinall$"))
    async def unpinall_cmd(event):
        try:
            await client.unpin_message(event.chat_id, message=None)
            await event.edit("✅ **Saare pins hata diye!**")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}pinspam\s+(.+?)\s+(\d+)$"))
    async def pinspam_cmd(event):
        msg   = event.pattern_match.group(1)
        count = min(int(event.pattern_match.group(2)), 20)
        chat  = event.chat_id
        await safe_delete(event)
        for _ in range(count):
            try:
                sent = await client.send_message(chat, msg)
                await client.pin_message(chat, sent.id, notify=True)
                await asyncio.sleep(antiban(BASE_RAID))
            except FloodWaitError as e:
                await _handle_flood(e)
            except Exception: break

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}title\s+(.+)"))
    async def title_cmd(event):
        title = event.pattern_match.group(1)
        reply = await event.get_reply_message()
        if not reply or not reply.sender_id: return await safe_delete(event)
        try:
            rights = ChatAdminRights(change_info=False)
            await client(EditAdminRequest(event.chat_id, reply.sender_id, rights, rank=title))
            await event.edit(f"✅ **Title:** `{title}`")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}nuke$"))
    async def nuke_cmd(event):
        await event.edit("💣 **NUKE MODE ACTIVE...**")
        count = 0
        async for p in client.iter_participants(event.chat_id):
            if p.is_self: continue
            try:
                await client(EditBannedRequest(event.chat_id, p, ChatBannedRights(until_date=None, view_messages=True)))
                count += 1
                await asyncio.sleep(0.18)
            except Exception: pass
        await client.send_message(event.chat_id, f"💣 **NUKE COMPLETE!** `{count}` banned.")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}kickme$"))
    async def kickme_cmd(event):
        await event.delete()
        await client.delete_dialog(event.chat_id)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}listadmins$"))
    async def listadmins_cmd(event):
        try:
            admins = []
            async for p in client.iter_participants(event.chat_id, filter=ChannelParticipantsAdmins()):
                name  = getattr(p, 'first_name', '') or 'N/A'
                uname = f"@{p.username}" if getattr(p, 'username', None) else f"`{p.id}`"
                admins.append(f"👑 **{name}** — {uname}")
            text = "**🏆 Admins:**\n" + "\n".join(admins[:30]) if admins else "**No admins found**"
            await event.edit(text)
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}members$"))
    async def members_cmd(event):
        try:
            chat  = await client.get_entity(event.chat_id)
            count = getattr(chat, 'participants_count', 'N/A')
            title = getattr(chat, 'title', 'Group')
            await event.edit(f"**👥 {title}**\n**Members:** `{count}`")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}chatinfo$"))
    async def chatinfo_cmd(event):
        try:
            chat  = await client.get_entity(event.chat_id)
            title = getattr(chat, 'title', 'N/A')
            count = getattr(chat, 'participants_count', 'N/A')
            uname = f"@{chat.username}" if getattr(chat, 'username', None) else "None"
            mega  = getattr(chat, 'megagroup', False)
            bcast = getattr(chat, 'broadcast', False)
            await event.edit(
                f"╔══ 💬 𝗖𝗛𝗔𝗧 𝗜𝗡𝗙𝗢 ══╗\n"
                f"**Title:** `{title}`\n"
                f"**ID:** `{event.chat_id}`\n"
                f"**Username:** {uname}\n"
                f"**Members:** `{count}`\n"
                f"**Supergroup:** `{mega}`\n"
                f"**Channel:** `{bcast}`\n"
                f"╚═════════════════╝"
            )
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}inviteall\s+(\S+)"))
    async def inviteall_cmd(event):
        link  = event.pattern_match.group(1)
        await event.edit("📨 **Inviting all members...**")
        count = 0
        try:
            target = await client.get_entity(link)
        except Exception as e:
            return await event.edit(f"❌ Invalid link: `{e}`")
        async for p in client.iter_participants(event.chat_id):
            if p.bot or p.is_self: continue
            try:
                await client(InviteToChannelRequest(target, [p]))
                count += 1
                await asyncio.sleep(0.5)
            except Exception: pass
        await event.edit(f"✅ **{count} members invite kiye!**")

    # ─── TAG ALL (loop) ───────────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}tagall(?:\s+(.+))?$"))
    async def tagall_cmd(event):
        msg  = (event.pattern_match.group(1) or "👋").strip()
        chat = event.chat_id
        if chat in tagall_tasks: tagall_tasks[chat].cancel()
        async def _loop():
            try:
                while True:
                    try:
                        members = []
                        async for p in client.iter_participants(chat):
                            if p.bot or p.is_self: continue
                            name = getattr(p, 'first_name', '') or 'User'
                            members.append(f"[{name}](tg://user?id={p.id})")
                            if len(members) >= 5:
                                await client.send_message(chat, f"{msg} {' '.join(members)}")
                                members = []
                                await asyncio.sleep(antiban(BASE_RAID))
                        if members:
                            await client.send_message(chat, f"{msg} {' '.join(members)}")
                        await asyncio.sleep(antiban(BASE_RAID))
                    except FloodWaitError as e:
                        await _handle_flood(e)
                    except Exception:
                        await asyncio.sleep(2)
            except asyncio.CancelledError:
                pass
        tagall_tasks[chat] = asyncio.create_task(_loop())
        await safe_delete(event)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}stoptagall$"))
    async def stoptagall_cmd(event):
        t = tagall_tasks.pop(event.chat_id, None)
        if t: t.cancel()
        await safe_delete(event)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}everyone(?:\s+(.+))?$"))
    async def everyone_cmd(event):
        msg  = (event.pattern_match.group(1) or "👋").strip()
        chat = event.chat_id
        await safe_delete(event)
        members = []
        async for p in client.iter_participants(chat):
            if p.bot or p.is_self: continue
            name = getattr(p, 'first_name', '') or 'User'
            members.append(f"[{name}](tg://user?id={p.id})")
            if len(members) >= 5:
                try:
                    await client.send_message(chat, f"{msg} {' '.join(members)}")
                    members = []
                    await asyncio.sleep(antiban(BASE_RAID))
                except FloodWaitError as e:
                    await _handle_flood(e)
        if members:
            await client.send_message(chat, f"{msg} {' '.join(members)}")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}broadcast\s+(.+)"))
    async def broadcast_cmd(event):
        msg  = event.pattern_match.group(1)
        chat = event.chat_id
        sent = fail = 0
        await event.edit("📣 **Broadcasting...**")
        async for p in client.iter_participants(chat):
            if p.bot or p.is_self: continue
            try:
                await client.send_message(p.id, msg)
                sent += 1
                await asyncio.sleep(0.45)
            except Exception:
                fail += 1
        await event.edit(f"✅ **Broadcast done!**\n✅ `{sent}` | ❌ `{fail}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}massdm\s+(.+)"))
    async def massdm_cmd(event):
        msg  = event.pattern_match.group(1)
        chat = event.chat_id
        await event.edit("💬 **Mass DM chal raha hai...**")
        sent = 0
        async for p in client.iter_participants(chat):
            if p.bot or p.is_self: continue
            try:
                await client.send_message(p.id, msg)
                sent += 1
                await asyncio.sleep(antiban(0.5))
            except Exception: pass
        await event.edit(f"✅ **Mass DM done:** `{sent}` messages")

    # ─── PROFILE TOOLS ───────────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}setname\s+(\S+)(?:\s+(.+))?$"))
    async def setname_cmd(event):
        first = event.pattern_match.group(1)
        last  = event.pattern_match.group(2) or ""
        try:
            await client(UpdateProfileRequest(first_name=first, last_name=last))
            await event.edit(f"✅ **Name:** `{first} {last}`")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}setbio\s+(.+)"))
    async def setbio_cmd(event):
        bio = event.pattern_match.group(1)
        try:
            await client(UpdateProfileRequest(about=bio))
            await event.edit(f"✅ **Bio:** `{bio[:60]}`")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}username\s+(\S+)"))
    async def username_cmd(event):
        uname = event.pattern_match.group(1).lstrip("@")
        try:
            await client(UpdateUsernameRequest(uname))
            await event.edit(f"✅ **Username:** `@{uname}`")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}setpic$"))
    async def setpic_cmd(event):
        reply = await event.get_reply_message()
        if not reply or not reply.photo: return await event.edit("❌ Photo reply karo!")
        try:
            from telethon.tl.functions.photos import UploadProfilePhotoRequest
            data = await client.download_media(reply.photo, bytes)
            await client(UploadProfilePhotoRequest(await client.upload_file(data, file_name="pic.jpg")))
            await event.edit("✅ **Profile pic set!**")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}delpic$"))
    async def delpic_cmd(event):
        try:
            from telethon.tl.functions.photos import DeletePhotosRequest, GetUserPhotosRequest
            photos = await client(GetUserPhotosRequest(await client.get_me(), offset=0, max_id=0, limit=1))
            if photos.photos:
                await client(DeletePhotosRequest(photos.photos))
                await event.edit("✅ **Profile pic delete ho gaya!**")
            else:
                await event.edit("❌ Koi photo nahi mili")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    # ─── TTS ─────────────────────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}ttslist$"))
    async def ttslist_cmd(event):
        await event.edit(
            "**🎙 TTS Voices:**\n"
            "`en-US-AriaNeural` — English Female\n"
            "`en-US-GuyNeural` — English Male\n"
            "`hi-IN-SwaraNeural` — Hindi Female\n"
            "`hi-IN-MadhurNeural` — Hindi Male\n"
            "`ur-PK-AsadNeural` — Urdu Male\n"
            "\n`.ttsvoice <name>` se change karo"
        )

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}ttsvoice\s+(\S+)"))
    async def ttsvoice_cmd(event):
        global tts_voice
        tts_voice = event.pattern_match.group(1)
        await event.edit(f"✅ **TTS:** `{tts_voice}`")

    async def _tts_send(event, text, voice):
        try:
            import edge_tts
        except ImportError:
            await event.edit("❌ `pip install edge-tts`")
            return
        await event.edit("🎙 Generating...")
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
        try:
            await edge_tts.Communicate(text, voice).save(tmp)
            await safe_delete(event, 0)
            await client.send_file(event.chat_id, tmp, voice_note=True)
        except Exception as e:
            await event.edit(f"❌ `{e}`")
        finally:
            if os.path.exists(tmp): os.unlink(tmp)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}tts\s+(.+)"))
    async def tts_cmd(event):
        text  = event.pattern_match.group(1)
        voice = tts_voice
        parts = text.split(None, 1)
        lmap = {"en": "en-US-AriaNeural", "hi": "hi-IN-SwaraNeural", "ur": "ur-PK-AsadNeural"}
        if len(parts) == 2 and parts[0].lower() in lmap:
            voice = lmap[parts[0].lower()]
            text  = parts[1]
        await _tts_send(event, text, voice)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}ttsreply$"))
    async def ttsreply_cmd(event):
        reply = await event.get_reply_message()
        if not reply or not reply.text: return await safe_delete(event)
        await _tts_send(event, reply.text[:500], tts_voice)

    # ─── TEXT TOOLS ──────────────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}mock\s+(.+)"))
    async def mock_cmd(event):
        t = event.pattern_match.group(1)
        await event.edit("".join(c.upper() if i % 2 else c.lower() for i, c in enumerate(t)))

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}vp\s+(.+)"))
    async def vp_cmd(event):
        N = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        V = "ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ０１２３４５６７８９"
        await event.edit(event.pattern_match.group(1).translate(str.maketrans(N, V)))

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}tiny\s+(.+)"))
    async def tiny_cmd(event):
        N = "abcdefghijklmnopqrstuvwxyz0123456789"
        T = "ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖᵠʳˢᵗᵘᵛʷˣʸᶻ⁰¹²³⁴⁵⁶⁷⁸⁹"
        await event.edit(event.pattern_match.group(1).lower().translate(str.maketrans(N, T)))

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}reverse\s+(.+)"))
    async def reverse_cmd(event):
        await event.edit(event.pattern_match.group(1)[::-1])

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}upper\s+(.+)"))
    async def upper_cmd(event):
        await event.edit(event.pattern_match.group(1).upper())

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}lower\s+(.+)"))
    async def lower_cmd(event):
        await event.edit(event.pattern_match.group(1).lower())

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}b64\s+(.+)"))
    async def b64_cmd(event):
        enc = base64.b64encode(event.pattern_match.group(1).encode()).decode()
        await event.edit(f"**🔐 Base64:**\n`{enc}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}unb64\s+(.+)"))
    async def unb64_cmd(event):
        try:
            dec = base64.b64decode(event.pattern_match.group(1).encode()).decode()
            await event.edit(f"**🔓 Decoded:**\n`{dec}`")
        except Exception:
            await event.edit("❌ Invalid base64!")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}char\s+(.+)"))
    async def char_cmd(event):
        t = event.pattern_match.group(1)
        await event.edit(f"**📝 Text:** `{t[:50]}`\n**Chars:** `{len(t)}`\n**Words:** `{len(t.split())}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}calc\s+(.+)"))
    async def calc_cmd(event):
        expr = event.pattern_match.group(1)
        try:
            allowed = set("0123456789+-*/().% ")
            if not all(c in allowed for c in expr):
                return await event.edit("❌ Invalid characters!")
            result = eval(expr, {"__builtins__": {}, "math": math}, {})
            await event.edit(f"🧮 `{expr}` = **`{result}`**")
        except Exception as e:
            await event.edit(f"❌ `{e}`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}ascii\s+(.+)"))
    async def ascii_cmd(event):
        t = event.pattern_match.group(1).upper()
        blk = {"A":"▄▀█","B":"█▄▄","C":"█▀▀","D":"█▀▄","E":"█▀▀","F":"█▀▀","G":"█▀▀",
               "H":"█ █","I":"█","J":" ▄█","K":"█▄▀","L":"█  ","M":"█▀█▀█","N":"█▄ █",
               "O":"█▀█","P":"█▀█","Q":"█▀▀","R":"█▀▄","S":"▄▀▀","T":"▀█▀","U":"█ █",
               "V":"▀▄▀","W":"█ ▄ █","X":"▀▄▀","Y":"▀▄▀","Z":"▀▀▄"," ":"   "}
        result = " ".join(blk.get(c, c) for c in t)
        await event.edit(f"`{result}`")

    # ─── FUN ─────────────────────────────────────────
    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}dice$"))
    async def dice_cmd(event):
        n = random.randint(1, 6)
        await event.edit(f"{'⚀⚁⚂⚃⚄⚅'[n-1]} **Dice: {n}**")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}flip$"))
    async def flip_cmd(event):
        await event.edit(random.choice(["🪙 **Heads!**", "🪙 **Tails!**"]))

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}8ball\s+(.+)"))
    async def eightball_cmd(event):
        answers = [
            "✅ Bilkul haan!", "✅ Pakka!", "🤔 Shayad...", "❌ Nahi bhai nahi!",
            "🔮 Aage dekho acha hoga", "💯 100% YES", "🎱 Doubtful bhai",
            "⚡ Abhi nahi, baad mein", "😂 Are yaar LOL nahi", "👑 kiwi NE KAHA HAAN"
        ]
        await event.edit(f"🎱 **{random.choice(answers)}**")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}roast$"))
    async def roast_cmd(event):
        roasts = [
            "Teri IQ aur shoe size same hai 🤡",
            "Tu itna boring hai ki neend bhi tujhse bhaag jaati hai 💤",
            "Teri personality recycled plastic jitni fake hai ♻️",
            "Tere face pe ban lagana chahiye 🚫",
            "Tera future itna dark hai sunglasses bhi nahi chalenge 😎",
            "Tu ek living proof hai ki evolution ulta bhi ho sakta hai 🦧",
            "Teri life ek error hai aur kiwi ne abhi tak debug nahi kiya 🐛",
            "Duniya ki sabse badi mistake — tera paida hona 🤮","Galat jawab aab to teri maa chudegi","Hum khade sarkar se bade,teri maa niche pade, hum teri maa ke bhosde pe chadhe","Bhai yrr galli dene mai hu thoda sa kacha, teri mummy ke bhosde mai land maar ke nikal du bacha!?","Laga aapne vidhwa maa ki boli teri mkc mai khelenge holi","Lohri hai lohra hai teri maa ka bhosda hai ","Kabhi kabhi tujhe dekhta hu to lagta hai kaash uss din teri maa ko chod ke maar hi deta, tere jaisa rndi ka bacha to nhi niklta","♾️Teri mkc mai lnd daal ke loop mode mai chala dunga"
        ]
        await event.edit(random.choice(roasts))

    @client.on(events.NewMessage(outgoing=True, pattern=rf"{P}ship\s+(\S+)\s+(\S+)"))
    async def ship_cmd(event):
        u1  = event.pattern_match.group(1)
        u2  = event.pattern_match.group(2)
        pct = random.randint(0, 100)
        bar = "❤️" * (pct // 10) + "🖤" * (10 - pct // 10)
        mood = "💍 Shaadi karo!" if pct > 80 else "💕 Accha hai!" if pct > 50 else "😬 Theek hai..." if pct > 30 else "💔 Mat karo bhai"
        await event.edit(f"💘 **{u1}** + **{u2}**\n{bar}\n**{pct}%** — {mood}")

# ════════════════════════════════════════════════════
#  USERBOT RUNNER
# ════════════════════════════════════════════════════

def get_client():
    if os.path.exists("session_string.txt"):
        with open("session_string.txt") as f:
            sess = f.read().strip()
        return TelegramClient(StringSession(sess), API_ID, API_HASH)
    return TelegramClient(SESSION_NAME, API_ID, API_HASH)

async def run_userbot():
    global userbot_client, userbot_running
    userbot_client = get_client()
    try:
        await userbot_client.connect()
        if not await userbot_client.is_user_authorized():
            print("❌ Session nahi hai — management bot se pehle login karo")
            return
        setup_userbot_handlers(userbot_client)
        me = await userbot_client.get_me()
        print(f"⚡ Userbot: {me.first_name} (@{me.username}) | v{BOT_VERSION}")
        userbot_running = True
        await userbot_client.run_until_disconnected()
    except Exception as e:
        print(f"❌ Userbot error: {e}")
    finally:
        userbot_running = False

def start_userbot_thread():
    global userbot_loop, userbot_thread
    def run():
        global userbot_loop
        userbot_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(userbot_loop)
        userbot_loop.run_until_complete(run_userbot())
    userbot_thread = threading.Thread(target=run, daemon=True)
    userbot_thread.start()

def stop_userbot_thread():
    global userbot_client, userbot_loop, userbot_running
    if userbot_loop and userbot_client:
        asyncio.run_coroutine_threadsafe(userbot_client.disconnect(), userbot_loop)
    userbot_running = False

# ════════════════════════════════════════════════════
#  MANAGEMENT BOT
# ════════════════════════════════════════════════════

login_state     = {}
temp_client_ref = [None]
temp_phone_ref  = [None]
temp_hash_ref   = [None]

def _main_kb():
    session_ok = os.path.exists("session_string.txt") or os.path.exists(f"{SESSION_NAME}.session")
    if session_ok:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Userbot Start", callback_data="start_bot"),
             InlineKeyboardButton("⏹ Userbot Stop",  callback_data="stop_bot")],
            [InlineKeyboardButton("📊 Status",        callback_data="status"),
             InlineKeyboardButton("🔑 Re-Login",      callback_data="login_phone")],
        ])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Phone se Login",  callback_data="login_phone")],
        [InlineKeyboardButton("🔗 String Session",  callback_data="login_session")],
    ])

async def mgmt_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("❌ Tum owner nahi ho!")
    login_state[OWNER_ID] = None
    session_ok = os.path.exists("session_string.txt") or os.path.exists(f"{SESSION_NAME}.session")
    txt = ("<b>⚡ kiwi USERBOT ▼・ᴥ・▼ — ULTRA kiwi MODE ⚡</b>\n\n✅ Session saved. Kya karna hai?"
           if session_ok else
           "<b>⚡ kiwi USERBOT ▼・ᴥ・▼ — ULTRA kiwi MODE ⚡</b>\n\nKoi session nahi. Pehle login karo:")
    await update.message.reply_text(txt, reply_markup=_main_kb(), parse_mode="HTML")

async def mgmt_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != OWNER_ID:
        return await query.answer("❌ Not owner!", show_alert=True)
    await query.answer()
    data = query.data

    if data == "start_bot":
        if userbot_running:
            return await query.edit_message_text("⚠️ Already chal raha hai!")
        session_ok = os.path.exists("session_string.txt") or os.path.exists(f"{SESSION_NAME}.session")
        if not session_ok:
            return await query.edit_message_text("❌ Pehle login karo! /start")
        start_userbot_thread()
        await query.edit_message_text(
            "✅ <b>Userbot start ho gaya!</b>\n\n<code>.help</code> ya <code>.menu</code> type karo.",
            parse_mode="HTML"
        )

    elif data == "stop_bot":
        stop_userbot_thread()
        await query.edit_message_text("⏹ <b>Userbot band ho gaya.</b>", parse_mode="HTML")

    elif data == "status":
        session_ok = os.path.exists("session_string.txt") or os.path.exists(f"{SESSION_NAME}.session")
        txt = (
            f"<b>📊 kiwi ▼・ᴥ・▼ STATUS</b>\n\n"
            f"{'🟢 Running' if userbot_running else '🔴 Stopped'} — Userbot\n"
            f"{'✅' if session_ok else '❌'} Session\n"
            f"🔥 Raids: <code>{len(raid_tasks)}</code>\n"
            f"💬 Cudega: <code>{len(cudega_tasks)}</code>\n"
            f"👁 Rndy: <code>{len(rndy_chats)}</code>\n"
            f"<b>API:</b> <code>{API_ID}</code>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data="status")],
            [InlineKeyboardButton("▶️ Start" if not userbot_running else "⏹ Stop",
                                  callback_data="start_bot" if not userbot_running else "stop_bot")],
        ])
        await query.edit_message_text(txt, reply_markup=kb, parse_mode="HTML")

    elif data == "login_phone":
        login_state[OWNER_ID] = "wait_phone"
        await query.edit_message_text(
            "📱 Phone number bhejo:\nExample: <code>+919876543210</code>\n\n❌ /cancel",
            parse_mode="HTML"
        )

    elif data == "login_session":
        login_state[OWNER_ID] = "wait_session"
        await query.edit_message_text(
            "🔗 <b>String Session</b> paste karo:\n\n❌ /cancel",
            parse_mode="HTML"
        )

async def mgmt_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    state = login_state.get(OWNER_ID)
    if not state: return
    text = update.message.text.strip()

    if state == "wait_phone":
        temp_phone_ref[0] = text
        c = TelegramClient(StringSession(), API_ID, API_HASH)
        temp_client_ref[0] = c
        await c.connect()
        try:
            sent = await c.send_code_request(text)
            temp_hash_ref[0] = sent.phone_code_hash
            login_state[OWNER_ID] = "wait_code"
            await update.message.reply_text(
                f"✅ OTP bheja: <code>{text}</code>\n\nOTP bhejo: <code>1 2 3 4 5</code>\n\n❌ /cancel",
                parse_mode="HTML"
            )
        except Exception as e:
            login_state[OWNER_ID] = None
            await update.message.reply_text(f"❌ <code>{e}</code>\n\n/start", parse_mode="HTML")

    elif state == "wait_code":
        code  = text.replace(" ", "")
        phone = temp_phone_ref[0]
        phash = temp_hash_ref[0]
        c     = temp_client_ref[0]
        try:
            await c.sign_in(phone=phone, code=code, phone_code_hash=phash)
            with open("session_string.txt", "w") as f:
                f.write(c.session.save())
            await c.disconnect()
            login_state[OWNER_ID] = None
            temp_hash_ref[0] = None
            await update.message.reply_text("✅ <b>Login ho gaya!</b>\n\n/start", parse_mode="HTML", reply_markup=_main_kb())
        except Exception as e:
            err = str(e)
            if "SessionPasswordNeeded" in err or "password" in err.lower():
                login_state[OWNER_ID] = "wait_password"
                await update.message.reply_text("🔐 2FA password bhejo:")
            elif "PhoneCodeExpired" in err or "expired" in err.lower():
                try:
                    sent2 = await c.send_code_request(phone)
                    temp_hash_ref[0] = sent2.phone_code_hash
                    login_state[OWNER_ID] = "wait_code"
                    await update.message.reply_text("⏰ Expire tha — <b>naya OTP aaya!</b>", parse_mode="HTML")
                except Exception as e2:
                    login_state[OWNER_ID] = None
                    await update.message.reply_text(f"❌ <code>{e2}</code>\n\n/start", parse_mode="HTML")
            elif "PhoneCodeInvalid" in err:
                await update.message.reply_text("❌ <b>Galat OTP!</b>", parse_mode="HTML")
            else:
                login_state[OWNER_ID] = None
                await update.message.reply_text(f"❌ <code>{e}</code>\n\n/start", parse_mode="HTML")

    elif state == "wait_password":
        c = temp_client_ref[0]
        try:
            await c.sign_in(password=text)
            with open("session_string.txt", "w") as f:
                f.write(c.session.save())
            await c.disconnect()
            login_state[OWNER_ID] = None
            await update.message.reply_text("✅ <b>2FA login!</b>\n\n/start", parse_mode="HTML", reply_markup=_main_kb())
        except Exception as e:
            await update.message.reply_text(f"❌ Wrong password: <code>{e}</code>", parse_mode="HTML")

    elif state == "wait_session":
        sess = text.strip()
        try:
            test = TelegramClient(StringSession(sess), API_ID, API_HASH)
            await test.connect()
            if await test.is_user_authorized():
                await test.disconnect()
                with open("session_string.txt", "w") as f:
                    f.write(sess)
                login_state[OWNER_ID] = None
                await update.message.reply_text("✅ <b>Session saved!</b>\n\n/start", parse_mode="HTML", reply_markup=_main_kb())
            else:
                await test.disconnect()
                await update.message.reply_text("❌ Invalid session!")
        except Exception as e:
            login_state[OWNER_ID] = None
            await update.message.reply_text(f"❌ <code>{e}</code>", parse_mode="HTML")

async def mgmt_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    login_state[OWNER_ID] = None
    if temp_client_ref[0]:
        try: await temp_client_ref[0].disconnect()
        except: pass
        temp_client_ref[0] = None
    await update.message.reply_text("❌ Cancelled.", reply_markup=_main_kb())

# ════════════════════════════════════════════════════
#  MAIN ENTRY
# ════════════════════════════════════════════════════

def main():
    print("╔══════════════════════════════════════════╗")
    print("║  ⚡ kiwi USERBOT ▼・ᴥ・▼ — ULTRA kiwi MODE ⚡  ║")
    print("║      70+ Commands | Max Speed | Beast     ║")
    print("╚══════════════════════════════════════════╝")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", mgmt_start))
    app.add_handler(CommandHandler("cancel", mgmt_cancel))
    app.add_handler(CallbackQueryHandler(mgmt_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mgmt_message))
    print("✅ Management bot ready! Telegram mein /start bhejo.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
