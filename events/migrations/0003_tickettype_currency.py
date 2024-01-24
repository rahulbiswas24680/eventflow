# Generated by Django 5.0.1 on 2024-01-24 15:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0002_tickettype_image_tickettype_stripe_price_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='tickettype',
            name='currency',
            field=models.CharField(choices=[('USD', 'USD'), ('INR', 'INR'), ('EUR', 'EUR')], default='INR', max_length=10),
        ),
    ]