# apps/core/migrations/0005_popular_vinculos_existentes.py
from django.db import migrations


def popular_vinculos_existentes(apps, schema_editor):
    """
    Popula a tabela VinculoUsuarioBarbearia com os DONOs existentes.
    """
    Barbearia = apps.get_model('tenants', 'Barbearia')
    Vinculo = apps.get_model('core', 'VinculoUsuarioBarbearia')
    
    barbearias_criadas = 0
    for barbearia in Barbearia.objects.filter(is_deleted=False):
        if barbearia.created_by_id:
            vinculo, created = Vinculo.objects.get_or_create(
                usuario_id=barbearia.created_by_id,
                barbearia_id=barbearia.id,
                defaults={'papel': 'DONO'}
            )
            if created:
                barbearias_criadas += 1
    
    print(f"\n✅ Vínculos criados: {barbearias_criadas}")


def reverter_vinculos(apps, schema_editor):
    Vinculo = apps.get_model('core', 'VinculoUsuarioBarbearia')
    Vinculo.objects.all().delete()


class Migration(migrations.Migration):
    
    dependencies = [
        # ⚠️ IMPORTANTE: Ajuste o nome da migração anterior conforme o que foi gerado no Passo 3
        ('core', '0004_vinculousuariobarbearia'),  # ← AJUSTE SE NECESSÁRIO
        ('tenants', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            popular_vinculos_existentes,
            reverse_code=reverter_vinculos,
        ),
    ]