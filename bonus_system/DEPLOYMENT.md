# Инструкция по развертыванию приложения

## Варианты развертывания

### 1. PythonAnywhere (Рекомендуется для начала)

**Преимущества:**
- Бесплатный план доступен
- Простая настройка
- Поддержка Django из коробки

**Шаги:**
1. Зарегистрируйтесь на https://www.pythonanywhere.com
2. Создайте новый веб-приложение (Web tab)
3. Загрузите код через Git или файловый менеджер
4. Установите зависимости: `pip3.10 install --user django`
5. Настройте WSGI файл для вашего приложения
6. Настройте статические файлы и медиа
7. Выполните миграции: `python3.10 manage.py migrate`
8. Создайте суперпользователя: `python3.10 manage.py createsuperuser`

### 2. Railway

**Преимущества:**
- Бесплатный план с ограничениями
- Автоматическое развертывание из Git
- Простая настройка

**Шаги:**
1. Зарегистрируйтесь на https://railway.app
2. Подключите ваш GitHub репозиторий
3. Railway автоматически определит Django проект
4. Добавьте переменные окружения (SECRET_KEY, DATABASE_URL)
5. Railway автоматически развернет приложение

### 3. Render

**Преимущества:**
- Бесплатный план доступен
- Автоматическое развертывание
- PostgreSQL в комплекте

**Шаги:**
1. Зарегистрируйтесь на https://render.com
2. Создайте новый Web Service
3. Подключите GitHub репозиторий
4. Настройте:
   - Build Command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
   - Start Command: `gunicorn bonus_system.wsgi:application`
5. Добавьте переменные окружения
6. Выполните миграции через shell

### 4. VPS (DigitalOcean, AWS, Hetzner)

**Преимущества:**
- Полный контроль
- Масштабируемость
- Производительность

**Шаги:**
1. Создайте VPS (Ubuntu 22.04)
2. Установите Python, PostgreSQL, Nginx
3. Настройте Gunicorn как WSGI сервер
4. Настройте Nginx как reverse proxy
5. Настройте SSL через Let's Encrypt
6. Настройте автоматическое развертывание

## Подготовка к развертыванию

### 1. Установите зависимости

Файл `requirements.txt` уже создан. Установите зависимости:

```bash
cd bonus_system
pip install -r requirements.txt
```

### 2. Обновите settings.py для production

Добавьте:
- `DEBUG = False`
- `ALLOWED_HOSTS = ['your-domain.com']`
- Настройки для статических файлов
- Настройки базы данных (PostgreSQL рекомендуется)

### 3. Создайте .env файл для секретных данных

```env
SECRET_KEY=your-secret-key
DEBUG=False
DATABASE_URL=postgresql://user:password@host:port/dbname
```

### 4. Выполните миграции

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Соберите статические файлы

```bash
python manage.py collectstatic
```

## Рекомендации

- Используйте PostgreSQL вместо SQLite для production
- Настройте резервное копирование базы данных
- Используйте переменные окружения для секретных данных
- Настройте SSL/HTTPS
- Регулярно обновляйте зависимости
