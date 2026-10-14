# BigBoard — AI Telegram bot for an outdoor advertising agency

An AI-powered Telegram assistant that answers customer questions, estimates prices and collects leads for a (fictional) outdoor advertising agency.

👉 **Try it live:** [@artmin_ads_demo_bot](https://t.me/artmin_ads_demo_bot)

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![aiogram](https://img.shields.io/badge/aiogram-3-26A5E4?logo=telegram&logoColor=white)
![Gemini](https://img.shields.io/badge/Google_Gemini-API-8E75B2?logo=googlegemini&logoColor=white)

## ✨ Features

- 🤖 **AI consultant** — understands free-form questions ("how much is a billboard near the metro for 2 months?") and answers strictly based on the price list and FAQ, without making things up
- 🧮 **Price estimates** — calculates a rough cost from the price list
- ✍️ **Lead capture** — step-by-step form: name → phone (one-tap contact sharing) → service → comment
- 🔔 **Instant notifications** — every new lead is sent to the manager in Telegram
- 📊 **Lead storage** — leads are saved to a CSV file that opens in Excel
- 📋 **Menu** with services, prices, FAQ and contacts
- 🛡 **Fallback models** — if one AI model is overloaded, the bot automatically switches to another

## 🔄 Easy to adapt

All business content (services, prices, FAQ, contacts) lives in one file — [`content.py`](content.py). The AI uses the same file as its knowledge base, so adapting the bot for a beauty salon, car service or online store means editing texts, not code.

## 🧱 Project structure

```
bot.py       — Telegram handlers: menu, lead form, AI chat
ai.py        — Gemini integration, system prompt, dialog memory
content.py   — business texts: services, prices, FAQ, contacts
leads.py     — saving leads to CSV
```

## 🚀 Run locally

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # then fill in the values
python bot.py
```

`.env` settings:

| Variable | Description |
|---|---|
| `BOT_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather) |
| `ADMIN_CHAT_ID` | Chat that receives new leads (send `/myid` to the bot to get it) |
| `GEMINI_API_KEY` | Key from [Google AI Studio](https://aistudio.google.com) — optional, without it the bot works by buttons only |
| `GEMINI_MODEL` | Model list, comma-separated (first available is used) |

---

## 🇷🇺 Кратко по-русски

ИИ-бот для агентства наружной рекламы: отвечает на вопросы клиентов свободным текстом, считает примерную стоимость по прайсу, собирает заявки и присылает их менеджеру в Telegram. Под другой бизнес адаптируется заменой текстов в `content.py`.

**Нужен похожий бот для вашего бизнеса?** Пишите — [GitHub @ARTmin05](https://github.com/ARTmin05).
