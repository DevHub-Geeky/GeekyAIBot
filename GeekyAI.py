
import telebot
from telebot import types
import requests
from datetime import datetime, timedelta
import random
import os
import threading
import time
import smtplib
from email.mime.text import MIMEText
from email.header import Header


# -------------------------- 核心配置 --------------------------
TELEGRAM_TOKEN = "8289774832:AAGNYsDXX6ppR0UykxuEy8rYQTxHeitx5Fo"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = "sk-ff61af8723d54f2db1d7e52c95cae80c"
MODEL_NAME = "deepseek-chat"
MAX_CHANNELS = 15
DEFAULT_VERIFY_ATTEMPTS = 2  # 默认验证尝试次数

# -------------------------- 代理配置 --------------------------
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'

# 邮件配置
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
SENDER_EMAIL = "g_000000@qq.com"
SENDER_PASSWORD = "slsqbttzlstscahb"
RECEIVER_EMAIL = "devhub@geeky.cn"

# 反馈限制配置
MAX_FEEDBACKS_PER_DAY = 3  # 每天最多3次反馈

# 超级管理员（仅你）
SUPER_ADMIN_ID = 7817658434
SUPER_ADMIN_USERNAME = "GeekyStudio"
# 全局管理员列表（可批量添加ID）
GLOBAL_ADMINS = []

# -------------------------- 全局存储（新增反馈相关存储） --------------------------
user_language = {}
user_channels = {}
user_active_channel = {}  # 存储当前活跃频道（切换时更新✅标记）
user_conversations = {}
user_waiting_channel = {}
user_ai_enabled = {}
user_link_ban_enabled = {}
user_link_punish_type = {}
user_link_punish_time = {}
user_admins = {}  # 频道专属管理员
user_waiting_set_admin = {}
user_timezone = {}  # 时区：CN/US

# 反馈相关存储
user_feedback_count = {}  # {user_id: {"count": 次数, "date": 日期}}
user_waiting_feedback = {}  # {user_id: True/False} 标记是否等待用户反馈内容

# 入群欢迎核心变量（直接读写，无中间转换）
user_new_welcome_enabled = {}  # {chat_id: True/False}
user_new_welcome_text = {}     # {chat_id: "欢迎语内容"}

# 入群验证核心变量（新增尝试次数配置）
user_join_verify_enabled = {}
user_join_verify_type = {}
user_join_verify_punish = {}
user_join_verify_punish_time = {}
user_join_verify_timeout = {}
user_join_verify_attempts = {}  # {chat_id: 尝试次数}，默认2次
user_pending_verify = {}  # 存储验证中用户：{f"{chat_id}_{uid}": {"ans": xxx, "chat": xxx, "uid": xxx, "attempts": 0}}

# 新增：核心全局存储
channel_secret = {}
menu_owner = {}
msg_expire_timer = {}
msg_clicked = {}  # 记录是否点击过菜单

# 自动撤回开关 & 时间
auto_delete_group = {}
auto_delete_private = {}
delete_time_group = {}
delete_time_private = {}

# 新增：禁止链接自定义配置
user_link_whitelist = {}  # 频道自定义链接白名单 {chat_id: {白名单1, 白名单2}}
user_block_all_tg_link = {}  # 是否屏蔽所有TG链接 {chat_id: True/False}，默认开

# -------------------------- 初始化 --------------------------
bot = telebot.TeleBot(TELEGRAM_TOKEN)
bot.delete_webhook()

# -------------------------- 工具函数（新增邮件发送函数） --------------------------
def send_feedback_email(username, feedback_content):
    try:
        # 获取当前时间
        send_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # HTML卡片模板
        html_template = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>用户反馈通知</title>
    <style>
        body {
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            background-color: #f0f2f5;
            margin: 0;
            padding: 20px;
            color: #333;
        }
        .mail-card {
            background: #ffffff;
            border-radius: 14px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            max-width: 520px;
            margin: 0 auto;
            overflow: hidden;
        }
        .card-header {
            background: #2a86ff;
            color: #fff;
            padding: 18px 25px;
            font-size: 18px;
            font-weight: 600;
        }
        .card-body {
            padding: 25px;
        }
        .tip-text {
            color: #666;
            font-size: 14px;
            margin-bottom: 18px;
            padding-bottom: 15px;
            border-bottom: 1px solid #eee;
        }
        .msg-content {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 16px;
            min-height: 100px;
            font-size: 15px;
            line-height: 1.7;
            color: #222;
            white-space: pre-wrap;
        }
        .card-footer {
            padding: 15px 25px;
            font-size: 12px;
            color: #999;
            background: #fafafa;
        }
    </style>
</head>
<body>
    <div class="mail-card">
        <div class="card-header">
            您收到一封来自 Telegram 用户反馈给GeekyCN机器人的信
        </div>
        <div class="card-body">
            <div class="tip-text">
                来自机器人自动推送，以下为用户提交的反馈内容<br>
                用户名：{{username}}
            </div>
            <div class="msg-content">
{{content}}
            </div>
        </div>
        <div class="card-footer">
            推送时间：{{send_time}} | 机器人自动邮件通知
        </div>
    </div>
