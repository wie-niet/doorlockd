# Generated by Django 4.0.1 on 2023-03-14 17:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("doorlockdb", "0003_alter_accessrule_rules"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="accessrule",
            name="rules",
        ),
        migrations.AddField(
            model_name="accessrule",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="doorlockdb.accessruleset",
            ),
        ),
    ]
