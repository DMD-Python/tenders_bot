from django.db import models


class Node(models.Model):
    button_text = models.CharField(max_length=50, null=True, blank=False)
    text = models.TextField(max_length=4096, null=True, blank=True)
    nav_text = models.CharField(max_length=255, null=False, blank=False, default="-")
    parent_node = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="child_nodes"
    )
    input_function = models.CharField(max_length=50, default=None, null=True, blank=True)
    path = models.CharField(max_length=1000, editable=False, null=True, default=None)
    button_order = models.PositiveIntegerField(default=0, blank=False, null=False, db_index=True)

    class Meta:
        verbose_name = "узел"
        verbose_name_plural = "узлы"
        ordering = ["button_order"]

    def save(self, *args, **kwargs):
        self.update_path()
        super(Node, self).save(*args, **kwargs)

    def update_path(self):
        self.path = self.button_text
        if self.parent_node is not None:
            self.path = f"{self.parent_node.path} – {self.path}"
        if self.pk is not None:
            for node in self.child_nodes.only("id", "path", "parent_node", "button_text"):
                node.save(update_fields=["path"])

    def __str__(self):
        return self.path


class File(models.Model):
    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to="nodes_content/")

    def __str__(self):
        return self.file.name


class Feedback(models.Model):
    class Meta:
        verbose_name = "обращение"
        verbose_name_plural = "обращения"

    class FeedbackType(models.TextChoices):
        GENERAL = "GENERAL", "Обратная связь"
        CONTRACT_TEMPLATE_CONTRACTOR = "CONTRACT_TEMPLATE_CONTRACTOR", "Шаблон договора подрядчика"
        CONTRACT_TEMPLATE_SUPPLIER = "CONTRACT_TEMPLATE_SUPPLIER", "Шаблон договора поставщика"

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Время обращения")

    telegram_chat_id = models.PositiveIntegerField(null=True, verbose_name="ID чата в Telegram")
    telegram_sent_message_id = models.PositiveIntegerField(null=True, verbose_name="ID сообщения в Telegram")

    telegram_username = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Имя пользователя в Telegram"
    )
    telegram_first_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Имя в Telegram")
    telegram_last_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Фамилия в Telegram")

    name = models.CharField(max_length=255, null=True, blank=True, verbose_name="ФИО")
    contact_number = models.CharField(max_length=255, null=True, blank=True, verbose_name="Номер телефона")
    email = models.CharField(max_length=255, null=True, blank=True, verbose_name="Email")
    company = models.CharField(max_length=255, null=True, blank=True, verbose_name="Компания")
    inn = models.CharField(max_length=255, null=True, blank=True, verbose_name="ИНН")
    text = models.TextField(max_length=4096, null=True, blank=True, verbose_name="Текст обращения")

    type = models.CharField(
        max_length=255, choices=FeedbackType.choices, default=FeedbackType.GENERAL, verbose_name="Тип запроса"
    )
    processed = models.BooleanField(default=False, verbose_name="Обработано")

    submitted = models.BooleanField(default=False)
    comment = models.CharField(max_length=500, null=True, blank=True, verbose_name="Комментарий")
    next_field = models.CharField(max_length=255, null=True)


class UserUploadedFile(models.Model):
    feedback = models.ForeignKey(Feedback, on_delete=models.CASCADE, related_name="uploaded_files")
    file = models.FileField(upload_to="user_uploads/")
