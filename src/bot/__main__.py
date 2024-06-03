import asyncio


async def _startup_user_dialog() -> None:
    ...


async def main() -> None:
    """
    Точка входа в приложение.
    :return:
    """
    await _startup_user_dialog()


if __name__ == '__main__':
    asyncio.run(main())
