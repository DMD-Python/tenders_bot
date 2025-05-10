# Импортируем базовый модуль моделей Django
from django.db import models

# Модель Node - узел дерева меню чат-бота
class Node(models.Model):
    # Текст кнопки, которая будет отображаться в меню бота
    button_text = models.CharField(max_length=50, null=True, blank=False)

    # Основной текст, который бот отправляет при входе в этот узел
    text = models.TextField(max_length=4096, null=True, blank=True)

    # Отдельный текст, который будет показан над inline-кнопками навигации
    nav_text = models.CharField(max_length=255, null=False, blank=False, default="-")

    # Связь с родительским узлом (self-связь), формирует дерево
    parent_node = models.ForeignKey(
    "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="child_nodes" # дочерние узлы доступны как .child_nodes
    )

    # Название функции (если нужно вводить данные в этом узле)
    input_function = models.CharField(max_length=50, default=None, null=True, blank=True)

    # Поле path используется для отображения полного пути от корня до узла
    path = models.CharField(max_length=1000, editable=False, null=True, default=None)

    # Поле сортировки кнопок в меню (чем меньше значение — тем выше в списке)
    button_order = models.PositiveIntegerField(default=0, blank=False, null=False, db_index=True)

    class Meta:
        verbose_name = "узел"
        verbose_name_plural = "узлы"
        ordering = ["button_order"] # сортировка по порядку кнопок в меню

    # Переопределяем метод сохранения модели
    def save(self, *args, **kwargs):
        self.update_path()
        super(Node, self).save(*args, **kwargs)

    # Метод обновления path (используется для отображения структуры дерева)
    def update_path(self):
        self.path = self.button_text
        if self.parent_node is not None:
            self.path = f"{self.parent_node.path} – {self.path}" # рекурсивное построение пути

        # Рекурсивно обновляем путь у всех дочерних узлов
        if self.pk is not None:
            for node in self.child_nodes.only("id", "path", "parent_node", "button_text"):
                node.save(update_fields=["path"])

    # Представление узла в админ-панели
    def __str__(self):
        return self.path

# Модель File — прикреплённые файлы к узлам (Node)
class File(models.Model):
    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to="nodes_content/")

    def __str__(self):
        return self.file.name

# Модель Feedback — обращение пользователя из Telegram
# Вся информация, введённая пользователем в чат-боте, сохраняется здесь
class Feedback(models.Model):
    class Meta:
        verbose_name = "обращение"
        verbose_name_plural = "обращения"

    # Варианты типов обращения (оставляем только GENERAL в данном релизе, два других резервные на будущее расширение функционала)
    class FeedbackType(models.TextChoices):
        GENERAL = "GENERAL", "Обратная связь"
#        CONTRACT_TEMPLATE_CONTRACTOR = "CONTRACT_TEMPLATE_CONTRACTOR", "резерв Шаблон договора подрядчика"
#        CONTRACT_TEMPLATE_SUPPLIER = "CONTRACT_TEMPLATE_SUPPLIER", "резерв Шаблон договора поставщика"

    # Метка времени создания обращения
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Время обращения")

    # Telegram ID чата и ID последнего отправленного ботом сообщения
    telegram_chat_id = models.PositiveIntegerField(null=True, verbose_name="ID чата в Telegram")
    telegram_sent_message_id = models.PositiveIntegerField(null=True, verbose_name="ID сообщения в Telegram")

    # Информация о пользователе Telegram (если доступна)
    telegram_username = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Имя пользователя в Telegram"
    )
    telegram_first_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Имя в Telegram")
    telegram_last_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Фамилия в Telegram")

    # Поля, заполняемые пользователем в форме обратной связи
    name = models.CharField(max_length=255, null=True, blank=True, verbose_name="ФИО")
    contact_number = models.CharField(max_length=255, null=True, blank=True, verbose_name="Номер телефона")
    email = models.CharField(max_length=255, null=True, blank=True, verbose_name="Email")
    company = models.CharField(max_length=255, null=True, blank=True, verbose_name="Компания")
    inn = models.CharField(max_length=255, null=True, blank=True, verbose_name="ИНН")
    text = models.TextField(max_length=4096, null=True, blank=True, verbose_name="Текст обращения")

    # Тип формы, по умолчанию GENERAL (сейчас один, далее дополнительные на развитие функционал по договорам)
    type = models.CharField(
        max_length=255, choices=FeedbackType.choices, default=FeedbackType.GENERAL, verbose_name="Тип запроса"
    )

    # Флаг, обработано ли обращение (сотрудником или администратором)
    processed = models.BooleanField(default=False, verbose_name="Обработано")

    # Внутренний флаг: отправлено ли обращение (по кнопке "Отправить")
    submitted = models.BooleanField(default=False)

    # Комментарий администратора (для использования в админ-панели)
    comment = models.CharField(max_length=500, null=True, blank=True, verbose_name="Комментарий")

    # Следующее поле для ввода в форме (техническое поле, для маршрутизации)
    next_field = models.CharField(max_length=255, null=True)

# Модель UserUploadedFile — файлы, загруженные пользователем
# Каждый файл связан с обращением Feedback (один ко многим)
class UserUploadedFile(models.Model):
    feedback = models.ForeignKey(Feedback, on_delete=models.CASCADE, related_name="uploaded_files")
    file = models.FileField(upload_to="user_uploads/")
