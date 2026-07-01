from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("examples", "0008_assignment"),
    ]

    operations = [
        migrations.AddField(
            model_name="example",
            name="gearbox_status",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
