# Generated by Django 5.0.6 on 2024-07-03 02:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_client_is_joint_account_client_user_one_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client',
            name='email',
            field=models.EmailField(max_length=254, verbose_name='Email'),
        ),
    ]