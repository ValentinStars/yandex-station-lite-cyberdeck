# 💽 Yandex Station Lite Cyberdeck (yandexmicro)

<div align="center">

```text
  __   __             _             _____ _        _   _              
  \ \ / /_ _ _ _  __| |_____ __   / ____| |      | | (_)             
   \ V / _` | ' \/ _` / -_) \ /  | (___ | |_ __ _| |_ _  ___  _ __    
    |_|\__,_|_||_\__,_\___/_\_\   \___ \| __/ _` | __| |/ _ \| '_ \   
                                  ____) | || (_| | |_| | (_) | | | |  
                                 |_____/ \__\__,_|\__|_|\___/|_| |_|  
              --- CYBERDECK 2007 AERO EDITION ---                     
```

[![Platform](https://img.shields.io/badge/SoC-Amlogic%20A113X%20AXG-red.svg)](https://www.amlogic.com)
[![Architecture](https://img.shields.io/badge/Arch-aarch64%20(64--bit)-blue.svg)]()
[![Kernel](https://img.shields.io/badge/Kernel-Linux%204.9.68-green.svg)]()
[![OS](https://img.shields.io/badge/OS-Quasar%20Buildroot%20+%20Entware-orange.svg)]()
[![Web UI](https://img.shields.io/badge/UI-Windows%20Vista%202007%20Web%202.0-yellow.svg)]()
[![License](https://img.shields.io/badge/License-MIT-purple.svg)]()

**Превращение умной колонки Яндекс Станция Лайт (1-е поколение, `YNDX-00025`, `yandexmicro`) в автономный Linux Cyberdeck / DJ скретч-станцию / Вардрайвинг-комбайн с веб-интерфейсом в стиле 2007 года.**

[Аппаратная архитектура](docs/hardware.md) • [Реверс протоколов](docs/protocols.md) • [Anti-OTA & Root](docs/anti_ota.md) • [Web Панель](#-веб-интерфейс-2007-года)

</div>

---

## ⚡ Ключевые возможности

* 🎧 **DJ Вики-Вики (Vinyl Scratch Engine):**  
  Интерактивный скретч-эффект на 100 Гц емкостном датчике взмахов (`AW9610X SAR`). Взмахиваешь ладонью над станцией — и она выдает сочные виниловые скретчи через динамик в реальном времени!
* 🌈 **Liquid RGB Wave (Перелив без белизны):**  
  После 5 секунд бездействия кольцо плавно запускает медленный глубокий перелив чистых спектральных цветов (Red $\rightarrow$ Green $\rightarrow$ Blue $\rightarrow$ Magenta) без выбелений. При приближении руки мгновенно гаснет.
* 💽 **Web Cyberdeck в стиле 2007 года (Порт 8888):**  
  Интерфейс в эстетике **Windows Vista Aero Glass / Winamp 5 / Web 2.0**: бегущие строки `<marquee>`, неоновые дисплеи, стеклянные кнопки Aqua и 88x31 ретро-бейджы.
* 🤫 **Silent Hardware API (`alice-cmd`):**  
  Прямая инъекция событий в Linux Input Subsystem (`/dev/input/event1` key 582/115/114/113). Мгновенно ставит на паузу, регулирует звук и отправляет тихие текстовые команды Алисе в `DirectiveSequencer` без использования микрофона.
* 📡 **16-MFSK Акустический модем:**  
  Синтезатор звуковых частот первичной настройки Яндекса (1140–4740 Гц). Позволяет сопрягать Wi-Fi и передавать данные звуком прямо из браузера смартфона через Web Audio API.
* 🛡️ **Permanent Root & Anti-OTA Cementing:**  
  Официальная прошивка зацементирована (RSA-ключи обновлений подменены, апдейтер заглушен), Dropbear SSH на порту `:2222`, Entware (`opkg`) и BetterYAM активны.
* 🚀 **ZRAM 128MB Swap & USB-Host OTG:**  
  Активирован USB Host стек (драйверы Wi-Fi адаптеров `ath9k_htc`, `rt2800usb`, накопителей `usb-storage`, `r8152`) и сжатый LZO своп в оперативной памяти.

---

## 📂 Структура репозитория

```text
├── bin/
│   ├── alice-cmd          # Утилита тихого управления (Key 582, Vol+/-, тихий ввод)
│   ├── ambient-lights     # Демон 5-секундного глубокого RGB-перелива (Pure Hue)
│   ├── dj-live            # Интерактивный движок DJ-скретча на взмахи ладони (100 Hz)
│   ├── dj-record          # Рекордер траектории жестов с ASCII-визуализацией
│   ├── chirp-gen          # 16-MFSK синтезатор аудио-чирпов Яндекса
│   ├── led-fx             # CLI управление кольцом светодиодов (police, rainbow, spin)
│   ├── play-audio         # Универсальный плеер WAV/MP3/OPUS через GStreamer/ALSA
│   ├── yandex-micro-kit.sh# Anti-OTA цементатор и установщик постоянного SSH
│   └── zram-swap.sh       # Менеджер 128MB ZRAM свопа в RAM
├── web/
│   └── server.py          # Веб-сервер Cyberdeck 2007 года + REST API на порту 8888
├── services/
│   ├── S96ambientlights   # Init-скрипт автозагрузки фонового перелива
│   ├── S97otg-host        # Init-скрипт инициализации USB OTG и ZRAM
│   ├── S98chirpweb        # Init-скрипт веб-интерфейса 2007 года
│   └── S99zdropbear       # Init-скрипт Dropbear SSH (порт 2222)
├── audio/
│   ├── scratch_fwd.wav    # Виниловый скретч вперед
│   ├── scratch_bwd.wav    # Виниловый скретч назад
│   └── scratch_combo.wav  # Комбо "Вики-Вики"
└── docs/
    ├── hardware.md        # Разводка платы, UART, тестпоинты, чипы I2C
    ├── protocols.md       # Реверс 16-MFSK звукового протокола и Input Subsystem
    └── anti_ota.md        # Инструкция по даунгрейду и фиксации прошивки
```

---

## 🚀 Быстрый старт

### 1. Подключение к колонке
```bash
ssh -p 2222 root@192.168.1.127
```

### 2. Запуск DJ Вики-Вики
Помаши рукой туда-сюда над верхней панелью колонки:
```bash
dj-live
```
* **Взмах вправо:** `ВИК!`
* **Взмах влево:** `ВАК!`
* **Быстро туда-сюда:** `🔥 ВИКИ-ВИКИ СКРЕТЧ!`

### 3. Тихий пульт управления (`alice-cmd`)
```bash
alice-cmd pause        # Аппаратный Play/Pause/Stop (Key 582)
alice-cmd volup        # Громче (+)
alice-cmd voldn        # Тише (-)
alice-cmd mute         # Mute микрофона
alice-cmd query "стоп" # Тихая голосовая команда Алисе без микрофона
```

### 4. Веб-интерфейс 2007 года
Открой в браузере смартфона или ПК:  
👉 **`http://192.168.1.127:8888`**

---

## 📡 REST API (для умного дома и скриптов)

| Эндпоинт | Метод | Описание |
| :--- | :---: | :--- |
| `/api/pause` | `GET` / `POST` | Поставить на паузу / снять с паузы (Key 582) |
| `/api/volup` | `GET` / `POST` | Увеличить громкость |
| `/api/voldn` | `GET` / `POST` | Уменьшить громкость |
| `/api/mute` | `GET` / `POST` | Переключить Mute микрофона |
| `/api/query?q=<текст>` | `GET` / `POST` | Отправить тихий запрос в DirectiveSequencer |

---

## 🛠️ Аппаратные особенности (Amlogic A113X)

* **Ёмкостные зоны (AW9610X SAR):**  
  Сенсор опрашивается через sysfs:
  ```bash
  cat /sys/devices/platform/soc/ffd00000.cbus/ffd1f000.i2c/i2c-0/0-0012/diff
  ```
  * Фоновый шум: `-10...+40`
  * Осознанный взмах: `+150...+4380` (порог детекции установлен на `140`).
* **Аудиоусилитель NTP8910A:**  
  Работает по шине I2S через ALSA `hw:0,0`. Аппаратный мьют доступен через `amixer sset 'SPK mute' on/off`.

---

## 📜 Лицензия
MIT License. Создано в исследовательских целях для превращения закрытого IoT-железа в открытую хакерскую платформу.
