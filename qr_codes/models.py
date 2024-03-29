import json
import random
import string
import uuid
from io import BytesIO

import segno
from django.core.files import File
from django.db import models

from payments.models import Transaction
from rsvp.storage import SupabaseStorage

s = SupabaseStorage()


class QRCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.OneToOneField(
        Transaction, on_delete=models.PROTECT, default=None
    )
    code_image = models.ImageField(
        upload_to="transaction_qr_code/",
        blank=True,
        null=True,
        editable=True,
        default=None,
    )
    code_data = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "QRCode"
        verbose_name_plural = "QRCodes"

    def __str__(self):
        return str(self.id) + "-(" + self.transaction.rsvp.event.name + ")"

    def save(self, *args, **kwargs):
        tkn = None
        if not self.code_data:
            if self.transaction:
                transaction_obj = self.transaction
                self.code_data = f"""//////
{transaction_obj.ticket_type.name}-
{transaction_obj.currency}-
{transaction_obj.amount}-
{transaction_obj.quantity}-
{transaction_obj.payment_status}-
{transaction_obj.rsvp.id}-
{transaction_obj.transaction_id}
//////
"""
                tkn = self.code_data

        if not self.code_image:
            self.code_image = self.generate_qrcode(tkn)

        if self.code_image:
            current_image_name = str(self.code_image)
            self.code_image = self.generate_qrcode(tkn)
            self.remove_old_qr(current_image_name)

        super().save(*args, **kwargs)

    def generate_qrcode(self, tkn):
        qr_data = str(tkn)
        qr_image = segno.make(qr_data, micro=False)

        img_buffer = BytesIO()

        qr_image.save(img_buffer, scale=10, kind="png")
        img_buffer.seek(0)

        fname = "".join(
            random.choice(string.ascii_lowercase) for i in range(6)
        )
        return File(img_buffer, name=f"{fname}.png")

    def remove_old_qr(self, filename):
        s.delete(filename)
