from adminsortable2.admin import SortableAdminBase, SortableTabularInline
from django.contrib import admin

from tenders_bot.models import Feedback, File, Node, UserUploadedFile
from tenders_bot.settings import ID_FORMAT


class FileInline(admin.StackedInline):
    model = File
    extra = 0


class UserUploadedFileInline(admin.StackedInline):
    model = UserUploadedFile
    extra = 0
    can_delete = False
    readonly_fields = ("file",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class NodeInline(SortableTabularInline):
    model = Node
    fields = ("button_text", "text", "nav_text")
    extra = 0
    can_delete = False
    show_change_link = True


@admin.register(Node)
class NodeAdmin(SortableAdminBase, admin.ModelAdmin):
    list_display = ("path", "text", "nav_text", "number_of_files")
    ordering = ("path",)
    exclude = ("button_order",)
    inlines = [FileInline, NodeInline]

    def number_of_files(self, obj):
        return len(obj.files.all())


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("formatted_id", "created_at", "type", "company", "email", "telegram_username", "text", "processed")
    search_fields = (
        "id",
        "company",
        "telegram_username",
        "text",
    )
    exclude = ("telegram_chat_id", "telegram_sent_message_id", "submitted", "next_field")
    readonly_fields = (
        "formatted_id",
        "type",
        "created_at",
        "company",
        "inn",
        "name",
        "contact_number",
        "email",
        "text",
        "telegram_username",
        "telegram_first_name",
        "telegram_last_name",
    )
    ordering = ("-created_at",)
    list_filter = ("type", "processed")
    inlines = [UserUploadedFileInline]
    actions = ["mark_as_processed"]

    def formatted_id(self, obj):
        return ID_FORMAT.format(id=obj.id)

    formatted_id.short_description = "Номер обращения"

    @admin.action(description="Пометить обработанным")
    def mark_as_processed(self, request, queryset):
        queryset.update(processed=True)