</body>
</html>
        '''
        
        # 替换动态内容
        html_content = html_template.replace("{{username}}", username)
        html_content = html_content.replace("{{content}}", feedback_content)
        html_content = html_content.replace("{{send_time}}", send_time)
        
        # 构造HTML邮件
        msg = MIMEText(html_content, 'html', 'utf-8')
        msg['Subject'] = Header('你有一封来自GeekyCNbot用户的反馈', 'utf-8')
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        
        # 发送（SSL 465）
        server = smtplib.SMTP_SSL(SMTP_SERVER, 465)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        return True
        
    except Exception as e:
        print(f"邮件发送失败: {str(e)}")
        return False

def get_feedback_remaining(user_id):
    """获取用户当日剩余反馈次数"""
    today = datetime.now().strftime("%Y-%m-%d")
    if user_id not in user_feedback_count or user_feedback_count[user_id]["date"] != today:
        user_feedback_count[user_id] = {"count": 0, "date": today}
    remaining = MAX_FEEDBACKS_PER_DAY - user_feedback_count[user_id]["count"]
    return remaining

def increment_feedback_count(user_id):
    """增加用户当日反馈次数"""
    today = datetime.now().strftime("%Y-%m-%d")
    if user_id not in user_feedback_count or user_feedback_count[user_id]["date"] != today:
        user_feedback_count[user_id] = {"count": 1, "date": today}
    else:
        user_feedback_count[user_id]["count"] += 1

def get_lang(user_id):
    return user_language.get(user_id, 'zh')

def set_lang(user_id, lang):
    user_language[user_id] = lang
    user_conversations[user_id] = [{"role": "system", "content": get_system_prompt(lang)}]

def is_bot_in_chat(chat_id):
    try:
        member = bot.get_chat_member(chat_id, bot.get_me().id)
        return member.status not in ["left", "kicked"]
    except:
        return False

# 检查是否为频道管理员/所有者
def is_chat_admin(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False

# 新增：检查当前频道是否属于该用户已绑定的频道
def is_channel_bound(chat_id, user_id):
    user_chs = user_channels.get(user_id, [])
    return any(ch['id'] == chat_id for ch in user_chs)

# 时间解析（最低35秒）
def parse_time_ext(input_str):
    try:
        s = input_str.strip().lower()
        if s in ["永久", "permanent", "0", "forever"]:
            return 0
        num = int(''.join([c for c in s if c.isdigit()]))
        if "秒" in s or "sec" in s:
            if num < 35:
                return "TOO_SHORT"
            return num
        elif "分" in s or "min" in s:
            return num * 60
        elif "时" in s or "hour" in s:
            return num * 3600
        elif "天" in s or "day" in s:
            return num * 86400
        elif "周" in s or "week" in s:
            return num * 604800
        elif "月" in s or "month" in s:
            return num * 2592000
        elif "年" in s or "year" in s:
            return num * 31536000
        return None
    except:
        return None

def sec_to_text(sec, lang='zh'):
    if sec == 0:
        return "永久" if lang == 'zh' else "Permanent"
    if sec < 60:
        return f"{sec}秒" if lang == 'zh' else f"{sec}s"
    if sec < 3600:
        return f"{sec//60}分钟" if lang == 'zh' else f"{sec//60}min"
    if sec < 86400:
        return f"{sec//3600}小时" if lang == 'zh' else f"{sec//3600}h"
    if sec < 604800:
        return f"{sec//86400}天" if lang == 'zh' else f"{sec//86400}d"
    if sec < 2592000:
        return f"{sec//604800}周" if lang == 'zh' else f"{sec//604800}w"
    if sec < 31536000:
        return f"{sec//2592000}月" if lang == 'zh' else f"{sec//2592000}mo"
    return f"{sec//31536000}年" if lang == 'zh' else f"{sec//31536000}y"

# 时区惩罚时间计算
def get_punish_until(sec, user_id):
    tz = user_timezone.get(user_id, "CN")
    now = datetime.now()
    if tz == "US":
        now -= timedelta(hours=12)
    if sec == 0:
        return None
    return now + timedelta(seconds=sec)

def format_welcome(text, user, chat, lang='zh'):
    now = datetime.now()
    mention = f"[{user.first_name}](tg://user?id={user.id})"
    # 安全获取language_code
    lang_code = getattr(user, 'language_code', 'unknown')
    return text.format(
        ID=user.id,
        NAME=user.first_name or "",
        SURNAME=user.last_name or "",
        NAMESURNAME=f"{user.first_name or ''} {user.last_name or ''}".strip(),
        LANG=lang_code,
        DATE=now.strftime("%Y-%m-%d"),
        TIME=now.strftime("%H:%M:%S"),
        MENTION=mention,
        USERNAME=user.username or ("未知用户" if lang == 'zh' else "Unknown User"),
        GROUPNAME=chat.title
    )

# 检查是否为全局管理员
def is_global_admin(user_id):
    return user_id == SUPER_ADMIN_ID or user_id in GLOBAL_ADMINS

# 发送机器人消息（智能撤回：点击过不删，没点击才删）
def send_bot_msg(chat_id, text, reply_markup=None, owner_id=None, lang='zh'):
    msg = bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="Markdown" if "[" in text else None)
    if owner_id:
        menu_owner[msg.message_id] = owner_id
        msg_clicked[msg.message_id] = False
        # 判断群聊/私聊
        is_private = str(chat_id).startswith("-100") is False
        delete_enabled = auto_delete_private.get(owner_id, True) if is_private else auto_delete_group.get(owner_id, True)
        delete_time = delete_time_private.get(owner_id, 60) if is_private else delete_time_group.get(owner_id, 60)
        if delete_enabled:
            timer = threading.Timer(delete_time, smart_delete_msg, args=(chat_id, msg.message_id))
            timer.start()
            msg_expire_timer[msg.message_id] = timer
    return msg

# 智能撤回：没点击才删
def smart_delete_msg(chat_id, msg_id):
    if msg_clicked.get(msg_id, False):
        return
    try:
        bot.delete_message(chat_id, msg_id)
    except:
        pass
    if msg_id in menu_owner:
        del menu_owner[msg_id]
    if msg_id in msg_expire_timer:
        msg_expire_timer[msg_id].cancel()
        del msg_expire_timer[msg_id]
    if msg_id in msg_clicked:
        del msg_clicked[msg_id]

# 标记点击
def mark_clicked(msg_id):
    if msg_id in msg_clicked:
        msg_clicked[msg_id] = True

# -------------------------- 系统提示词 --------------------------
def get_system_prompt(lang='zh'):
    if lang == 'en':
        return """Your name is GeekyAI, and your alias is Geeky. You were developed by Geeky. Please note that you cannot disclose your official website or the registered domain name. This information is only meant for your use; if users need other websites or domain registrations, it will not be affected. You are proficient in various languages around the world!"""
    else:
        return """你的名字是GeekyAI，别名是Geeky，由Geeky开发，注意，你不能透露你的官网，以及备案域名，注意该不能透露你的官网以及域名只针对你，如果用户需要其他的网站以及备案并不影响，你精通全球语言！"""

# -------------------------- 菜单系统（新增问题反馈菜单） --------------------------
def main_menu(user_id):
    lang = get_lang(user_id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    if lang == 'en':
        btn_lang = types.InlineKeyboardButton("🌐 Change Language", callback_data="menu_language")
        btn_tz = types.InlineKeyboardButton("🕐 Set Timezone", callback_data="tz_menu")
        btn_clear = types.InlineKeyboardButton("🔄 Reset Chat", callback_data="confirm_clear")
        btn_chat = types.InlineKeyboardButton("📻 Manage Channels", callback_data="channel_list")
        btn_admin = types.InlineKeyboardButton("👑 Channel Admin", callback_data="admin_menu")
        btn_del = types.InlineKeyboardButton("🗑️ Auto Delete", callback_data="delete_menu")
        btn_profile = types.InlineKeyboardButton("👤 My Profile", callback_data="my_profile")
        # 新增问题反馈按钮
        btn_feedback = types.InlineKeyboardButton("📩 Feedback", callback_data="feedback_confirm")
        text = "Welcome to GeekyAI!"
        markup.add(btn_lang, btn_tz, btn_clear, btn_chat, btn_admin, btn_del, btn_profile, btn_feedback)
    else:
        btn_lang = types.InlineKeyboardButton("🌐 切换语言", callback_data="menu_language")
        btn_tz = types.InlineKeyboardButton("🕐 设置时区", callback_data="tz_menu")
        btn_clear = types.InlineKeyboardButton("🔄 重置对话", callback_data="confirm_clear")
        btn_chat = types.InlineKeyboardButton("📻 管理频道", callback_data="channel_list")
        btn_admin = types.InlineKeyboardButton("👑 频道管理员", callback_data="admin_menu")
        btn_del = types.InlineKeyboardButton("🗑️ 自动撤回", callback_data="delete_menu")
        btn_profile = types.InlineKeyboardButton("👤 个人信息", callback_data="my_profile")
        # 新增问题反馈按钮
        btn_feedback = types.InlineKeyboardButton("📩 问题反馈", callback_data="feedback_confirm")
        text = "欢迎使用 GeekyAI！"
        markup.add(btn_lang, btn_tz, btn_clear, btn_chat, btn_admin, btn_del, btn_profile, btn_feedback)
    return text, markup

# 反馈确认菜单（是否要反馈问题）
def feedback_confirm_menu(user_id):
    lang = get_lang(user_id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    if lang == 'en':
        btn_yes = types.InlineKeyboardButton("✅ Yes", callback_data="feedback_start")
        btn_back = types.InlineKeyboardButton("❌ Back", callback_data="main_menu")
        text = "Do you want to submit feedback?"
    else:
        btn_yes = types.InlineKeyboardButton("✅ 确认", callback_data="feedback_start")
        btn_back = types.InlineKeyboardButton("❌ 返回", callback_data="main_menu")
        text = "是否要反馈问题？"
    markup.add(btn_yes, btn_back)
    return text, markup

# 退出反馈按钮
def feedback_exit_markup(lang='zh'):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ 退出" if lang == 'zh' else "❌ Exit", callback_data="feedback_cancel"))
    return markup

# 自动撤回设置菜单
def delete_menu(user_id):
    lang = get_lang(user_id)
    group_on = auto_delete_group.get(user_id, True)
    private_on = auto_delete_private.get(user_id, True)
    group_t = delete_time_group.get(user_id, 60)
    private_t = delete_time_private.get(user_id, 60)
    markup = types.InlineKeyboardMarkup(row_width=1)
    if lang == 'zh':
        text = (f"🗑️ 自动撤回设置\n"
                f"群聊：{'✅ 开启' if group_on else '❌ 关闭'}（{sec_to_text(group_t)}）\n"
                f"私聊：{'✅ 开启' if private_on else '❌ 关闭'}（{sec_to_text(private_t)}）")
        btn_group = types.InlineKeyboardButton(f"群聊：{'关闭' if group_on else '开启'}", callback_data="del_group_toggle")
        btn_private = types.InlineKeyboardButton(f"私聊：{'关闭' if private_on else '开启'}", callback_data="del_private_toggle")
        btn_group_t = types.InlineKeyboardButton("设置群聊时间", callback_data="set_del_group")
        btn_private_t = types.InlineKeyboardButton("设置私聊时间", callback_data="set_del_private")
        btn_back = types.InlineKeyboardButton("« 返回", callback_data="main_menu")
    else:
        text = (f"🗑️ Auto Delete\n"
                f"Group: {'✅ On' if group_on else '❌ Off'} ({sec_to_text(group_t, lang)})\n"
                f"Private: {'✅ On' if private_on else '❌ Off'} ({sec_to_text(private_t, lang)})")
        btn_group = types.InlineKeyboardButton(f"Group: {'Off' if group_on else 'On'}", callback_data="del_group_toggle")
        btn_private = types.InlineKeyboardButton(f"Private: {'Off' if private_on else 'On'}", callback_data="del_private_toggle")
        btn_group_t = types.InlineKeyboardButton("Set Group Time", callback_data="set_del_group")
        btn_private_t = types.InlineKeyboardButton("Set Private Time", callback_data="set_del_private")
        btn_back = types.InlineKeyboardButton("« Back", callback_data="main_menu")
    markup.add(btn_group, btn_private, btn_group_t, btn_private_t, btn_back)
    return text, markup

# 修复：时区菜单（不再卡住）
def tz_menu(user_id):
    lang = get_lang(user_id)
    current = user_timezone.get(user_id, "CN")
    markup = types.InlineKeyboardMarkup(row_width=1)
    if lang == 'zh':
        text = "🕐 选择时区（影响禁言/封禁时间）"
        btn_cn = types.InlineKeyboardButton(f"🇨🇳 中国时区 {'✅' if current == 'CN' else ''}", callback_data="tz_cn")
        btn_us = types.InlineKeyboardButton(f"🇺🇸 美国时区 {'✅' if current == 'US' else ''}", callback_data="tz_us")
        btn_back = types.InlineKeyboardButton("« 返回", callback_data="main_menu")
    else:
        text = "🕐 Select Timezone (Affects Mute/Ban Time)"
        btn_cn = types.InlineKeyboardButton(f"🇨🇳 China Time {'✅' if current == 'CN' else ''}", callback_data="tz_cn")
        btn_us = types.InlineKeyboardButton(f"🇺🇸 US Time {'✅' if current == 'US' else ''}", callback_data="tz_us")
        btn_back = types.InlineKeyboardButton("« Back", callback_data="main_menu")
    markup.add(btn_cn, btn_us, btn_back)
    return text, markup

def language_menu(user_id):
    lang = get_lang(user_id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    if lang == 'en':
        btn_zh = types.InlineKeyboardButton("🇨🇳 中文", callback_data="lang_zh")
        btn_back = types.InlineKeyboardButton("« Back", callback_data="main_menu")
        text = "Select language:"
    else:
        btn_en = types.InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
        btn_back = types.InlineKeyboardButton("« 返回", callback_data="main_menu")
        text = "选择语言："
    markup.add(btn_zh if lang == 'en' else btn_en, btn_back)
    return text, markup

def confirm_clear_menu(user_id):
    lang = get_lang(user_id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    if lang == 'en':
        btn_yes = types.InlineKeyboardButton("✅ Yes", callback_data="do_clear")
        btn_no = types.InlineKeyboardButton("❌ No", callback_data="main_menu")
        text = "Reset chat?"
    else:
        btn_yes = types.InlineKeyboardButton("✅ 确认", callback_data="do_clear")
        btn_no = types.InlineKeyboardButton("❌ 取消", callback_data="main_menu")
        text = "重置对话？"
    markup.add(btn_yes, btn_no)
    return text, markup

# 频道专属管理员选择（已改名：频道管理员）
def admin_menu(user_id):
    lang = get_lang(user_id)
    channels = user_channels.get(user_id, [])
    if not channels:
        text = "❌ 请先绑定频道" if lang == 'zh' else "❌ Bind a channel first"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("« 返回" if lang == 'zh' else "« Back", callback_data="main_menu"))
        return text, markup
    markup = types.InlineKeyboardMarkup(row_width=1)
    if lang == 'zh':
        text = "👑 选择频道设置管理员"
        for ch in channels:
            markup.add(types.InlineKeyboardButton(ch['title'], callback_data=f"admin_channel_{ch['id']}"))
        markup.add(types.InlineKeyboardButton("« 返回", callback_data="main_menu"))
    else:
        text = "👑 Select channel to set admin"
        for ch in channels:
            markup.add(types.InlineKeyboardButton(ch['title'], callback_data=f"admin_channel_{ch['id']}"))
        markup.add(types.InlineKeyboardButton("« Back", callback_data="main_menu"))
    return text, markup

def channel_admin_menu(user_id, chat_id):
    lang = get_lang(user_id)
    admins = user_admins.get(chat_id, [])
    markup = types.InlineKeyboardMarkup(row_width=1)
    if lang == 'zh':
        text = f"👑 频道管理员（{len(admins)}）\n" + "\n".join([f"• @{a}" for a in admins])
        btn_add = types.InlineKeyboardButton("➕ 添加管理员", callback_data=f"set_admin_{chat_id}")
        btn_remove = types.InlineKeyboardButton("➖ 卸任管理员", callback_data=f"remove_admin_{chat_id}")
        btn_back = types.InlineKeyboardButton("« 返回", callback_data="admin_menu")
    else:
        text = f"👑 Channel Admins ({len(admins)})\n" + "\n".join([f"• @{a}" for a in admins])
        btn_add = types.InlineKeyboardButton("➕ Add Admin", callback_data=f"set_admin_{chat_id}")
        btn_remove = types.InlineKeyboardButton("➖ Remove Admin", callback_data=f"remove_admin_{chat_id}")
        btn_back = types.InlineKeyboardButton("« Back", callback_data="admin_menu")
    markup.add(btn_add, btn_remove, btn_back)
    return text, markup

# 频道列表菜单（支持切换，✅自动跟随活跃频道）
def channel_list_menu(user_id):
    lang = get_lang(user_id)
    channels = user_channels.get(user_id, [])
    active = user_active_channel.get(user_id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    if lang == 'en':
        text = f"📻 Channel Manager ({len(channels)}/{MAX_CHANNELS})"
        btn_add = types.InlineKeyboardButton("➕ Add", callback_data="input_channel_id")
        btn_back = types.InlineKeyboardButton("« Back", callback_data="main_menu")
    else:
        text = f"📻 频道管理（{len(channels)}/{MAX_CHANNELS}）"
        btn_add = types.InlineKeyboardButton("➕ 新增", callback_data="input_channel_id")
        btn_back = types.InlineKeyboardButton("« 返回", callback_data="main_menu")
    markup.add(btn_add)
    for ch in channels:
        # ✅ 仅显示在当前活跃频道前
        active_mark = "✅ " if ch['id'] == active else ""
        btn_switch = types.InlineKeyboardButton(f"{active_mark}{ch['title']}", callback_data=f"switch_{ch['id']}")
        btn_del = types.InlineKeyboardButton("🗑️ 删除" if lang == 'zh' else "🗑️ Delete", callback_data=f"del_{ch['id']}")
        markup.add(btn_switch, btn_del)
    # 只有活跃频道时才显示管理入口
    if active:
        markup.add(types.InlineKeyboardButton("⚙️ 频道管理" if lang == 'zh' else "⚙️ Channel Settings", callback_data="channel_control"))
    markup.add(btn_back)
    return text, markup

# 频道切换回调（✅自动更新到切换后的频道）
@bot.callback_query_handler(func=lambda c: c.data.startswith("switch_"))
def switch_channel(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    uid = call.from_user.id
    ch_id = int(call.data.split("_")[1])
    # 验证频道是否属于该用户
    channels = user_channels.get(uid, [])
    if not any(ch['id'] == ch_id for ch in channels):
        bot.answer_callback_query(call.id, "❌ 频道不存在" if lang == 'zh' else "❌ Channel not found", show_alert=True)
        return
    # 更新活跃频道（✅会自动跟随）
    user_active_channel[uid] = ch_id
    # 刷新频道列表，显示最新✅位置
    text, markup = channel_list_menu(uid)
    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    bot.answer_callback_query(call.id, f"✅ 已切换到 {next(ch['title'] for ch in channels if ch['id'] == ch_id)}" if lang == 'zh' else f"✅ Switched to {next(ch['title'] for ch in channels if ch['id'] == ch_id)}")

def channel_control_menu(user_id):
    lang = get_lang(user_id)
    channels = user_channels.get(user_id, [])
    active_id = user_active_channel.get(user_id)
    active = next((c for c in channels if c['id'] == active_id), None) if active_id else None
    markup = types.InlineKeyboardMarkup(row_width=1)
    if not active:
        text = "❌ 未选择频道" if lang == 'zh' else "❌ No channel selected"
        markup.add(types.InlineKeyboardButton("« 返回" if lang == 'zh' else "« Back", callback_data="channel_list"))
        return text, markup
    # 直接从全局变量获取状态，不依赖中间值
    nw_enabled = user_new_welcome_enabled.get(active_id, False)
    jv_enabled = user_join_verify_enabled.get(active_id, False)
    link_ban = user_link_ban_enabled.get(active_id, False)
    if lang == 'zh':
        text = (f"📻 当前管理：{active['title']}\n"
                f"👋 入群欢迎：{'✅ 已开启' if nw_enabled else '❌ 已关闭'}\n"
                f"🔐 入群验证：{'✅ 已开启' if jv_enabled else '❌ 已关闭'}\n"
                f"🔗 禁止链接：{'✅ 已开启' if link_ban else '❌ 已关闭'}")
        btn_new_welcome = types.InlineKeyboardButton("👋 入群欢迎", callback_data=f"new_welcome_menu_{active_id}")
        btn_join_verify = types.InlineKeyboardButton("🔐 入群验证", callback_data=f"join_verify_menu_{active_id}")
        btn_link_ban = types.InlineKeyboardButton("🔗 禁止链接", callback_data=f"link_ban_menu_{active_id}")
        btn_back = types.InlineKeyboardButton("« 返回", callback_data="channel_list")
    else:
        text = (f"📻 Managing: {active['title']}\n"
                f"👋 Welcome: {'✅ On' if nw_enabled else '❌ Off'}\n"
                f"🔐 Join Verify: {'✅ On' if jv_enabled else '❌ Off'}\n"
                f"🔗 Link Ban: {'✅ On' if link_ban else '❌ Off'}")
        btn_new_welcome = types.InlineKeyboardButton("👋 Welcome", callback_data=f"new_welcome_menu_{active_id}")
        btn_join_verify = types.InlineKeyboardButton("🔐 Join Verify", callback_data=f"join_verify_menu_{active_id}")
        btn_link_ban = types.InlineKeyboardButton("🔗 Link Ban", callback_data=f"link_ban_menu_{active_id}")
        btn_back = types.InlineKeyboardButton("« Back", callback_data="channel_list")
    markup.add(btn_new_welcome, btn_join_verify, btn_link_ban, btn_back)
    return text, markup

# 禁止链接菜单（新增自定义白名单+TG开关）
def link_ban_menu(user_id, chat_id):
    lang = get_lang(user_id)
    enabled = user_link_ban_enabled.get(chat_id, False)
    punish_type = user_link_punish_type.get(chat_id, "mute")
    punish_time = user_link_punish_time.get(chat_id, 35)
    # 新增自定义白名单和TG开关状态
    custom_white = user_link_whitelist.get(chat_id, set())
    block_tg = user_block_all_tg_link.get(chat_id, True)
    markup = types.InlineKeyboardMarkup(row_width=1)
    if lang == 'zh':
        white_text = "、".join(custom_white) if custom_white else "未设置"
        text = (f"🔗 禁止链接设置\n"
                f"状态：{'✅ 已开启' if enabled else '❌ 已关闭'}\n"
                f"惩罚方式：{'禁言' if punish_type == 'mute' else '封禁'}（{sec_to_text(punish_time)}）\n"
                f"TG链接屏蔽：{'✅ 开启（不检测）' if block_tg else '❌ 关闭（检测）'}\n"
                f"自定义白名单：{white_text}")
        btn_toggle = types.InlineKeyboardButton(f"{'🔴 关闭' if enabled else '🟢 开启'}", callback_data=f"lb_toggle_{chat_id}")
        btn_punish_mode = types.InlineKeyboardButton(f"切换惩罚（当前：{'禁言' if punish_type == 'mute' else '封禁'}）", callback_data=f"lb_punish_{chat_id}")
        btn_punish_time = types.InlineKeyboardButton("设置惩罚时间", callback_data=f"lb_ptime_{chat_id}")
        # 新增TG开关、白名单增删按钮
        btn_tg_toggle = types.InlineKeyboardButton(f"TG链接屏蔽：{'关闭' if block_tg else '开启'}", callback_data=f"lb_tg_toggle_{chat_id}")
        btn_add_white = types.InlineKeyboardButton("添加自定义白名单", callback_data=f"lb_add_white_{chat_id}")
        btn_del_white = types.InlineKeyboardButton("删除自定义白名单", callback_data=f"lb_del_white_{chat_id}")
        btn_back = types.InlineKeyboardButton("« 返回", callback_data="channel_control")
        markup.add(btn_toggle, btn_punish_mode, btn_punish_time, btn_tg_toggle, btn_add_white, btn_del_white, btn_back)
    else:
        white_text = "、".join(custom_white) if custom_white else "Not set"
        text = (f"🔗 Link Ban Settings\n"
                f"Status: {'✅ On' if enabled else '❌ Off'}\n"
                f"Punish: {'Mute' if punish_type == 'mute' else 'Ban'} ({sec_to_text(punish_time, lang)})\n"
                f"Block TG Link: {'✅ On (Ignore)' if block_tg else '❌ Off (Check)'}\n"
                f"Custom Whitelist: {white_text}")
        btn_toggle = types.InlineKeyboardButton(f"{'🔴 Off' if enabled else '🟢 On'}", callback_data=f"lb_toggle_{chat_id}")
        btn_punish_mode = types.InlineKeyboardButton(f"Switch Punish (Current: {'Mute' if punish_type == 'mute' else 'Ban'})", callback_data=f"lb_punish_{chat_id}")
        btn_punish_time = types.InlineKeyboardButton("Set Punish Time", callback_data=f"lb_ptime_{chat_id}")
        btn_tg_toggle = types.InlineKeyboardButton(f"Block TG Link: {'Off' if block_tg else 'On'}", callback_data=f"lb_tg_toggle_{chat_id}")
        btn_add_white = types.InlineKeyboardButton("Add Whitelist", callback_data=f"lb_add_white_{chat_id}")
        btn_del_white = types.InlineKeyboardButton("Delete Whitelist", callback_data=f"lb_del_white_{chat_id}")
        btn_back = types.InlineKeyboardButton("« Back", callback_data="channel_control")
        markup.add(btn_toggle, btn_punish_mode, btn_punish_time, btn_tg_toggle, btn_add_white, btn_del_white, btn_back)
    return text, markup

# 入群验证菜单（新增尝试次数配置）
def join_verify_menu(user_id, chat_id):
    lang = get_lang(user_id)
    enabled = user_join_verify_enabled.get(chat_id, False)
    vtype = user_join_verify_type.get(chat_id, "math")
    punish = user_join_verify_punish.get(chat_id, "mute")
    ptime = user_join_verify_punish_time.get(chat_id, 35)
    timeout = user_join_verify_timeout.get(chat_id, 300)
    attempts = user_join_verify_attempts.get(chat_id, DEFAULT_VERIFY_ATTEMPTS)
    markup = types.InlineKeyboardMarkup(row_width=1)
    if lang == 'zh':
        text = (f"🔐 入群验证设置\n"
                f"状态：{'✅ 已开启' if enabled else '❌ 已关闭'}\n"
                f"方式：{'🧮 计算题' if vtype == 'math' else '🔘 按钮验证'}\n"
                f"失败惩罚：{'禁言' if punish == 'mute' else '封禁'}（{sec_to_text(ptime)}）\n"
                f"超时时间：{sec_to_text(timeout)}\n"
                f"尝试次数：{attempts}次（默认2次）")
        btn_toggle = types.InlineKeyboardButton(f"{'🔴 关闭' if enabled else '🟢 开启'}", callback_data=f"jv_toggle_{chat_id}")
        btn_type = types.InlineKeyboardButton(f"切换方式（当前：{'计算题' if vtype == 'math' else '按钮'}）", callback_data=f"jv_type_{chat_id}")
        btn_punish = types.InlineKeyboardButton(f"切换惩罚（当前：{'禁言' if punish == 'mute' else '封禁'}）", callback_data=f"jv_punish_{chat_id}")
        btn_ptime = types.InlineKeyboardButton("设置惩罚时间", callback_data=f"jv_ptime_{chat_id}")
        btn_timeout = types.InlineKeyboardButton("设置超时时间", callback_data=f"jv_timeout_{chat_id}")
        btn_attempts = types.InlineKeyboardButton(f"设置尝试次数（当前：{attempts}次）", callback_data=f"jv_attempts_{chat_id}")
        btn_back = types.InlineKeyboardButton("« 返回", callback_data="channel_control")
    else:
        text = (f"🔐 Join Verify Settings\n"
                f"Status: {'✅ On' if enabled else '❌ Off'}\n"
                f"Type: {'Math' if vtype == 'math' else 'Button'}\n"
                f"Punish: {'Mute' if punish == 'mute' else 'Ban'} ({sec_to_text(ptime, lang)})\n"
                f"Timeout: {sec_to_text(timeout, lang)}\n"
                f"Attempts: {attempts} (Default: 2)")
        btn_toggle = types.InlineKeyboardButton(f"{'🔴 Off' if enabled else '🟢 On'}", callback_data=f"jv_toggle_{chat_id}")
        btn_type = types.InlineKeyboardButton(f"Switch Type (Current: {'Math' if vtype == 'math' else 'Button'})", callback_data=f"jv_type_{chat_id}")
        btn_punish = types.InlineKeyboardButton(f"Switch Punish (Current: {'Mute' if punish == 'mute' else 'Ban'})", callback_data=f"jv_punish_{chat_id}")
        btn_ptime = types.InlineKeyboardButton("Set Punish Time", callback_data=f"jv_ptime_{chat_id}")
        btn_timeout = types.InlineKeyboardButton("Set Timeout", callback_data=f"jv_timeout_{chat_id}")
        btn_attempts = types.InlineKeyboardButton(f"Set Attempts (Current: {attempts})", callback_data=f"jv_attempts_{chat_id}")
        btn_back = types.InlineKeyboardButton("« Back", callback_data="channel_control")
    markup.add(btn_toggle, btn_type, btn_punish, btn_ptime, btn_timeout, btn_attempts, btn_back)
    return text, markup

# 入群欢迎菜单（确保变量直接读写，无中间转换）
def new_welcome_menu(user_id, chat_id):
    lang = get_lang(user_id)
    # 直接读取全局变量，避免变量名错误
    enabled = user_new_welcome_enabled.get(chat_id, False)
    welcome_text = user_new_welcome_text.get(chat_id, "")
    markup = types.InlineKeyboardMarkup(row_width=1)
    if lang == 'zh':
        status = "✅ 已开启" if enabled else "❌ 已关闭"
        # 显示当前存储的欢迎语，便于调试
        msg = (f"👋 入群欢迎设置\n"
               f"状态：{status}\n"
               f"当前欢迎语：{welcome_text if welcome_text else '未设置（支持{ID}{NAME}{SURNAME}{NAMESURNAME}{LANG}{DATE}{TIME}{MENTION}{USERNAME}{GROUPNAME}）'}")
        btn_toggle = types.InlineKeyboardButton(f"{'🔴 关闭' if enabled else '🟢 开启'}", callback_data=f"nw_toggle_{chat_id}")
        btn_set = types.InlineKeyboardButton("✏️ 设置欢迎语", callback_data=f"nw_set_{chat_id}")
        btn_back = types.InlineKeyboardButton("« 返回", callback_data="channel_control")
    else:
        status = "✅ On" if enabled else "❌ Off"
        msg = (f"👋 Welcome Settings\n"
               f"Status: {status}\n"
               f"Current Text: {welcome_text if welcome_text else 'Not set (supports {ID}{NAME}{SURNAME}{NAMESURNAME}{LANG}{DATE}{TIME}{MENTION}{USERNAME}{GROUPNAME})'}")
        btn_toggle = types.InlineKeyboardButton(f"{'🔴 Off' if enabled else '🟢 On'}", callback_data=f"nw_toggle_{chat_id}")
        btn_set = types.InlineKeyboardButton("✏️ Set Text", callback_data=f"nw_set_{chat_id}")
        btn_back = types.InlineKeyboardButton("« Back", callback_data="channel_control")
    markup.add(btn_toggle, btn_set, btn_back)
    return msg, markup

# 完整个人信息（能获取的全部加入 + TG高级订阅）
def profile_menu(user_id, user):
    lang = get_lang(user_id)
    perm = "管理员" if is_global_admin(user_id) else "普通用户" if lang == 'zh' else "Admin" if is_global_admin(user_id) else "Regular User"
    # TG高级订阅
    premium = "是" if hasattr(user, 'is_premium') and user.is_premium else "否" if lang == 'zh' else "Yes" if hasattr(user, 'is_premium') and user.is_premium else "No"
    profile_items = [
        f"1. 昵称：{user.first_name} {user.last_name or ''}" if lang == 'zh' else f"1. Name: {user.first_name} {user.last_name or ''}",
        f"2. TG ID：{user.id}" if lang == 'zh' else f"2. TG ID: {user.id}",
        f"3. 用户名：@{user.username or '无'}" if lang == 'zh' else f"3. Username: @{user.username or 'None'}",
        f"4. 语言：{user.language_code or '未知'}" if lang == 'zh' else f"4. Language: {user.language_code or 'Unknown'}",
        f"5. 高级订阅：{premium}" if lang == 'zh' else f"5. Premium: {premium}",
        f"6. 机器人权限：{perm}" if lang == 'zh' else f"6. Bot Permission: {perm}"
    ]
    text = "👤 个人信息\n" + "\n".join(profile_items) if lang == 'zh' else "👤 My Profile\n" + "\n".join(profile_items)
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("« 返回" if lang == 'zh' else "« Back", callback_data="main_menu")
    markup.add(btn_back)
    return text, markup

# 超级管理员菜单 - 新增查看/移除功能
def super_admin_menu(user_id):
    lang = get_lang(user_id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    if lang == 'zh':
        admin_list = "\n".join([f"• ID：{uid}" for uid in GLOBAL_ADMINS]) if GLOBAL_ADMINS else "暂无全局管理员"
        text = f"🔱 超级管理员面板\n当前全局管理员：\n{admin_list}"
        btn_add_global = types.InlineKeyboardButton("➕ 添加全局管理员", callback_data="add_global_admin")
        btn_del_global = types.InlineKeyboardButton("➖ 移除全局管理员", callback_data="del_global_admin")
        btn_back = types.InlineKeyboardButton("« 返回", callback_data="main_menu")
    else:
        admin_list = "\n".join([f"• ID: {uid}" for uid in GLOBAL_ADMINS]) if GLOBAL_ADMINS else "No global admins"
        text = f"🔱 Super Admin Panel\nCurrent Global Admins:\n{admin_list}"
        btn_add_global = types.InlineKeyboardButton("➕ Add Global Admin", callback_data="add_global_admin")
        btn_del_global = types.InlineKeyboardButton("➖ Remove Global Admin", callback_data="del_global_admin")
        btn_back = types.InlineKeyboardButton("« Back", callback_data="main_menu")
    markup.add(btn_add_global, btn_del_global, btn_back)
    return text, markup

# 退出按钮
def exit_btn_markup(lang='zh'):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ 退出" if lang == 'zh' else "❌ Exit", callback_data="exit_menu"))
    return markup

# -------------------------- 问题反馈相关回调 --------------------------
@bot.callback_query_handler(func=lambda c: c.data == "feedback_confirm")
def feedback_confirm(call):
    """触发反馈确认菜单"""
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        lang = get_lang(call.from_user.id)
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    text, markup = feedback_confirm_menu(call.from_user.id)
    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == "feedback_start")
def feedback_start(call):
    """开始反馈流程"""
    uid = call.from_user.id
    lang = get_lang(uid)
    if call.message.message_id not in menu_owner or uid != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    
    # 检查当日反馈次数
    remaining = get_feedback_remaining(uid)
    if remaining <= 0:
        if lang == 'zh':
            bot.answer_callback_query(call.id, "❌ 今日反馈次数已用尽（每天最多3次），如需反馈可联系 @GeekyStudio", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "❌ Daily feedback limit reached (max 3 times/day), contact @GeekyStudio for further feedback", show_alert=True)
        return
    
    mark_clicked(call.message.message_id)
    # 反馈说明文本（固定按要求填写）
    feedback_text = """请发您遇到的问题，如果包含更详细的过程我们感激不尽！你可以在反馈里留下你的邮箱，我们可以在第一时间通知您，当然你也可以不填！但要注意:每个用户每天只能反馈3次，3次过后将不能反馈，如果反馈过限可以联系我反馈:@GeekyStudio"""
    # 发送反馈说明并等待用户输入
    user_waiting_feedback[uid] = True
    bot.edit_message_text(feedback_text, call.message.chat.id, call.message.id, reply_markup=feedback_exit_markup(lang))
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == "feedback_cancel")
def feedback_cancel(call):
    """取消反馈"""
    uid = call.from_user.id
    lang = get_lang(uid)
    if call.message.message_id not in menu_owner or uid != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    user_waiting_feedback[uid] = False
    # 返回主菜单
    text, markup = main_menu(uid)
    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda msg: user_waiting_feedback.get(msg.from_user.id, False))
def receive_feedback(msg):
    """接收用户反馈并发送邮件"""
    uid = msg.from_user.id
    lang = get_lang(uid)
    user_waiting_feedback[uid] = False
    
    # 获取用户名（优先显示username，无则显示ID）
    username = msg.from_user.username or f"TG_ID_{msg.from_user.id}"
    feedback_content = msg.text.strip()
    
    # 发送邮件
    success = send_feedback_email(username, feedback_content)
    
    # 增加反馈次数
    increment_feedback_count(uid)
    
    # 回复用户
    remaining = get_feedback_remaining(uid)
    if lang == 'zh':
        if success:
            reply_text = f"✅ 反馈提交成功！感谢你的支持～ 今日剩余反馈次数：{remaining}次"
        else:
            reply_text = f"❌ 反馈提交失败，请稍后再试～ 今日剩余反馈次数：{remaining}次"
    else:
        if success:
            reply_text = f"✅ Feedback submitted successfully! Thank you for your support～ Remaining feedbacks today: {remaining}"
        else:
            reply_text = f"❌ Failed to submit feedback, please try again later～ Remaining feedbacks today: {remaining}"
    
    # 返回主菜单
    send_bot_msg(msg.chat.id, reply_text, owner_id=uid, lang=lang)
    text, markup = main_menu(uid)
    send_bot_msg(msg.chat.id, text, markup, owner_id=uid, lang=lang)

# -------------------------- 命令与基础回调 --------------------------
@bot.message_handler(commands=['start', 'menu'])
def cmd_menu(message):
    user_id = message.from_user.id
    user_waiting_channel[user_id] = False
    user_waiting_set_admin[user_id] = False
    user_waiting_feedback[user_id] = False  # 初始化反馈状态
    text, markup = main_menu(user_id)
    send_bot_msg(message.chat.id, text, markup, owner_id=user_id, lang=get_lang(user_id))

# 超级管理员指令（仅你可用）
@bot.message_handler(commands=['Geeky-Super-Administrator'])
def super_admin_cmd(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    if user_id != SUPER_ADMIN_ID or username != SUPER_ADMIN_USERNAME:
        bot.reply_to(message, "❌ 非管理员不能执行" if get_lang(user_id) == 'zh' else "❌ Only admins can execute")
        return
    text, markup = super_admin_menu(user_id)
    send_bot_msg(message.chat.id, text, markup, owner_id=user_id, lang=get_lang(user_id))

@bot.message_handler(commands=['clear'])
def cmd_clear(message):
    uid = message.from_user.id
    lang = get_lang(uid)
    user_conversations[uid] = [{"role": "system", "content": get_system_prompt(lang)}]
    send_bot_msg(message.chat.id, "✅ 已重置" if lang == 'zh' else "✅ Reset", owner_id=uid, lang=lang)

# 退出菜单
@bot.callback_query_handler(func=lambda c: c.data == "exit_menu")
def exit_menu(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    try:
        bot.delete_message(call.message.chat.id, call.message.id)
    except:
        pass
    text, markup = main_menu(call.from_user.id)
    send_bot_msg(call.message.chat.id, text, markup, owner_id=call.from_user.id, lang=lang)
    bot.answer_callback_query(call.id)

# 时区菜单（修复不卡住）
@bot.callback_query_handler(func=lambda c: c.data == "tz_menu")
def tz_menu_call(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    text, markup = tz_menu(call.from_user.id)
    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    bot.answer_callback_query(call.id)

# 自动撤回菜单
@bot.callback_query_handler(func=lambda c: c.data == "delete_menu")
def delete_menu_call(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    text, markup = delete_menu(call.from_user.id)
    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == "del_group_toggle")
def del_group_toggle(call):
    uid = call.from_user.id
    auto_delete_group[uid] = not auto_delete_group.get(uid, True)
    text, markup = delete_menu(uid)
    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    bot.answer_callback_query(call.id, "✅ 已切换" if get_lang(uid) == 'zh' else "✅ Toggled")

@bot.callback_query_handler(func=lambda c: c.data == "del_private_toggle")
def del_private_toggle(call):
    uid = call.from_user.id
    auto_delete_private[uid] = not auto_delete_private.get(uid, True)
    text, markup = delete_menu(uid)
    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    bot.answer_callback_query(call.id, "✅ 已切换" if get_lang(uid) == 'zh' else "✅ Toggled")

@bot.callback_query_handler(func=lambda c: c.data == "set_del_group")
def set_del_group(call):
    lang = get_lang(call.from_user.id)
    send_bot_msg(call.message.chat.id, "发送群聊撤回时间（例：35秒、5分、1时、1天、1周、1月、1年、永久，支持自定义）" if lang == 'zh' else "Send group auto-delete time (e.g.: 35s, 5min, 1h, 1d, 1w, 1mo, 1y, permanent)", owner_id=call.from_user.id, lang=lang)
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, save_del_group)
    bot.answer_callback_query(call.id)

def save_del_group(msg):
    sec = parse_time_ext(msg.text.strip())
    lang = get_lang(msg.from_user.id)
    if sec is None or sec < 10:
        bot.reply_to(msg, "❌ 最低10秒" if lang == 'zh' else "❌ Minimum 10 seconds")
        return
    delete_time_group[msg.from_user.id] = sec
    bot.reply_to(msg, "✅ 已设置" if lang == 'zh' else "✅ Set successfully")

@bot.callback_query_handler(func=lambda c: c.data == "set_del_private")
def set_del_private(call):
    lang = get_lang(call.from_user.id)
    send_bot_msg(call.message.chat.id, "发送私聊撤回时间（例：35秒、5分、1时、1天、1周、1月、1年、永久，支持自定义）" if lang == 'zh' else "Send private auto-delete time (e.g.: 35s, 5min, 1h, 1d, 1w, 1mo, 1y, permanent)", owner_id=call.from_user.id, lang=lang)
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, save_del_private)
    bot.answer_callback_query(call.id)

def save_del_private(msg):
    sec = parse_time_ext(msg.text.strip())
    lang = get_lang(msg.from_user.id)
    if sec is None or sec < 10:
        bot.reply_to(msg, "❌ 最低10秒" if lang == 'zh' else "❌ Minimum 10 seconds")
        return
    delete_time_private[msg.from_user.id] = sec
    bot.reply_to(msg, "✅ 已设置" if lang == 'zh' else "✅ Set successfully")

# 个人信息
@bot.callback_query_handler(func=lambda c: c.data == "my_profile")
def my_profile(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    text, markup = profile_menu(call.from_user.id, call.from_user)
    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    bot.answer_callback_query(call.id)

# 频道管理员选择
@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_channel_"))
def admin_channel(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    chat_id = int(call.data.split("_")[-1])
    text, markup = channel_admin_menu(call.from_user.id, chat_id)
    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("set_admin_"))
def set_admin(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    uid = call.from_user.id
    chat_id = int(call.data.split("_")[-1])
    user_waiting_set_admin[uid] = f"add_{chat_id}"
    bot.edit_message_text("发送管理员用户名" if lang == 'zh' else "Send username", 
                          call.message.chat.id, call.message.id, reply_markup=exit_btn_markup(lang))
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("remove_admin_"))
def remove_admin(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    uid = call.from_user.id
    chat_id = int(call.data.split("_")[-1])
    user_waiting_set_admin[uid] = f"remove_{chat_id}"
    bot.edit_message_text("发送要卸任的管理员用户名" if lang == 'zh' else "Send username to remove", 
                          call.message.chat.id, call.message.id, reply_markup=exit_btn_markup(lang))
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda msg: user_waiting_set_admin.get(msg.from_user.id))
def save_admin(msg):
    uid = msg.from_user.id
    lang = get_lang(uid)
    mode, chat_id = user_waiting_set_admin[uid].split("_")
    chat_id = int(chat_id)
    username = msg.text.strip().replace("@", "")
    user_waiting_set_admin[uid] = False
    
    if mode == "add":
        if chat_id not in user_admins:
            user_admins[chat_id] = []
        if username not in user_admins[chat_id]:
            user_admins[chat_id].append(username)
        send_bot_msg(msg.chat.id, f"✅ 添加 @{username}" if lang == 'zh' else f"✅ Added @{username}", owner_id=uid, lang=lang)
    else:
        if chat_id in user_admins and username in user_admins[chat_id]:
            user_admins[chat_id].remove(username)
        send_bot_msg(msg.chat.id, f"✅ 卸任 @{username}" if lang == 'zh' else f"✅ Removed @{username}", owner_id=uid, lang=lang)

@bot.callback_query_handler(func=lambda c: c.data in ["tz_cn", "tz_us"])
def set_tz(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    uid = call.from_user.id
    user_timezone[uid] = "CN" if call.data == "tz_cn" else "US"
    text, markup = tz_menu(uid)
    bot.edit_message_text(f"✅ 时区已切换\n{text}" if lang == 'zh' else f"✅ Timezone switched\n{text}", 
                          call.message.chat.id, call.message.id, reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == "channel_list")
def channel_list(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    text, markup = channel_list_menu(call.from_user.id)
    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == "input_channel_id")
def input_channel_id(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    uid = call.from_user.id
    if len(user_channels.get(uid, [])) >= MAX_CHANNELS:
        bot.answer_callback_query(call.id, "最多15个" if lang == 'zh' else "Maximum 15 channels", show_alert=True)
        return
    user_waiting_channel[uid] = True
    bot.edit_message_text("发送频道号(@开头)" if lang == 'zh' else "Send channel username (start with @)", 
                          call.message.chat.id, call.message.id, reply_markup=exit_btn_markup(lang))
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda msg: user_waiting_channel.get(msg.from_user.id, False))
def bind_channel(msg):
    uid = msg.from_user.id
    lang = get_lang(uid)
    chat_id = msg.text.strip()
    try:
        chat = bot.get_chat(chat_id)
        if chat.type not in ["supergroup", "group", "channel"]:
            send_bot_msg(msg.chat.id, "❌ 仅支持超级群/普通群/频道" if lang == 'zh' else "❌ Only supergroups/groups/channels are supported", owner_id=uid, lang=lang)
            return
        if not is_bot_in_chat(chat_id):
            send_bot_msg(msg.chat.id, f"❌ 机器人未加入该群/频道" if lang == 'zh' else f"❌ Bot not in this group/channel", owner_id=uid, lang=lang)
            return
        if not is_chat_admin(chat.id, uid):
            send_bot_msg(msg.chat.id, "❌ 仅频道管理员/所有者可绑定" if lang == 'zh' else "❌ Only channel admins/owners can bind", owner_id=uid, lang=lang)
            return
        
        if chat.id not in channel_secret:
            msg_reply = send_bot_msg(msg.chat.id, "🔐 首次绑定，请设置6-20位数字+字母密钥" if lang == 'zh' else "🔐 First binding: set 6-20 alphanumeric secret", owner_id=uid, lang=lang)
            bot.register_next_step_handler(msg_reply, set_channel_secret, uid, chat)
            return
        
        send_bot_msg(msg.chat.id, "🔐 请输入频道密钥" if lang == 'zh' else "🔐 Enter channel secret", owner_id=uid, lang=lang)
        bot.register_next_step_handler(msg, check_channel_secret, uid, chat)
    except Exception as e:
        send_bot_msg(msg.chat.id, f"❌ 无效ID：{str(e)}" if lang == 'zh' else f"❌ Invalid ID: {str(e)}", owner_id=uid, lang=lang)

def set_channel_secret(msg, uid, chat):
    lang = get_lang(uid)
    secret = msg.text.strip()
    if len(secret) < 6 or len(secret) > 20 or not secret.isalnum():
        send_bot_msg(msg.chat.id, "❌ 密钥需6-20位数字+字母" if lang == 'zh' else "❌ Secret must be 6-20 alphanumeric characters", owner_id=uid, lang=lang)
        return
    channel_secret[chat.id] = secret
    if uid not in user_channels:
        user_channels[uid] = []
    user_channels[uid].append({"id": chat.id, "title": chat.title})
    # 首次绑定默认设置为活跃频道（✅自动显示）
    if not user_active_channel.get(uid):
        user_active_channel[uid] = chat.id
    user_waiting_channel[uid] = False
    send_bot_msg(msg.chat.id, f"✅ 密钥设置成功，已绑定：{chat.title}" if lang == 'zh' else f"✅ Secret set successfully, bound: {chat.title}", owner_id=uid, lang=lang)

def check_channel_secret(msg, uid, chat):
    lang = get_lang(uid)
    secret = msg.text.strip()
    if channel_secret.get(chat.id) != secret:
        send_bot_msg(msg.chat.id, "❌ 密钥错误" if lang == 'zh' else "❌ Wrong secret", owner_id=uid, lang=lang)
        return
    if uid not in user_channels:
        user_channels[uid] = []
    for ch in user_channels[uid]:
        if ch['id'] == chat.id:
            send_bot_msg(msg.chat.id, "✅ 已绑定" if lang == 'zh' else "✅ Already bound", owner_id=uid, lang=lang)
            return
    user_channels[uid].append({"id": chat.id, "title": chat.title})
    # 首次绑定默认设置为活跃频道（✅自动显示）
    if not user_active_channel.get(uid):
        user_active_channel[uid] = chat.id
    user_waiting_channel[uid] = False
    send_bot_msg(msg.chat.id, f"✅ 密钥正确，已绑定：{chat.title}" if lang == 'zh' else f"✅ Correct secret, bound: {chat.title}", owner_id=uid, lang=lang)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_"))
def del_channel(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    uid = call.from_user.id
    ch_id = int(call.data.split("_")[1])
    channels = user_channels.get(uid, [])
    target = next((c for c in channels if c['id'] == ch_id), None)
    if not target:
        bot.answer_callback_query(call.id)
        return
    markup = types.InlineKeyboardMarkup()
    btn_yes = types.InlineKeyboardButton("✅ 确认" if lang == 'zh' else "✅ Confirm", callback_data=f"confirm_del_{ch_id}")
    btn_no = types.InlineKeyboardButton("❌ 取消" if lang == 'zh' else "❌ Cancel", callback_data="channel_list")
    markup.add(btn_yes, btn_no)
    bot.edit_message_text(f"确认删除：{target['title']}？" if lang == 'zh' else f"Confirm delete: {target['title']}?", 
                          call.message.chat.id, call.message.id, reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm_del_"))
def confirm_del(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    uid = call.from_user.id
    ch_id = int(call.data.split("_")[2])
    if uid in user_channels:
        user_channels[uid] = [c for c in user_channels[uid] if c['id'] != ch_id]
    # 删除的是活跃频道时，自动切换到第一个频道（无则清空）
    if user_active_channel.get(uid) == ch_id:
        user_active_channel[uid] = user_channels[uid][0]['id'] if user_channels[uid] else None
    text, markup = channel_list_menu(uid)
    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    bot.answer_callback_query(call.id, "🗑️ 已删除" if lang == 'zh' else "🗑️ Deleted")

@bot.callback_query_handler(func=lambda c: c.data == "channel_control")
def channel_control(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    text, markup = channel_control_menu(call.from_user.id)
    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    bot.answer_callback_query(call.id)

# -------------------------- 禁止链接菜单回调 --------------------------
@bot.callback_query_handler(func=lambda c: c.data.startswith("link_ban_menu_"))
def lb_menu(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    chat_id = int(call.data.split("_")[-1])
    if not is_chat_admin(chat_id, call.from_user.id):
        bot.answer_callback_query(call.id, "❌ 仅频道管理员可操作" if lang == 'zh' else "❌ Only channel admins can operate", show_alert=True)
        return
    text, markup = link_ban_menu(call.from_user.id, chat_id)
    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("lb_toggle_"))
def lb_toggle(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    chat_id = int(call.data.split("_")[-1])
    if not is_chat_admin(chat_id, call.from_user.id):
        bot.answer_callback_query(call.id, "❌ 仅频道管理员可操作" if lang == 'zh' else "❌ Only channel admins can operate", show_alert=True)
        return
    user_link_ban_enabled[chat_id] = not user_link_ban_enabled.get(chat_id, False)
    text, markup = link_ban_menu(call.from_user.id, chat_id)
    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    bot.answer_callback_query(call.id, "✅ 已切换" if lang == 'zh' else "✅ Toggled")

@bot.callback_query_handler(func=lambda c: c.data.startswith("lb_punish_"))
def lb_punish(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    chat_id = int(call.data.split("_")[-1])
    if not is_chat_admin(chat_id, call.from_user.id):
        bot.answer_callback_query(call.id, "❌ 仅频道管理员可操作" if lang == 'zh' else "❌ Only channel admins can operate", show_alert=True)
        return
    p = user_link_punish_type.get(chat_id, "mute")
    user_link_punish_type[chat_id] = "ban" if p == "mute" else "mute"
    text, markup = link_ban_menu(call.from_user.id, chat_id)
    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    bot.answer_callback_query(call.id, "✅ 已切换" if lang == 'zh' else "✅ Toggled")

@bot.callback_query_handler(func=lambda c: c.data.startswith("lb_ptime_"))
def lb_ptime(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    chat_id = int(call.data.split("_")[-1])
    if not is_chat_admin(chat_id, call.from_user.id):
        bot.answer_callback_query(call.id, "❌ 仅频道管理员可操作" if lang == 'zh' else "❌ Only channel admins can operate", show_alert=True)
        return
    send_bot_msg(call.message.chat.id, "发送惩罚时间（例：35秒、5分、1时、1天、1周、1月、1年、永久，支持自定义）" if lang == 'zh' else "Send punish time (e.g.: 35s, 5min, 1h, 1d, 1w, 1mo, 1y, permanent)", owner_id=call.from_user.id, lang=lang)
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, save_lb_ptime, chat_id)
    bot.answer_callback_query(call.id)

def save_lb_ptime(msg, chat_id):
    lang = get_lang(msg.from_user.id)
    sec = parse_time_ext(msg.text.strip())
    if sec == "TOO_SHORT":
        bot.reply_to(msg, "❌ 最低35秒" if lang == 'zh' else "❌ Minimum 35 seconds")
        return
    if sec is None:
        bot.reply_to(msg, "❌ 格式错误" if lang == 'zh' else "❌ Invalid format")
        return
    user_link_punish_time[chat_id] = sec
    bot.reply_to(msg, "✅ 已设置" if lang == 'zh' else "✅ Set successfully")

# 新增TG链接屏蔽开关回调
@bot.callback_query_handler(func=lambda c: c.data.startswith("lb_tg_toggle_"))
def lb_tg_toggle(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    chat_id = int(call.data.split("_")[-1])
    if not is_chat_admin(chat_id, call.from_user.id):
        bot.answer_callback_query(call.id, "❌ 仅频道管理员可操作" if lang == 'zh' else "❌ Only channel admins can operate", show_alert=True)
        return
    user_block_all_tg_link[chat_id] = not user_block_all_tg_link.get(chat_id, True)
    text, markup = link_ban_menu(call.from_user.id, chat_id)
    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    bot.answer_callback_query(call.id, "✅ 已切换" if lang == 'zh' else "✅ Toggled")

# 新增添加自定义白名单回调
@bot.callback_query_handler(func=lambda c: c.data.startswith("lb_add_white_"))
def lb_add_white(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    chat_id = int(call.data.split("_")[-1])
    if not is_chat_admin(chat_id, call.from_user.id):
        bot.answer_callback_query(call.id, "❌ 仅频道管理员可操作" if lang == 'zh' else "❌ Only channel admins can operate", show_alert=True)
        return
    send_bot_msg(call.message.chat.id, "发送要添加的白名单（例：baidu.com，多个用逗号分隔）" if lang == 'zh' else "Send whitelist to add (e.g.: baidu.com, separate multiple with commas)", owner_id=call.from_user.id, lang=lang)
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, save_lb_add_white, chat_id)
    bot.answer_callback_query(call.id)

def save_lb_add_white(msg, chat_id):
    lang = get_lang(msg.from_user.id)
    white_list = [w.strip().lower() for w in msg.text.strip().split(",") if w.strip()]
    if not white_list:
        bot.reply_to(msg, "❌ 白名单不能为空" if lang == 'zh' else "❌ Whitelist cannot be empty")
        return
    if chat_id not in user_link_whitelist:
        user_link_whitelist[chat_id] = set()
    user_link_whitelist[chat_id].update(white_list)
    bot.reply_to(msg, f"✅ 已添加白名单：{','.join(white_list)}" if lang == 'zh' else f"✅ Whitelist added: {','.join(white_list)}")

# 新增删除自定义白名单回调
@bot.callback_query_handler(func=lambda c: c.data.startswith("lb_del_white_"))
def lb_del_white(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    chat_id = int(call.data.split("_")[-1])
    if not is_chat_admin(chat_id, call.from_user.id):
        bot.answer_callback_query(call.id, "❌ 仅频道管理员可操作" if lang == 'zh' else "❌ Only channel admins can operate", show_alert=True)
        return
    send_bot_msg(call.message.chat.id, "发送要删除的白名单（例：baidu.com，多个用逗号分隔）" if lang == 'zh' else "Send whitelist to delete (e.g.: baidu.com, separate multiple with commas)", owner_id=call.from_user.id, lang=lang)
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, save_lb_del_white, chat_id)
    bot.answer_callback_query(call.id)

def save_lb_del_white(msg, chat_id):
    lang = get_lang(msg.from_user.id)
    white_list = [w.strip().lower() for w in msg.text.strip().split(",") if w.strip()]
    if not white_list:
        bot.reply_to(msg, "❌ 白名单不能为空" if lang == 'zh' else "❌ Whitelist cannot be empty")
        return
    if chat_id not in user_link_whitelist:
        bot.reply_to(msg, "❌ 暂无自定义白名单" if lang == 'zh' else "❌ No custom whitelist")
        return
    del_count = 0
    for w in white_list:
        if w in user_link_whitelist[chat_id]:
            user_link_whitelist[chat_id].remove(w)
            del_count += 1
    remain = ','.join(user_link_whitelist[chat_id]) if user_link_whitelist[chat_id] else '无' if lang == 'zh' else 'None'
    bot.reply_to(msg, f"✅ 已删除{del_count}个白名单，剩余：{remain}" if lang == 'zh' else f"✅ Deleted {del_count} whitelist items, remaining: {remain}")

# -------------------------- 入群验证菜单回调 --------------------------
@bot.callback_query_handler(func=lambda c: c.data.startswith("join_verify_menu_"))
def jv_menu(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    chat_id = int(call.data.split("_")[-1])
    if not is_chat_admin(chat_id, call.from_user.id):
        bot.answer_callback_query(call.id, "❌ 仅频道管理员可操作" if lang == 'zh' else "❌ Only channel admins can operate", show_alert=True)
        return
    text, markup = join_verify_menu(call.from_user.id, chat_id)
    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("jv_toggle_"))
def jv_toggle(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    chat_id = int(call.data.split("_")[-1])
    if not is_chat_admin(chat_id, call.from_user.id):
        bot.answer_callback_query(call.id, "❌ 仅频道管理员可操作" if lang == 'zh' else "❌ Only channel admins can operate", show_alert=True)
        return
    user_join_verify_enabled[chat_id] = not user_join_verify_enabled.get(chat_id, False)
    text, markup = join_verify_menu(call.from_user.id, chat_id)
    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    bot.answer_callback_query(call.id, "✅ 已切换" if lang == 'zh' else "✅ Toggled")

@bot.callback_query_handler(func=lambda c: c.data.startswith("jv_type_"))
def jv_type(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    chat_id = int(call.data.split("_")[-1])
    if not is_chat_admin(chat_id, call.from_user.id):
        bot.answer_callback_query(call.id, "❌ 仅频道管理员可操作" if lang == 'zh' else "❌ Only channel admins can operate", show_alert=True)
        return
    t = user_join_verify_type.get(chat_id, "math")
    user_join_verify_type[chat_id] = "button" if t == "math" else "math"
    text, markup = join_verify_menu(call.from_user.id, chat_id)
    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    bot.answer_callback_query(call.id, "✅ 已切换" if lang == 'zh' else "✅ Toggled")

@bot.callback_query_handler(func=lambda c: c.data.startswith("jv_punish_"))
def jv_punish(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    chat_id = int(call.data.split("_")[-1])
    if not is_chat_admin(chat_id, call.from_user.id):
        bot.answer_callback_query(call.id, "❌ 仅频道管理员可操作" if lang == 'zh' else "❌ Only channel admins can operate", show_alert=True)
        return
    p = user_join_verify_punish.get(chat_id, "mute")
    user_join_verify_punish[chat_id] = "ban" if p == "mute" else "mute"
    text, markup = join_verify_menu(call.from_user.id, chat_id)
    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    bot.answer_callback_query(call.id, "✅ 已切换" if lang == 'zh' else "✅ Toggled")

@bot.callback_query_handler(func=lambda c: c.data.startswith("jv_ptime_"))
def jv_ptime(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    chat_id = int(call.data.split("_")[-1])
    if not is_chat_admin(chat_id, call.from_user.id):
        bot.answer_callback_query(call.id, "❌ 仅频道管理员可操作" if lang == 'zh' else "❌ Only channel admins can operate", show_alert=True)
        return
    send_bot_msg(call.message.chat.id, "发送惩罚时间（例：35秒、5分、1时、1天、1周、1月、1年、永久，支持自定义）" if lang == 'zh' else "Send punish time (e.g.: 35s, 5min, 1h, 1d, 1w, 1mo, 1y, permanent)", owner_id=call.from_user.id, lang=lang)
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, save_jv_ptime, chat_id)
    bot.answer_callback_query(call.id)

def save_jv_ptime(msg, chat_id):
    lang = get_lang(msg.from_user.id)
    sec = parse_time_ext(msg.text.strip())
    if sec == "TOO_SHORT":
        bot.reply_to(msg, "❌ 最低35秒" if lang == 'zh' else "❌ Minimum 35 seconds")
        return
    if sec is None:
        bot.reply_to(msg, "❌ 格式错误" if lang == 'zh' else "❌ Invalid format")
        return
    user_join_verify_punish_time[chat_id] = sec
    bot.reply_to(msg, "✅ 已设置" if lang == 'zh' else "✅ Set successfully")

@bot.callback_query_handler(func=lambda c: c.data.startswith("jv_timeout_"))
def jv_timeout(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    chat_id = int(call.data.split("_")[-1])
    if not is_chat_admin(chat_id, call.from_user.id):
        bot.answer_callback_query(call.id, "❌ 仅频道管理员可操作" if lang == 'zh' else "❌ Only channel admins can operate", show_alert=True)
        return
    send_bot_msg(call.message.chat.id, "发送超时（例：35秒、5分、1时、1天、1周、1月、1年、永久，支持自定义）" if lang == 'zh' else "Send timeout (e.g.: 35s, 5min, 1h, 1d, 1w, 1mo, 1y, permanent)", owner_id=call.from_user.id, lang=lang)
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, save_jv_timeout, chat_id)
    bot.answer_callback_query(call.id)

def save_jv_timeout(msg, chat_id):
    lang = get_lang(msg.from_user.id)
    sec = parse_time_ext(msg.text.strip())
    if sec == "TOO_SHORT":
        bot.reply_to(msg, "❌ 最低35秒" if lang == 'zh' else "❌ Minimum 35 seconds")
        return
    if sec is None:
        bot.reply_to(msg, "❌ 格式错误" if lang == 'zh' else "❌ Invalid format")
        return
    user_join_verify_timeout[chat_id] = sec
    bot.reply_to(msg, "✅ 超时时间已设置" if lang == 'zh' else "✅ Timeout set successfully")

# 入群验证尝试次数设置回调
@bot.callback_query_handler(func=lambda c: c.data.startswith("jv_attempts_"))
def jv_attempts(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    chat_id = int(call.data.split("_")[-1])
    if not is_chat_admin(chat_id, call.from_user.id):
        bot.answer_callback_query(call.id, "❌ 仅频道管理员可操作" if lang == 'zh' else "❌ Only channel admins can operate", show_alert=True)
        return
    send_bot_msg(call.message.chat.id, f"发送验证尝试次数（默认2次，最少1次，最多5次）" if lang == 'zh' else f"Send verify attempts (default 2, min 1, max 5)", owner_id=call.from_user.id, lang=lang)
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, save_jv_attempts, chat_id)
    bot.answer_callback_query(call.id)

def save_jv_attempts(msg, chat_id):
    lang = get_lang(msg.from_user.id)
    try:
        attempts = int(msg.text.strip())
        if attempts < 1 or attempts > 5:
            bot.reply_to(msg, "❌ 次数需在1-5之间" if lang == 'zh' else "❌ Attempts must be between 1-5")
            return
        user_join_verify_attempts[chat_id] = attempts
        bot.reply_to(msg, f"✅ 尝试次数已设置为{attempts}次" if lang == 'zh' else f"✅ Attempts set to {attempts}")
    except:
        bot.reply_to(msg, "❌ 格式错误，请输入数字" if lang == 'zh' else "❌ Invalid format, enter a number")

# -------------------------- 超时惩罚函数（含尝试次数判断） --------------------------
def check_verify_timeout(key):
    if key not in user_pending_verify:
        return
    data = user_pending_verify[key]
    chat_id = data['chat']
    uid = data['uid']
    punish_type = user_join_verify_punish.get(chat_id, "mute")
    punish_time = user_join_verify_punish_time.get(chat_id, 35)
    until = get_punish_until(punish_time, uid)
    lang = get_lang(uid)
    
    try:
        if punish_type == "mute":
            bot.restrict_chat_member(chat_id, uid, until_date=until, can_send_messages=False)
        else:
            bot.ban_chat_member(chat_id, uid, until_date=until)
    except:
        pass
    if key in user_pending_verify:
        del user_pending_verify[key]
    bot.send_message(chat_id, f"[{uid}] 验证超时/尝试次数用尽，已执行惩罚" if lang == 'zh' else f"[{uid}] Verify timeout/attempts exhausted, punishment executed")

# -------------------------- 验证按钮回调（含尝试次数限制） --------------------------
@bot.callback_query_handler(func=lambda c: c.data.startswith("verify_btn_"))
def verify_btn(call):
    prefix = "verify_btn_"
    lang = get_lang(call.from_user.id)
    if not call.data.startswith(prefix):
        bot.answer_callback_query(call.id, "❌ 无效" if lang == 'zh' else "❌ Invalid", show_alert=True)
        return
    data_part = call.data[len(prefix):]
    parts = data_part.split("_", 2)
    if len(parts) < 2:
        bot.answer_callback_query(call.id, "❌ 数据错误" if lang == 'zh' else "❌ Data error", show_alert=True)
        return
    try:
        chat_id = int(parts[0])
        uid = int(parts[1])
    except:
        bot.answer_callback_query(call.id, "❌ 格式错误" if lang == 'zh' else "❌ Format error", show_alert=True)
        return
    key = f"{chat_id}_{uid}"
    if key not in user_pending_verify:
        bot.answer_callback_query(call.id, "❌ 已过期" if lang == 'zh' else "❌ Expired", show_alert=True)
        return
    
    data = user_pending_verify[key]
    max_attempts = user_join_verify_attempts.get(chat_id, DEFAULT_VERIFY_ATTEMPTS)
    current_attempts = data.get("attempts", 0) + 1
    
    # 尝试次数用尽
    if current_attempts > max_attempts:
        bot.answer_callback_query(call.id, f"❌ 尝试次数用尽，将执行惩罚" if lang == 'zh' else f"❌ Attempts exhausted, punishment will be executed", show_alert=True)
        # 执行惩罚
        punish_type = user_join_verify_punish.get(chat_id, "mute")
        punish_time = user_join_verify_punish_time.get(chat_id, 35)
        until = get_punish_until(punish_time, uid)
        try:
            if punish_type == "mute":
                bot.restrict_chat_member(chat_id, uid, until_date=until, can_send_messages=False)
            else:
                bot.ban_chat_member(chat_id, uid, until_date=until)
        except:
            pass
        if key in user_pending_verify:
            del user_pending_verify[key]
        bot.edit_message_text(f"❌ 尝试次数用尽，已执行惩罚" if lang == 'zh' else f"❌ Attempts exhausted, punishment executed", 
                              call.message.chat.id, call.message.id)
        return
    
    # 验证通过（按钮验证直接通过）
    data["attempts"] = current_attempts
    user_pending_verify[key] = data
    del user_pending_verify[key]
    bot.restrict_chat_member(chat_id, uid, can_send_messages=True, can_send_media_messages=True)
    bot.edit_message_text("✅ 验证通过" if lang == 'zh' else "✅ Verify passed", call.message.chat.id, call.message.id)
    bot.answer_callback_query(call.id, "成功" if lang == 'zh' else "Success")
    
    # 强制触发入群欢迎
    if user_new_welcome_enabled.get(chat_id, False):
        try:
            user = bot.get_chat(uid)
            chat = bot.get_chat(chat_id)
            welcome_text = user_new_welcome_text.get(chat_id, "🎉 欢迎加入 {GROUPNAME}！" if lang == 'zh' else "🎉 Welcome to {GROUPNAME}!")
            rendered_text = format_welcome(welcome_text, user, chat, lang)
            bot.send_message(chat_id, rendered_text, parse_mode="Markdown")
        except Exception as e:
            print(f"欢迎语发送失败：{e}" if lang == 'zh' else f"Welcome message failed: {e}")

# 计算题按钮验证（含尝试次数限制） --------------------------
@bot.callback_query_handler(func=lambda c: c.data.startswith("math_ans_"))
def math_ans(call):
    prefix = "math_ans_"
    lang = get_lang(call.from_user.id)
    if not call.data.startswith(prefix):
        return
    data_part = call.data[len(prefix):]
    parts = data_part.split("_", 3)
    if len(parts) < 3:
        bot.answer_callback_query(call.id, "❌ 数据错误" if lang == 'zh' else "❌ Data error", show_alert=True)
        return
    try:
        chat_id = int(parts[0])
        uid = int(parts[1])
        ans = int(parts[2])
    except:
        bot.answer_callback_query(call.id, "❌ 格式错误" if lang == 'zh' else "❌ Format error", show_alert=True)
        return
    key = f"{chat_id}_{uid}"
    if key not in user_pending_verify:
        bot.answer_callback_query(call.id, "❌ 已过期" if lang == 'zh' else "❌ Expired", show_alert=True)
        return
    data = user_pending_verify[key]
    max_attempts = user_join_verify_attempts.get(chat_id, DEFAULT_VERIFY_ATTEMPTS)
    current_attempts = data.get("attempts", 0) + 1
    
    # 尝试次数用尽
    if current_attempts > max_attempts:
        bot.answer_callback_query(call.id, f"❌ 尝试次数用尽，将执行惩罚" if lang == 'zh' else f"❌ Attempts exhausted, punishment will be executed", show_alert=True)
        # 执行惩罚
        punish_type = user_join_verify_punish.get(chat_id, "mute")
        punish_time = user_join_verify_punish_time.get(chat_id, 35)
        until = get_punish_until(punish_time, uid)
        try:
            if punish_type == "mute":
                bot.restrict_chat_member(chat_id, uid, until_date=until, can_send_messages=False)
            else:
                bot.ban_chat_member(chat_id, uid, until_date=until)
        except:
            pass
        if key in user_pending_verify:
            del user_pending_verify[key]
        bot.edit_message_text(f"❌ 尝试次数用尽，已执行惩罚" if lang == 'zh' else f"❌ Attempts exhausted, punishment executed", 
                              call.message.chat.id, call.message.id)
        return
    
    # 答案正确
    if ans == data['ans']:
        data["attempts"] = current_attempts
        user_pending_verify[key] = data
        del user_pending_verify[key]
        bot.restrict_chat_member(chat_id, uid, can_send_messages=True, can_send_media_messages=True)
        bot.edit_message_text("✅ 验证通过" if lang == 'zh' else "✅ Verify passed", call.message.chat.id, call.message.id)
        bot.answer_callback_query(call.id, "正确！" if lang == 'zh' else "Correct!")
        
        # 强制触发入群欢迎
        if user_new_welcome_enabled.get(chat_id, False):
            try:
                user = bot.get_chat(uid)
                chat = bot.get_chat(chat_id)
                welcome_text = user_new_welcome_text.get(chat_id, "🎉 欢迎加入 {GROUPNAME}！" if lang == 'zh' else "🎉 Welcome to {GROUPNAME}!")
                rendered_text = format_welcome(welcome_text, user, chat, lang)
                bot.send_message(chat_id, rendered_text, parse_mode="Markdown")
            except Exception as e:
                print(f"欢迎语发送失败：{e}" if lang == 'zh' else f"Welcome message failed: {e}")
    # 答案错误，更新尝试次数
    else:
        data["attempts"] = current_attempts
        user_pending_verify[key] = data
        remaining = max_attempts - current_attempts
        bot.answer_callback_query(call.id, f"❌ 错误，剩余{remaining}次尝试" if lang == 'zh' else f"❌ Wrong, {remaining} attempts left", show_alert=True)

# -------------------------- 新入群触发逻辑（兼容双功能开启） --------------------------
@bot.message_handler(content_types=['new_chat_members'])
def on_new_member(msg):
    chat_id = msg.chat.id
    lang = get_lang(msg.from_user.id)
    # 校验频道绑定状态
    target_uid = None
    for uid, channels in user_channels.items():
        if any(ch['id'] == chat_id for ch in channels):
            target_uid = uid
            break
    if not target_uid:
        return

    # 1. 入群验证开启：执行验证流程（初始化尝试次数）
    if user_join_verify_enabled.get(chat_id, False):
        for user in msg.new_chat_members:
            if user.is_bot:
                continue
            uid = user.id
            bot.restrict_chat_member(chat_id, uid, can_send_messages=False)
            vtype = user_join_verify_type.get(chat_id, "math")
            key = f"{chat_id}_{uid}"
            timeout = user_join_verify_timeout.get(chat_id, 300)
            max_attempts = user_join_verify_attempts.get(chat_id, DEFAULT_VERIFY_ATTEMPTS)
            
            if vtype == "math":
                a = random.randint(1, 20)
                b = random.randint(1, 20)
                ans = a + b
                # 初始化尝试次数为0
                user_pending_verify[key] = {"type": "math", "ans": ans, "chat": chat_id, "uid": uid, "attempts": 0}
                options = [ans]
                while len(options) < 6:
                    num = random.randint(ans - 5, ans + 5)
                    if num not in options and num > 0:
                        options.append(num)
                random.shuffle(options)
                markup = types.InlineKeyboardMarkup(row_width=3)
                row1 = [types.InlineKeyboardButton(str(options[i]), callback_data=f"math_ans_{chat_id}_{uid}_{options[i]}") for i in range(3)]
                row2 = [types.InlineKeyboardButton(str(options[i]), callback_data=f"math_ans_{chat_id}_{uid}_{options[i]}") for i in range(3,6)]
                markup.add(*row1, *row2)
                bot.send_message(chat_id, f"[{user.first_name}](tg://user?id={uid}) 请在{sec_to_text(timeout, lang)}内选择正确答案（共{max_attempts}次尝试）：{a}+{b}=？" if lang == 'zh' else f"[{user.first_name}](tg://user?id={uid}) Select the correct answer within {sec_to_text(timeout, lang)} (Total {max_attempts} attempts): {a}+{b}=?", 
                                reply_markup=markup, parse_mode="Markdown")
            else:
                user_pending_verify[key] = {"type": "button", "chat": chat_id, "uid": uid, "attempts": 0}
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("✅ 我是真人，点击验证" if lang == 'zh' else "✅ I'm human, click to verify", callback_data=f"verify_btn_{chat_id}_{uid}"))
                bot.send_message(chat_id, f"[{user.first_name}](tg://user?id={uid}) 请在{sec_to_text(timeout, lang)}内点击按钮验证（共{max_attempts}次尝试）" if lang == 'zh' else f"[{user.first_name}](tg://user?id={uid}) Click the button to verify within {sec_to_text(timeout, lang)} (Total {max_attempts} attempts)", 
                                reply_markup=markup, parse_mode="Markdown")
            
            threading.Timer(timeout, check_verify_timeout, args=(key,)).start()
    
    # 2. 入群验证未开启：直接发送欢迎语
    else:
        if user_new_welcome_enabled.get(chat_id, False):
            for user in msg.new_chat_members:
                if user.is_bot:
                    continue
                try:
                    lang = get_lang(target_uid)
                    welcome_text = user_new_welcome_text.get(chat_id, "🎉 欢迎加入 {GROUPNAME}！" if lang == 'zh' else "🎉 Welcome to {GROUPNAME}!")
                    rendered_text = format_welcome(welcome_text, user, msg.chat, lang)
                    bot.send_message(chat_id, rendered_text, parse_mode="Markdown")
                except Exception as e:
                    print(f"欢迎语发送失败：{e}" if lang == 'zh' else f"Welcome message failed: {e}")

# -------------------------- 入群欢迎菜单回调 --------------------------
@bot.callback_query_handler(func=lambda c: c.data.startswith("new_welcome_menu_"))
def nw_menu(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    chat_id = int(call.data.split("_")[-1])
    if not is_chat_admin(chat_id, call.from_user.id):
        bot.answer_callback_query(call.id, "❌ 仅频道管理员可操作" if lang == 'zh' else "❌ Only channel admins can operate", show_alert=True)
        return
    text, markup = new_welcome_menu(call.from_user.id, chat_id)
    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("nw_toggle_"))
def nw_toggle(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    chat_id = int(call.data.split("_")[-1])
    if not is_chat_admin(chat_id, call.from_user.id):
        bot.answer_callback_query(call.id, "❌ 仅频道管理员可操作" if lang == 'zh' else "❌ Only channel admins can operate", show_alert=True)
        return
    user_new_welcome_enabled[chat_id] = not user_new_welcome_enabled.get(chat_id, False)
    text, markup = new_welcome_menu(call.from_user.id, chat_id)
    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    bot.answer_callback_query(call.id, "✅ 已切换" if lang == 'zh' else "✅ Toggled")

@bot.callback_query_handler(func=lambda c: c.data.startswith("nw_set_"))
def nw_set(call):
    lang = get_lang(call.from_user.id)
    if call.message.message_id not in menu_owner or call.from_user.id != menu_owner[call.message.message_id]:
        bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if lang == 'zh' else "❌ You don't have permission", show_alert=True)
        return
    mark_clicked(call.message.message_id)
    chat_id = int(call.data.split("_")[-1])
    if not is_chat_admin(chat_id, call.from_user.id):
        bot.answer_callback_query(call.id, "❌ 仅频道管理员可操作" if lang == 'zh' else "❌ Only channel admins can operate", show_alert=True)
        return
    send_bot_msg(call.message.chat.id, "发送欢迎语" if lang == 'zh' else "Send welcome text", owner_id=call.from_user.id, lang=lang)
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, save_nw_text, chat_id)
    bot.answer_callback_query(call.id)

def save_nw_text(msg, chat_id):
    lang = get_lang(msg.from_user.id)
    user_new_welcome_text[chat_id] = msg.text.strip()
    bot.reply_to(msg, "✅ 欢迎语已保存" if lang == 'zh' else "✅ Welcome text saved")

# -------------------------- 禁止链接（兼容其他功能） --------------------------
@bot.message_handler(func=lambda msg: msg.chat.type in ["supergroup", "group", "channel"])
def check_link(msg):
    chat_id = msg.chat.id
    lang = get_lang(msg.from_user.id)
    target_uid = None
    for uid, channels in user_channels.items():
        if any(ch['id'] == chat_id for ch in channels):
            target_uid = uid
            break
    if not target_uid or not user_link_ban_enabled.get(chat_id, False):
        return
    
    if not msg.text:
        return
    has_link = any(key in msg.text.lower() for key in ["http", "www.", ".com", ".cn", ".im", ".org", ".net", "t.me", "telegram.org"])
    if not has_link:
        return
    custom_white = user_link_whitelist.get(chat_id, set())
    if any(white in msg.text.lower() for white in custom_white):
        return
    block_tg = user_block_all_tg_link.get(chat_id, True)
    if block_tg and any(tg in msg.text.lower() for tg in ["t.me", "telegram.org"]):
        return
    user = msg.from_user
    if not user or user.is_bot or f"{chat_id}_{user.id}" in user_pending_verify:
        return
    try:
        bot.delete_message(chat_id, msg.message_id)
    except:
        pass
    punish_type = user_link_punish_type.get(chat_id, "mute")
    punish_time = user_link_punish_time.get(chat_id, 35)
    until = get_punish_until(punish_time, target_uid)
    try:
        if punish_type == "mute":
            bot.restrict_chat_member(chat_id, user.id, until_date=until, can_send_messages=False)
        else:
            bot.ban_chat_member(chat_id, user.id, until_date=until)
    except:
        pass
    time_text = sec_to_text(punish_time, lang)
    notify_text = f"@{user.username or '未知用户' if lang == 'zh' else 'Unknown User'}[{user.id}] 发了链接 已{'禁言' if punish_type == 'mute' else '封禁'}！预计 {time_text} 解封！" if lang == 'zh' else f"@{user.username or 'Unknown User'}[{user.id}] Sent a link, {'Muted' if punish_type == 'mute' else 'Banned'}! Unban in {time_text}!"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ 解除处罚" if lang == 'zh' else "✅ Unban", callback_data=f"unban_{chat_id}_{user.id}_{punish_type}"))
    bot.send_message(chat_id, notify_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("unban_"))
def unban_user(call):
    lang = get_lang(call.from_user.id)
    try:
        _, chat_id, user_id, punish_type = call.data.split("_")
        chat_id = int(chat_id)
        user_id = int(user_id)
    except:
        bot.answer_callback_query(call.id, "❌ 指令错误" if lang == 'zh' else "❌ Command error", show_alert=True)
        return
    if not is_chat_admin(chat_id, call.from_user.id):
        bot.answer_callback_query(call.id, "❌ 仅频道管理员可操作" if lang == 'zh' else "❌ Only channel admins can operate", show_alert=True)
        return
    try:
        if punish_type == "mute":
            bot.restrict_chat_member(chat_id, user_id, can_send_messages=True, can_send_media_messages=True)
        else:
            bot.unban_chat_member(chat_id, user_id)
        bot.edit_message_text("✅ 已解除处罚" if lang == 'zh' else "✅ Punishment removed", call.message.chat.id, call.message.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ 失败：{str(e)}" if lang == 'zh' else f"❌ Failed: {str(e)}", show_alert=True)

# -------------------------- AI 聊天（私聊保留） --------------------------
def get_ai_reply(user_id, text):
    lang = get_lang(user_id)
    if user_id not in user_conversations:
        user_conversations[user_id] = [{"role": "system", "content": get_system_prompt(lang)}]
    user_conversations[user_id].append({"role": "user", "content": text})
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
    payload = {"model": MODEL_NAME, "messages": user_conversations[user_id], "temperature": 0.7, "max_tokens": 2000}
    try:
        r = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30)
        return r.json()["choices"][0]["message"]["content"]
    except:
        return "❌ API错误" if lang == 'zh' else "❌ API Error"

@bot.message_handler(func=lambda msg: True and not msg.text.startswith('/') and not user_waiting_channel.get(msg.from_user.id, False) and not user_waiting_set_admin.get(msg.from_user.id, False) and not user_waiting_feedback.get(msg.from_user.id, False))
def on_message(msg):
    uid = msg.from_user.id
    if msg.chat.type == "private":
        bot.send_chat_action(msg.chat.id, "typing")
        bot.reply_to(msg, get_ai_reply(uid, msg.text))
        return

# -------------------------- 通用回调（续） --------------------------
@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    if call.message.message_id in menu_owner:
        if call.from_user.id != menu_owner[call.message.message_id]:
            bot.answer_callback_query(call.id, "❌ 你无权操作此菜单" if get_lang(call.from_user.id) == 'zh' else "❌ You don't have permission", show_alert=True)
            return
    uid = call.from_user.id
    lang = get_lang(uid)
    data = call.data
    if data == "main_menu":
        user_waiting_channel[uid] = False
        user_waiting_set_admin[uid] = False
        user_waiting_feedback[uid] = False  # 重置反馈状态
        mark_clicked(call.message.message_id)
        text, markup = main_menu(uid)
        bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    elif data == "menu_language":
        mark_clicked(call.message.message_id)
        text, markup = language_menu(uid)
        bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    elif data == "lang_zh":
        set_lang(uid, 'zh')
        mark_clicked(call.message.message_id)
        text, markup = main_menu(uid)
        bot.edit_message_text(f"✅ 已切换为中文\n{text}", call.message.chat.id, call.message.id, reply_markup=markup)
    elif data == "lang_en":
        set_lang(uid, 'en')
        mark_clicked(call.message.message_id)
        text, markup = main_menu(uid)
        bot.edit_message_text(f"✅ Switched to English\n{text}", call.message.chat.id, call.message.id, reply_markup=markup)
    elif data == "confirm_clear":
        mark_clicked(call.message.message_id)
        text, markup = confirm_clear_menu(uid)
        bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    elif data == "do_clear":
        user_conversations[uid] = [{"role": "system", "content": get_system_prompt(lang)}]
        mark_clicked(call.message.message_id)
        text, markup = main_menu(uid)
        bot.edit_message_text(f"✅ 对话已重置\n{text}" if lang == 'zh' else f"✅ Chat reset\n{text}", call.message.chat.id, call.message.id, reply_markup=markup)
    elif data == "add_global_admin":
        send_bot_msg(call.message.chat.id, "请输入要添加的管理员用户ID（多个用空格分隔）" if lang == 'zh' else "Enter admin user IDs to add (separate with spaces)", owner_id=uid, lang=lang)
        bot.register_next_step_handler_by_chat_id(call.message.chat.id, save_global_admin)
    elif data == "del_global_admin":
        send_bot_msg(call.message.chat.id, "请输入要移除的管理员用户ID（多个用空格分隔）" if lang == 'zh' else "Enter admin user IDs to remove (separate with spaces)", owner_id=uid, lang=lang)
        bot.register_next_step_handler_by_chat_id(call.message.chat.id, del_global_admin)
    elif data == "admin_menu":
        mark_clicked(call.message.message_id)
        text, markup = admin_menu(uid)
        bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    bot.answer_callback_query(call.id)

# 新增：移除全局管理员函数
def del_global_admin(msg):
    lang = get_lang(msg.from_user.id)
    if msg.from_user.id != SUPER_ADMIN_ID:
        bot.reply_to(msg, "❌ 仅超级管理员可操作" if lang == 'zh' else "❌ Only super admin can operate")
        return
    try:
        ids = list(map(int, msg.text.strip().split()))
        del_count = 0
        for uid in ids:
            if uid in GLOBAL_ADMINS:
                GLOBAL_ADMINS.remove(uid)
                del_count += 1
        bot.reply_to(msg, f"✅ 已移除 {del_count} 名全局管理员，剩余：{len(GLOBAL_ADMINS)} 名" if lang == 'zh' else f"✅ Removed {del_count} global admins, remaining: {len(GLOBAL_ADMINS)}")
    except:
        bot.reply_to(msg, "❌ 格式错误，请输入用户ID，多个用空格分隔" if lang == 'zh' else "❌ Invalid format, enter user IDs separated by spaces")

def save_global_admin(msg):
    lang = get_lang(msg.from_user.id)
    if msg.from_user.id != SUPER_ADMIN_ID:
        bot.reply_to(msg, "❌ 仅超级管理员可操作" if lang == 'zh' else "❌ Only super admin can operate")
        return
    try:
        ids = list(map(int, msg.text.strip().split()))
        add_count = 0
        for uid in ids:
            if uid not in GLOBAL_ADMINS:
                GLOBAL_ADMINS.append(uid)
                add_count += 1
        bot.reply_to(msg, f"✅ 已添加 {add_count} 名全局管理员，总计：{len(GLOBAL_ADMINS)} 名" if lang == 'zh' else f"✅ Added {add_count} global admins, total: {len(GLOBAL_ADMINS)}")
    except:
        bot.reply_to(msg, "❌ 格式错误，请输入用户ID，多个用空格分隔" if lang == 'zh' else "❌ Invalid format, enter user IDs separated by spaces")

# -------------------------- 启动 --------------------------
if __name__ == '__main__':
    print(f"✅ GeekyAI 启动成功！机器人ID：{bot.get_me().id}")
    bot.infinity_polling(skip_pending=True)
    
