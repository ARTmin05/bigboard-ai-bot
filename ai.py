"""ИИ-консультант на Gemini: отвечает на вопросы клиентов по прайсу и FAQ."""

import logging
import os
import re
from collections import defaultdict, deque

from dotenv import load_dotenv
from google import genai
from google.genai import types

import content

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Можно указать несколько моделей через запятую — запасные на случай перегрузки
GEMINI_MODELS = [
    m.strip()
    for m in os.getenv("GEMINI_MODEL", "gemini-flash-latest,gemini-3.5-flash,gemini-flash-lite-latest").split(",")
    if m.strip()
]

# Метка, которой ИИ сообщает: «клиент готов оставить заявку»
LEAD_MARKER = "[ЗАЯВКА]"

HISTORY_SIZE = 10  # сколько последних сообщений помнить в диалоге


def _plain(text: str) -> str:
    """Убирает HTML-теги из текстов content.py для промпта."""
    return re.sub(r"<[^>]+>", "", text)


SYSTEM_PROMPT = f"""Ты — вежливый менеджер-консультант агентства «{content.COMPANY_NAME}» в Telegram.

Отвечай ТОЛЬКО на основе информации ниже. Если чего-то в ней нет (точные адреса,
наличие конкретных мест, индивидуальные скидки) — честно скажи, что это уточнит менеджер,
и предложи оставить заявку. Не выдумывай цены и условия.

Правила:
- Пиши коротко: 2–5 предложений, по-русски, дружелюбно.
- Простой текст без markdown: без звёздочек, решёток и таблиц. Списки — через «•».
- Если клиент просит посчитать примерную стоимость — посчитай по ценам «от», явно скажи,
  что это ориентир.
- Если клиент хочет заказать, просит перезвонить или оценка уже дана —
  добавь в самый конец ответа метку {LEAD_MARKER}.
- На вопросы не про рекламу вежливо возвращай разговор к услугам агентства.

=== УСЛУГИ И ЦЕНЫ ===
{chr(10).join(_plain(description) for _, description in content.SERVICES.values())}

=== ЧАСТЫЕ ВОПРОСЫ ===
{_plain(content.FAQ)}

=== КОНТАКТЫ ===
{_plain(content.CONTACTS)}
"""

_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
_history: dict[int, deque] = defaultdict(lambda: deque(maxlen=HISTORY_SIZE))


def is_enabled() -> bool:
    return _client is not None


async def ask(user_id: int, question: str) -> tuple[str, bool]:
    """Возвращает (ответ, хочет_ли_клиент_оставить_заявку)."""
    history = _history[user_id]
    history.append(types.Content(role="user", parts=[types.Part(text=question)]))

    answer = None
    for model in GEMINI_MODELS:  # если модель перегружена — пробуем следующую
        try:
            response = await _client.aio.models.generate_content(
                model=model,
                contents=list(history),
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.4,
                    # с запасом: новые модели тратят часть лимита на «размышления»
                    max_output_tokens=2048,
                ),
            )
            answer = (response.text or "").strip()
            break
        except Exception as e:
            logging.warning("Gemini %s не ответил: %s", model, str(e)[:120])

    if not answer:
        history.pop()  # не сохраняем вопрос без ответа
        return ("Извините, сейчас не получается ответить. "
                "Оставьте заявку — менеджер ответит лично.", True)

    wants_lead = LEAD_MARKER in answer
    answer = answer.replace(LEAD_MARKER, "").strip()
    history.append(types.Content(role="model", parts=[types.Part(text=answer)]))
    return answer, wants_lead


def reset(user_id: int) -> None:
    _history.pop(user_id, None)
