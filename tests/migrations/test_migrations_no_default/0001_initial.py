from django_mongodb.fields import ObjectIdAutoField

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SillyModel",
            fields=[
                (
                    "id",
                    ObjectIdAutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("silly_field", models.BooleanField(default=False)),
            ],
            options={},
            bases=(models.Model,),
        ),
    ]
