# Generated by Django 4.0.1 on 2023-03-14 17:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("doorlockdb", "0002_remove_accessrule_parent_accessrule_rules"),
    ]

    operations = [
        migrations.AlterField(
            model_name="accessrule",
            name="rules",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="rules",
                to="doorlockdb.accessruleset",
            ),
        ),
    ]
