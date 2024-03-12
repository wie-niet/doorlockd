# Generated by Django 4.0.1 on 2023-05-30 13:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("doorlockdb", "0011_lockcertificate_remove_lock_certificate"),
    ]

    operations = [
        migrations.AddField(
            model_name="lockcertificate",
            name="fingerprint",
            field=models.CharField(default="not set", editable=False, max_length=64),
            preserve_default=False,
        ),
    ]
