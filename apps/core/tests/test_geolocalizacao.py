from unittest.mock import patch
from django.test import TestCase
from apps.core.service import GeolocalizacaoService
from apps.core.models import GeolocalizacaoCache

class GeolocalizacaoServiceTest(TestCase):
    def test_cache_hit(self):
        """Se o CEP está no cache, não deve chamar a API."""
        GeolocalizacaoCache.objects.create(
            cep="01001000", latitude=-23.5479, longitude=-46.636
        )
        
        with patch('requests.get') as mock_get:
            result = GeolocalizacaoService.obter_ou_criar_cache("01001000")
            
            self.assertIsNotNone(result)
            self.assertEqual(result['latitude'], -23.5479)
            mock_get.assert_not_called() # Garante que a API não foi chamada

    def test_api_call_and_cache_save(self):
        """Se o CEP não está no cache, deve chamar a API e salvar."""
        mock_response = {
            "cidade": {"nome": "São Paulo"},
            "estado": {"sigla": "SP"},
            "latitude": "-23.547909",
            "longitude": "-46.636"
        }
        
        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.raise_for_status.return_value = None
            
            result = GeolocalizacaoService.obter_ou_criar_cache("01001000")
            
            self.assertIsNotNone(result)
            self.assertEqual(result['latitude'], -23.547909)
            
            # Verifica se salvou no banco
            cache = GeolocalizacaoCache.objects.get(cep="01001000")
            self.assertEqual(float(cache.latitude), -23.547909)