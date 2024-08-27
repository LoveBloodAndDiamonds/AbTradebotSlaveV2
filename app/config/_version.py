__all__ = ["VERSION", "DB_VERSION", ]

# Определяем версию приложения, это важно, потому что главный сервер не будет
# поддерживать устаревшие версии клиентов.
VERSION: str = "2.04"

# Каждый раз, когда мы изменяем базу данных - необходимо менять название таблицы, чтобы не
# делать миграции на компьютерах пользователей.
DB_VERSION: str = "204"
