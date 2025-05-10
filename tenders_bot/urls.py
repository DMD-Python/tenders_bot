# Файл маршрутизации (routing) HTTP-запросов проекта Django.
# указывает какие URL-адреса обрабатываются какими функциями (views).

# Импорт стандартных компонентов Django для маршрутизации
from django.http import HttpResponse         # Для простого текстового ответа на HTTP-запрос
from django.conf import settings             # Импорт настроек проекта (settings.py)
from django.conf.urls.static import static   # Функция для раздачи медиафайлов в режиме разработки
from django.contrib import admin             # Панель администратора Django
from django.urls import path                 # Функция для объявления маршрутов

# Функция представления view, показывает приветственное сообщение на главной странице

def home(request):
    return HttpResponse("Добро пожаловать в Telegram-бот Департамента тендеров и закупок!")

# Список маршрутов (URL-шаблонов) проекта
urlpatterns = [
    path("", home, name="home"),        # Маршрут главной страницы сайта (доступна по адресу /)
    path("admin/", admin.site.urls),    # Маршрут административной панели Django (по адресу /admin/)
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Кастомизация панели администратора
admin.site.site_header = "Telegram Bot Administration"         # Заголовок админ-панели (в шапке)
admin.site.site_title = "Бот Департамента тендеров и закупок"  # Название сайта (в окне браузера)
admin.site.index_title = "Управление Telegram Ботом"           # Заголовок главной страницы админ-панели
