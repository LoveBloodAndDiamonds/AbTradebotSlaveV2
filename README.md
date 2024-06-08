# Клиент для работы с AbTradebotMaster
![alt text](static/app_icon.ico)

---


### Windows
[Ссылка на установщик](portable/Windows/AbTradebotInstaller.exe)<br>

Правила запуска:
- [Синхронизация времени с сетью](portable/Windows/TimeSync.bat)
- Скачивание установщика желательно через Egde или Mozilla
- Запуск установщика и синхронизатора от имени администратора


---

### MacOS
(Пока недоступно)<br>

---

### Linux
Инструкция на Linux рассчитана на продвинутого пользователя, многие моменты
пропущены.

<i>Внимание, данная инструкция не является документом, к которому можно высказать 
претензию, установка на разных версиях ОС, на серверах с разным пакетом 
предустановленных программ, и разным доступом к командам может отличаться.</i><br>

1. Обновите список доступных пакетов:
   ```shell
   sudo apt update
   ```
2. Обновите пакеты:
   ```shell
   sudo apt upgrade
   ```
3. Установите менеджер пакетов для python:
    ```shell
    sudo apt install python-pip
    ```
4. Скопируйте репозиторий или перенесите проект через SFTP в папку root/:
   ```shell
   git clone https://github.com/LoveBloodAndDiamonds/AbTradebotSlaveV2.git
   ```
5. Перейдите в директорию проекта используя команду cd (зависит от того,
в какой директории Вы сейчас, доступные каталоги для перехода можно узнать 
используя команду 'ls' или 'ls -a')
    ```shell
    cd AbTradebotSlaveV2
    ```
6. Перейдите в директорию, которая содержит файлы для настройки клиента
на linux сервер.
    ```shell
    cd .linux
    ```
7. Заполните secrets.json.dist и переменуйте его в secrets.json
используя консольный тектовый редактор nano (гайд по использованию можно
посмотреть на YouTube)
    ```shell
   nano secrets.json.dist
    ```
8. Используя Makefile переместите и запустите сервис, который позволит 
запустить программу в фоновым режим и с автоматическим перезапуском
    ```shell
   make move-service && make run-service
    ```

Логи можно посмотреть введя команду:
```shell
sudo systemctl status app
```

Файл с логами находится в корне сервера, в папке "AbTradebot", база данных находится там же.

---

### Compile Notes:

#### Windows:
```shell
nuitka --follow-imports --include-package=websockets --standalone --windows-icon-from-ico=static/app_icon.ico app/__main__.py
```

#### MacOS:
ModuleNotFoundError:
    traceback like "no module named 'app' in 11 str'"
    pyinstaller -F --target-arch arm64 --argv-emulation app/__main__.py
