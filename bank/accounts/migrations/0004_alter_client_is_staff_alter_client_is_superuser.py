# Generated by Django 5.0.6 on 2024-06-29 17:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_client_in_transaction_balance'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client',
            name='is_staff',
            field=models.BooleanField(default=True, verbose_name='Staff'),
        ),
        migrations.AlterField(
            model_name='client',
            name='is_superuser',
            field=models.BooleanField(default=False),
        ),
    ]
