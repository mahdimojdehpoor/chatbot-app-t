# -*- coding: utf-8 -*-
"""
چت‌بات هوش مصنوعی - نسخه‌ی پایه با Toga
(متن فارسی توسط خودِ ویجت‌های بومی اندروید رندر می‌شه، بدون نیاز به هیچ ترفندی)
"""

import re
import threading

import requests
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

# ==========================================
# کلید API خودتون رو اینجا بذارید
# از سایت console.groq.com بگیرید
# ==========================================
API_KEY = "PLACEHOLDER_API_KEY"
URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "openai/gpt-oss-120b"
VISION_MODEL = "qwen/qwen3.6-27b"

BASE_PROMPT = (
    "تو یک دستیار هوشمند و مفید هستی که فقط و فقط به فارسیِ روان و طبیعی پاسخ می‌دی. "
    "همیشه از دستور زبان و ترتیب طبیعیِ کلمات در جمله‌ی فارسی استفاده کن؛ جمله‌هات باید دقیقاً "
    "مثل یک فارسی‌زبان بومی نوشته بشه، نه شبیه ترجمه‌ی کلمه‌به‌کلمه از انگلیسی. "
    "پاسخ‌هات باید دقیق، منسجم و منطقی باشه."
)

LEVEL_PROMPTS = {
    "عمومی": "توضیحت رو ساده و روان بده، همراه با یه مثال ملموس، و از اصطلاحات تخصصی پرهیز کن.",
    "نیمه‌تخصصی": "توضیحت باید هم با مثال ملموس همراه باشه، هم از لحن آکادمیک/تخصصیِ رایج استفاده کنه.",
    "تخصصی": "توضیحت رو کاملاً آکادمیک، دقیق و با عمق فنی بده.",
}

BG_COLOR = "#0f1115"
USER_BUBBLE_COLOR = "#2663d9"
BOT_BUBBLE_COLOR = "#2e2f38"
HEADER_COLOR = "#191b21"


def strip_thinking(text):
    """بخش «فرآیند فکر کردن» مدل رو از جواب نهایی حذف می‌کنه"""
    if not text:
        return text
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    return cleaned.strip() or text.strip()


class ChatbotApp(toga.App):

    def startup(self):
        self.response_level = "نیمه‌تخصصی"
        self.conversation_history = [{"role": "system", "content": self._full_system_prompt()}]

        main_box = toga.Box(style=Pack(direction=COLUMN, flex=1, background_color=BG_COLOR))

        header = toga.Box(style=Pack(direction=ROW, padding=12, background_color=HEADER_COLOR))
        title_label = toga.Label(
            "دستیار هوشمند",
            style=Pack(flex=1, font_size=17, color="#ffffff", text_align="center"),
        )
        header.add(title_label)
        main_box.add(header)

        self.messages_box = toga.Box(style=Pack(direction=COLUMN, padding=10))
        scroll_container = toga.ScrollContainer(
            content=self.messages_box, style=Pack(flex=1), horizontal=False
        )
        main_box.add(scroll_container)

        input_box = toga.Box(style=Pack(direction=ROW, padding=10))
        self.text_input = toga.TextInput(
            style=Pack(flex=1, padding_right=8, text_align="right"),
            placeholder="پیامت رو بنویس...",
        )
        send_button = toga.Button("ارسال", on_press=self.on_send, style=Pack(width=90))
        input_box.add(self.text_input)
        input_box.add(send_button)
        main_box.add(input_box)

        self.add_message("سلام! چطور می‌تونم کمکت کنم؟", is_user=False)
        if API_KEY == "اینجا_کلید_API_رو_بذار":
            self.add_message("⚠️ هنوز کلید API رو توی کد نذاشتید!", is_user=False)

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = main_box
        self.main_window.show()

    def _full_system_prompt(self):
        return BASE_PROMPT + " " + LEVEL_PROMPTS[self.response_level]

    def add_message(self, text, is_user):
        bubble = toga.Box(
            style=Pack(
                direction=COLUMN,
                padding=10,
                background_color=USER_BUBBLE_COLOR if is_user else BOT_BUBBLE_COLOR,
            )
        )
        label = toga.Label(
            text,
            style=Pack(color="#ffffff", text_align="right", font_size=14),
        )
        bubble.add(label)

        row = toga.Box(style=Pack(direction=ROW, padding_bottom=8))
        spacer = toga.Box(style=Pack(flex=1))
        if is_user:
            row.add(spacer)
            row.add(bubble)
        else:
            row.add(bubble)
            row.add(spacer)

        self.messages_box.add(row)
        return label

    def on_send(self, widget):
        user_text = self.text_input.value.strip() if self.text_input.value else ""
        if not user_text:
            return
        self.text_input.value = ""
        self.add_message(user_text, is_user=True)
        thinking_label = self.add_message("در حال فکر کردن...", is_user=False)

        threading.Thread(target=self._get_ai_response, args=(user_text, thinking_label)).start()

    def _get_ai_response(self, user_text, thinking_label):
        self.conversation_history.append({"role": "user", "content": user_text})

        headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
        data = {
            "model": VISION_MODEL,
            "messages": self.conversation_history,
            "temperature": 0.3,
            "max_completion_tokens": 2000,
        }

        try:
            response = requests.post(URL, headers=headers, json=data, timeout=45)
            response.raise_for_status()
            result = response.json()
            reply = strip_thinking(result["choices"][0]["message"]["content"])
            self.conversation_history.append({"role": "assistant", "content": reply})
        except Exception as e:
            reply = f"خطا: {e}"

        def update_ui():
            thinking_label.text = reply

        self.loop.call_soon_threadsafe(update_ui)



def main():
    return ChatbotApp(formal_name="دستیار هوشمند (Toga)", app_id="org.mychatbottoga.aiassistant")
