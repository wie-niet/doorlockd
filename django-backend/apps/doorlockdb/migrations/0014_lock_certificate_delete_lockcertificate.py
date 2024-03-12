# Generated by Django 4.0.1 on 2023-05-30 14:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("doorlockdb", "0013_remove_lockcertificate_fingerprint"),
    ]

    operations = [
        migrations.AddField(
            model_name="lock",
            name="certificate",
            field=models.TextField(
                default=None, max_length=2000, null=True, unique=True
            ),
        ),
        migrations.DeleteModel(
            name="LockCertificate",
        ),
    ]
