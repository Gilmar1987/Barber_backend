import time
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from apps.tenants.models import Barbearia
from apps.core.service import GeolocalizacaoService

class Command(BaseCommand):
    help = 'Popula o campo localizacao (PostGIS) das barbearias existentes usando o cache de geolocalização.'

    def handle(self, *args, **kwargs):
        # Busca barbearias que não têm o campo localizacao preenchido
        barbearias = Barbearia.objects.filter(localizacao__isnull=True)
        total = barbearias.count()
        
        self.stdout.write(f"Encontradas {total} barbearias sem coordenadas geoespaciais (localizacao).")
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS("Nenhuma barbearia precisa de atualização."))
            return

        success_count = 0
        error_count = 0

        for barbearia in barbearias:
            self.stdout.write(f"Processando Barbearia: {barbearia.nome_comercial} (CEP: {barbearia.cep})")
            
            # Obtém coordenadas do cache ou API
            coords = GeolocalizacaoService.obter_ou_criar_cache(cep=barbearia.cep)
            
            if coords:
                # Cria o objeto Point do PostGIS: Point(longitude, latitude, srid=4326)
                # Nota: O PostGIS usa a ordem (Longitude, Latitude)
                barbearia.localizacao = Point(coords['longitude'], coords['latitude'], srid=4326)
                barbearia.save(update_fields=['localizacao'])
                success_count += 1
                self.stdout.write(self.style.SUCCESS(f"  ✅ Atualizada: Lon={coords['longitude']}, Lat={coords['latitude']}"))
            else:
                error_count += 1
                self.stdout.write(self.style.WARNING("  ⚠️ Falha ao obter coordenadas."))
            
            # Pausa de 1 segundo para não sobrecarregar a API gratuita
            time.sleep(1)

        self.stdout.write(self.style.SUCCESS(f"\nConcluído! Sucessos: {success_count} | Falhas: {error_count}"))