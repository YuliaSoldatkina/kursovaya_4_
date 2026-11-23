from django.db import models
from django.utils import timezone


class Recipient(models.Model):
    email = models.EmailField(
        'Email',
        unique=True,
    )
    full_name = models.CharField(
        'Ф. И. О.',
        max_length=150,
    )
    comment = models.TextField(
        'Комментарий',
        blank=True,
    )

    class Meta:
        verbose_name = 'Получатель рассылки'
        verbose_name_plural = 'Получатели рассылки'

    def __str__(self):
        return self.full_name


class Message(models.Model):
    subject = models.CharField(
        'Тема письма',
        max_length=255,
    )
    body = models.TextField(
        'Тело письма',
    )

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'

    def __str__(self):
        return self.subject


class Mailing(models.Model):
    STATUS_CREATED = 'Создана'
    STATUS_STARTED = 'Запущена'
    STATUS_COMPLETED = 'Завершена'

    STATUS_CHOICES = [
        (STATUS_CREATED, 'Создана'),
        (STATUS_STARTED, 'Запущена'),
        (STATUS_COMPLETED, 'Завершена'),
    ]

    start_time = models.DateTimeField(
        'Дата и время начала отправки',
    )
    end_time = models.DateTimeField(
        'Дата и время окончания отправки',
    )
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_CREATED,
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        verbose_name='Сообщение',
        related_name='mailings',
    )
    recipients = models.ManyToManyField(
        Recipient,
        verbose_name='Получатели',
        related_name='mailings',
    )

    class Meta:
        verbose_name = 'Рассылка'
        verbose_name_plural = 'Рассылки'

    def __str__(self):
        return f'Рассылка №{self.pk} — {self.message}'

    def update_status(self):
        now = timezone.now()

        if now < self.start_time:
            new_status = self.STATUS_CREATED
        elif self.start_time <= now <= self.end_time:
            new_status = self.STATUS_STARTED
        else:
            new_status = self.STATUS_COMPLETED

        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=['status'])

        return self.status


class MailingAttempt(models.Model):
    STATUS_SUCCESS = 'Успешно'
    STATUS_FAILED = 'Не успешно'

    STATUS_CHOICES = [
        (STATUS_SUCCESS, 'Успешно'),
        (STATUS_FAILED, 'Не успешно'),
    ]

    attempt_time = models.DateTimeField(
        'Дата и время попытки',
        auto_now_add=True,
    )
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
    )
    server_response = models.TextField(
        'Ответ почтового сервера',
        blank=True,
    )
    mailing = models.ForeignKey(
        Mailing,
        on_delete=models.CASCADE,
        verbose_name='Рассылка',
        related_name='attempts',
    )

    class Meta:
        verbose_name = 'Попытка рассылки'
        verbose_name_plural = 'Попытки рассылок'

    def __str__(self):
        return f'Попытка рассылки №{self.pk} — {self.status}'
