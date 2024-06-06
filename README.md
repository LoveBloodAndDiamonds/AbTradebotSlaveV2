# Клиент для работы с AbTradebotMaster
![alt text](static/app_icon.ico)

---


### Windows
[Ссылка на установщик](compiled/Windows)

---

### MacOS
(Пока недоступно)<br>
[Ссылка на скачивание программы](compiled/MacOS)

---

### Linux
Инструкция на Linux рассчитана на продвинутого пользователя, многие моменты
пропущены.

1. Склонируйте репозиторий
   ```shell
   git clone https://github.com/LoveBloodAndDiamonds/AbTradebotSlaveV2.git
   ```
2. Заполните .linux/secrets.json.dist и переменуйте его в secrets.json
    ```shell
   nano ./linux/secrets.json.dist
    ```
3. Установите зависимости и запустите.
    ```shell
   python3 -m app
   ```

В будущем будет дописан .service  для автоматического перезапуска
приложения после перезагрузки сервера.

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
