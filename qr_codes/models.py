import json
import random
import string
import uuid
from io import BytesIO

import segno
from django.core.files.base import ContentFile
from django.db import models

from payments.models import Transaction


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

    # def __str__(self):
    #     return str(self.id) + "-(" + self.transaction.rsvp.event.name + ")"

    def save(self, *args, **kwargs):
        tkn = None
        if not self.code_data and self.transaction:
            transaction_obj = self.transaction
            self.code_data = f"""//////
{transaction_obj.ticket_type.name}
{transaction_obj.currency} {transaction_obj.amount}
Qty: {transaction_obj.quantity}
Status: {transaction_obj.payment_status}
RSVP: {transaction_obj.rsvp.id}
TxnID: {transaction_obj.transaction_id}
//////
"""

        if not self.code_image and self.code_data:
            self.generate_qrcode(self.code_data)

        super().save(*args, **kwargs)

    def generate_qrcode(self, tkn):
        """Generate a professional styled QR code image locally"""
        qr_data = str(tkn)
        qr_image = segno.make(
            qr_data,
            micro=False,
            error='h',   # high error correction for logo/branding
        )

        # Make filename
        fname = "".join(random.choice(string.ascii_lowercase) for _ in range(8))
        file_name = f"{fname}.png"

        # Use a BytesIO buffer
        img_buffer = BytesIO()

        qr_image.save(
            img_buffer,
            kind="png",
            scale=10,
            border=2,
            dark="#2D3748",   # dark blue/gray instead of pure black
            light="#F7FAFC",  # subtle off-white background
            data_dark="#6B46C1",  # optional: emphasize data modules
        )
        img_buffer.seek(0)

        # Generate a proper random filename
        fname = "".join(random.choice(string.ascii_lowercase) for _ in range(8)) + ".png"

        # Attach to model field (Django will save it to MEDIA_ROOT/transaction_qr_code/)
        self.code_image.save(fname, ContentFile(img_buffer.read()), save=False)
