# [Domínio: operacional] [Skill: migration]
"""
Migration manual necessária porque:
- auto_now_add=True não aceita default automático em tabelas existentes
- OneToOneField → ForeignKey requer recriação da constraint
- unique_together adicionado para modelo freelancer
"""
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operacional', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Adiciona campos de auditoria em Servico
        migrations.AddField(
            model_name='servico',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
                help_text='Data/hora de criação',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='servico',
            name='updated_at',
            field=models.DateTimeField(
                auto_now=True,
                help_text='Data/hora da última atualização',
            ),
        ),
        migrations.AddField(
            model_name='servico',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                help_text='Usuário que criou o registro',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='servico_created',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='servico',
            name='updated_by',
            field=models.ForeignKey(
                blank=True,
                help_text='Usuário que atualizou o registro',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='servico_updated',
                to=settings.AUTH_USER_MODEL,
            ),
        ),

        # 2. Adiciona campos de auditoria em Profissional
        migrations.AddField(
            model_name='profissional',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
                help_text='Data/hora de criação',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='profissional',
            name='updated_at',
            field=models.DateTimeField(
                auto_now=True,
                help_text='Data/hora da última atualização',
            ),
        ),
        migrations.AddField(
            model_name='profissional',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                help_text='Usuário que criou o registro',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='profissional_created',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='profissional',
            name='updated_by',
            field=models.ForeignKey(
                blank=True,
                help_text='Usuário que atualizou o registro',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='profissional_updated',
                to=settings.AUTH_USER_MODEL,
            ),
        ),

        # 3. OneToOneField → ForeignKey (modelo freelancer)
        migrations.AlterField(
            model_name='profissional',
            name='usuario',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='vinculos_profissional',
                to=settings.AUTH_USER_MODEL,
            ),
        ),

        # 4. unique_together: 1 vínculo por (usuario, barbearia)
        migrations.AlterUniqueTogether(
            name='profissional',
            unique_together={('usuario', 'barbearia')},
        ),
    ]
