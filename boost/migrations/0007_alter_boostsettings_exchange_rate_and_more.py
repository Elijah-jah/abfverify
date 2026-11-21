# Switches boost pricing labels to USD (ReallySimpleSocial bills in USD).
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('boost', '0006_alter_boostorder_provider_cost_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='boostsettings',
            name='exchange_rate',
            field=models.DecimalField(decimal_places=2, default=1.0, help_text='ReallySimpleSocial bills in USD. Set this to the current NGN value of $1 (e.g. 1500).', max_digits=10),
        ),
        migrations.AlterField(
            model_name='boostservice',
            name='rate',
            field=models.DecimalField(decimal_places=4, help_text='Provider cost per 1000 units (USD)', max_digits=16),
        ),
    ]
