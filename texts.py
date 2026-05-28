HELP_TITLE = "Я могу ответить на следующие команды:"
HELP_LINES = [
    "/help - этот текст",
    "/neko - отправляет картинку с кошкодевочкой",
    "/animetoday - какое аниме выходит сегодня",
    "/animes - аниме этого сезона",
    "/tldr - суммаризация последних сообщений беседы",
]

START_TEXT = "Hi!\nI send catgirls and anime schedules."
NEKO_CAPTION = "Держи кошкодевочку!"
TLDR_PREFIX = "Вкратце в предыдущих сообщениях:\n"
ANIME_DAY_PREFIX = "С субтитрами выходят аниме:"
ANIME_TODAY_PREFIX = "Сегодня {day_label}, и выходят с субтитрами аниме:\n"
ANIME_PICK_DAY = "*Выберите день*:\n"
ANIME_PICK_TITLE = "*Выберите аниме*:\n"
MORE_DETAILS = "Подробнее"
BACK = "Назад"
KEK = "КЕК!"

ADMIN_UPDATED = "Updated"
ADMIN_NOTHING_TO_SAVE = "Error: Nothing to save"
ADMIN_ALREADY_EXISTS = "Error: {error}"
ADMIN_DOWNLOADED_ID = "Downloaded id: {file_info}"
ADMIN_DOWNLOADED_MD5 = "Downloaded md5: {file_md5}"
ADMIN_DEBUG = "Chat ID: {chat_id} UID :{user_id}"

HELP_LINES.append("/factcheck - проверка утверждений в посте через DeepSeek")
FACTCHECK_PREFIX = "Проверка утверждений:\n"
FACTCHECK_USAGE = (
    "Используйте /factcheck ответом на пост "
    "или передайте текст утверждения после команды."
)
FACTCHECK_UNAVAILABLE = "DeepSeek для /factcheck не настроен."
FACTCHECK_FAILED = "Не удалось выполнить /factcheck через DeepSeek."

