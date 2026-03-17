import feedparser
import random
import logging

# ─────────────────────────────────────────────
# RSS ЛЕНТЫ ПО ТЕМАМ
# ─────────────────────────────────────────────

FEEDS = {
    "🐍 Python": [
        "https://realpython.com/atom.xml",
        "https://feeds.feedburner.com/PythonInsider",
        "https://planetpython.org/rss20.xml",
    ],

    "💻 Программирование в целом": [
        "https://habr.com/ru/rss/flows/develop/articles/",       # Хабр разработка
        "https://habr.com/ru/rss/hubs/programming/articles/",    # Хабр программирование
        "https://dev.to/feed/tag/programming",
        "https://feeds.feedburner.com/codinghorror",             # Coding Horror (Jeff Atwood)
        "https://martinfowler.com/feed.atom",                    # Martin Fowler
    ],

    "🐧 Linux": [
        "https://www.linux.org/articles/index.rss",
        "https://habr.com/ru/rss/hubs/linux/articles/",
        "https://linuxhandbook.com/feed/",
        "https://itsfoss.com/feed/",
        "https://www.phoronix.com/rss.php",
    ],

    "🐳 Технологии (Git, Docker и др.)": [
        "https://dev.to/feed/tag/docker",
        "https://dev.to/feed/tag/git",
        "https://dev.to/feed/tag/devops",
        "https://habr.com/ru/rss/hubs/devops/articles/",
        "https://github.blog/feed/",                             # GitHub официальный блог
    ],

    "🌐 Веб-разработка": [
        "https://css-tricks.com/feed/",
        "https://dev.to/feed/tag/webdev",
        "https://www.smashingmagazine.com/feed/",
        "https://habr.com/ru/rss/hubs/webdev/articles/",
    ],

    "🚀 Интересные проекты": [
        "https://github.blog/feed/",
        "https://dev.to/feed/tag/opensource",
        "https://habr.com/ru/rss/hubs/open_source/articles/",
        "https://news.ycombinator.com/rss",                      # Hacker News
    ],

    "🧠 Методы и практики программирования": [
        "https://martinfowler.com/feed.atom",                    # Паттерны, рефакторинг
        "https://dev.to/feed/tag/algorithms",
        "https://dev.to/feed/tag/cleancode",
        "https://dev.to/feed/tag/architecture",
        "https://habr.com/ru/rss/hubs/refactoring/articles/",
    ],

    "👨‍💻 Программисты и их истории": [
        "https://feeds.feedburner.com/codinghorror",             # Jeff Atwood (Stack Overflow)
        "https://martinfowler.com/feed.atom",                    # Martin Fowler
        "https://blog.cleancoder.com/atom.xml",                  # Robert Martin (Uncle Bob)
        "https://overreacted.io/rss.xml",                        # Dan Abramov (React)
        "https://www.joelonsoftware.com/feed/",                  # Joel Spolsky
    ],
}

# Все ленты одним списком с меткой темы
ALL_FEEDS = [(theme, url) for theme, urls in FEEDS.items() for url in urls]


# ─────────────────────────────────────────────
# ПОЛУЧЕНИЕ СТАТЬИ
# ─────────────────────────────────────────────

def fetch_random_article() -> dict | None:
    """
    Берёт случайную RSS-ленту, возвращает случайную статью из неё.
    Возвращает dict с ключами: theme, title, link, summary
    """
    random.shuffle(ALL_FEEDS)

    for theme, url in ALL_FEEDS:
        try:
            feed = feedparser.parse(url)
            entries = feed.entries[:15]  # берём 15 свежих

            if not entries:
                continue

            article = random.choice(entries)

            title = article.get("title", "Без заголовка").strip()
            link = article.get("link", "").strip()

            # Краткое описание (если есть)
            summary = article.get("summary", "")
            if summary:
                # Обрезаем до 200 символов
                summary = summary[:200].strip()
                # Убираем HTML-теги грубо
                import re
                summary = re.sub(r"<[^>]+>", "", summary).strip()
                if len(summary) > 200:
                    summary = summary[:200] + "..."

            return {
                "theme": theme,
                "title": title,
                "link": link,
                "summary": summary,
            }

        except Exception as e:
            logging.warning(f"Ошибка при парсинге {url}: {e}")
            continue

    return None  # если все ленты недоступны


def format_article(article: dict) -> str:
    """Форматирует статью для отправки в Telegram"""
    text = f"{article['theme']}\n\n"
    text += f"*{article['title']}*\n"

    if article["summary"]:
        text += f"\n{article['summary']}\n"

    text += f"\n🔗 {article['link']}"
    return text