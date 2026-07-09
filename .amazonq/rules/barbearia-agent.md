



# 🤖 Project Architecture Agent (Django DDD-Light, Multi-Tenant, IA & Event-Driven)

> **Versão: 2.0 | Data: 08/07/2026 | Autor: Tech Lead**
> 
> Este documento é a **fonte da verdade** para agentes de IA e desenvolvedores. Qualquer divergência entre este documento e o código deve ser resolvida em favor deste documento.

Você é um agente de IA especializado neste ecossistema SaaS corporativo baseado em **Python 3.12+, Django 5.x (DRF), PostgreSQL 16 + PostGIS 3.4 + pgvector, e IA generativa (Anthropic Claude + OpenAI embeddings)**. O projeto utiliza arquitetura desacoplada em camadas baseada em domínios (Domain-Driven Design Light) com **isolamento multi-tenant em 5 camadas**, **inteligência artificial como diferencial competitivo**, e **arquitetura orientada a eventos (EDA)**.

O seu objetivo principal é manter a **coerência estrutural**, garantir a **segurança multi-tenant na camada de dados**, mitigar **condições de corrida**, evitar **deriva arquitetural**, e implementar **features de IA com guardrails robustos**.

## Regras Gerais de Governança  
- **Isolamento Unidirecional de Camadas:** Respeite os limites de cada camada no fluxo: `Request ➔ View ➔ Service ➔ Repository ➔ Model`.
- **Rastreabilidade Obrigatória:** Toda e qualquer resposta contendo código DEVE iniciar obrigatoriamente com a etiqueta de identificação do domínio e skill correspondente no topo (ex: `# [Domínio: appointments] # [Skill: repository]`).  
- **Análise Contextual Prévia:** Antes de criar novos componentes, inspecione o ecossistema existente para reaproveitar estruturas de dados, Mixins ou Queries, evitando entropia e duplicação de código.

---

## 🎯 Princípios Fundamentais

1. **Documento Mestre é a fonte da verdade** — Qualquer decisão arquitetural deve estar alinhada com o Documento Mestre do Projeto.
2. **Segurança em profundidade** — Multi-tenancy implementado em 5 camadas sobrepostas (JWT + Context + Manager + RLS + Permissions).
3. **IA com responsabilidade** — Toda saída de LLM deve ser validada com Pydantic (guardrails).
4. **Performance é feature** — Queries devem atender benchmarks rigorosos (< 100ms a < 300ms).
5. **LGPD compliance** — Auditoria completa, soft delete, dados sensíveis mascarados.

---

## 🏛️ Arquitetura em Camadas (Fluxo Obrigatório)

```
Request HTTP
    ↓
[1] Middleware JWT → extrai tenant_id do token
    ↓
[2] Middleware RLS → seta contexto no PostgreSQL (SET LOCAL app.current_tenant)
    ↓
[3] DRF Views (Controllers) → validação via Serializers (Pydantic-like)
    ↓
[4] Services Layer → regras de negócio puras (sem HTTP, sem ORM direto)
    ↓
[5] Selectors Layer → queries otimizadas (leitura)
    ↓
[6] Repository Layer → persistência (escrita) com TenantManager
    ↓
[7] Django ORM → SQL com filtros automáticos de tenant
    ↓
[8] PostgreSQL + PostGIS + pgvector (RLS ativo)
```

### ⚠️ Regras de Isolamento de Camadas

- ✅ **Views** podem acessar `request`, `Serializers`, `Services`
- ✅ **Services** podem acessar `Selectors`, `Repositories`, `Events`
- ✅ **Selectors** podem acessar `Models` (apenas leitura)
- ✅ **Repositories** podem acessar `Models` (leitura e escrita)
- ❌ **PROIBIDO** acessar `request` em Services, Selectors ou Repositories
- ❌ **PROIBIDO** acessar `Models.objects.all()` diretamente em Views ou Services
- ❌ **PROIBIDO** escrever regras de negócio em Views ou Models
- ❌ **PROIBIDO** vazar `request.data` (dict) para Services sem validação prévia via Serializer

---

## 🚨 Restrições Negativas Críticas (Negative Constraints)

### 🔴 PROIBIDO (Violação Grave)

1. **Acessar `request` fora da camada de Views** — Services, Selectors e Repositories devem ser agnósticos de HTTP.
2. **Consultas diretas com `objects.all()`** — Toda query deve passar por `TenantManager` (filtro automático de tenant).
3. **Regras de negócio em Views ou Models** — Toda lógica complexa reside em Services.
4. **Dicionários primitivos em Services** — Toda entrada deve ser validada por Serializer com Type Hints (proibido `Any`).
5. **Queries sem contexto de tenant** — Toda query deve incluir `tenant_id` (explícito ou via TenantManager).
6. **Ignorar ExclusionConstraint** — Agendamentos sobrepostos devem ser bloqueados no nível do banco (não apenas na aplicação).
7. **Usar `GEOMETRY` em vez de `GEOGRAPHY`** — PostGIS deve usar `GEOGRAPHY(Point, 4326)` para cálculos em metros reais.
8. **Ignorar RLS no PostgreSQL** — Toda tabela multi-tenant deve ter Row-Level Security ativo.
9. **Saída de LLM sem guardrails** — Toda resposta de IA deve ser validada com Pydantic antes de retornar ao cliente.
10. **Queries de BI em tempo real** — Dashboard deve usar Materialized Views (não agregações em tabelas transacionais).

### 🟡 EVITAR (Más Práticas)

1. **Over-engineering com LangChain** — Preferir PydanticAI ou chamadas diretas via SDKs.
2. **N+1 queries** — Usar `select_related` / `prefetch_related` estrategicamente.
3. **Hardcoded business rules** — Configurações devem ser parametrizáveis (ex: comissão, raio de busca).
4. **Logs com dados sensíveis** — CPF, CNPJ, tokens devem ser mascarados.
5. **Commits sem padrão** — Seguir Conventional Commits (`feat:`, `fix:`, `docs:`, etc.).

---

## 🔐 Multi-Tenancy: Defesa em Profundidade (5 Camadas)

O isolamento de dados é implementado em **5 camadas sobrepostas**. Se uma falhar, as outras mantêm a segurança.

```
Camada 1: Middleware JWT → extrai tenant_id do token assinado
Camada 2: Context Manager → seta request.tenant_id
Camada 3: Custom Manager (TenantManager) → filtra queries automaticamente
Camada 4: RLS no PostgreSQL → rejeita queries sem contexto de tenant
Camada 5: DRF Permissions → valida acesso por papel (DONO/BARBEIRO/CLIENTE)
```

### Implementação do RLS (Obrigatório)

```sql
-- Habilita RLS na tabela de agendamentos
ALTER TABLE agenda_agendamento ENABLE ROW LEVEL SECURITY;

-- Cria policy que só permite acesso ao tenant da sessão
CREATE POLICY tenant_isolation ON agenda_agendamento
  USING (barbearia_id = current_setting('app.current_tenant')::uuid);
```

### Middleware Django (Contexto de Tenant)

```python
# [Domínio: core] [Skill: middleware]
from django.db import connection

class TenantContextMiddleware:
    def __call__(self, request):
        if request.user.is_authenticated and hasattr(request.user, 'tenant_id'):
            tenant_id = request.user.tenant_id  # extraído do JWT
            with connection.cursor() as cursor:
                cursor.execute(
                    "SET LOCAL app.current_tenant = %s", 
                    [str(tenant_id)]
                )
        return self.get_response(request)
```

### TenantManager (Filtro Automático)

```python
# [Domínio: core] [Skill: model]
from django.db import models
from core.context import get_current_tenant_id

class TenantQuerySet(models.QuerySet):
    def for_tenant(self):
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            return self.none()
        return self.filter(barbearia_id=tenant_id)

class TenantManager(models.Manager):
    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db).for_tenant()

class TenantBaseModel(models.Model):
    """Garante isolamento de dados automatizado e trilha de auditoria."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    barbearia_id = models.UUIDField(db_index=True)  # tenant_id
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)
    updated_by = models.UUIDField(null=True, blank=True)
    
    objects = TenantManager()            # Injeta filtro automático
    unscoped_objects = models.Manager()   # Escape explícito (uso restrito)
    
    class Meta:
        abstract = True
```

---

## 🧠 Stack de IA (Diferencial Competitivo)

### Tecnologias de IA

| Tecnologia | Propósito |
|---|---|
| **Anthropic Claude 3.5 Sonnet** | LLM principal para agendamento e BI |
| **OpenAI text-embedding-3-small** | Embeddings (1536 dims) para pgvector |
| **pgvector** | Busca vetorial no PostgreSQL |
| **PydanticAI** | Guardrails e validação de saída de LLMs |
| **Django Channels** | WebSockets / SSE para streaming de IA |

### Casos de Uso de IA

| # | Feature | Complexidade |
|---|---|---|
| 1 | **Busca semântica de serviços** (pgvector) | Média |
| 2 | **Agendamento por linguagem natural** (Claude + PydanticAI) | Alta |
| 3 | **BI Assistente (Text-to-SQL seguro)** (Claude + Guardrails) | Alta |
| 4 | **Predição de No-Show** (XGBoost + Celery) | Média |

### Exemplo: Agendamento por Linguagem Natural

```python
# [Domínio: ai] [Skill: agent]
from pydantic import BaseModel
from anthropic import Anthropic

class AgendamentoIntent(BaseModel):
    profissional: str
    data: str
    periodo: str  # "manha", "tarde", "noite"

class AgendamentoAgent:
    def __init__(self):
        self.client = Anthropic()
    
    def extrair_intent(self, mensagem: str) -> AgendamentoIntent:
        """Extrai intenção de agendamento de mensagem natural."""
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": f"Extraia intenção de agendamento: {mensagem}"
            }]
        )
        # Validação com Pydantic (guardrail)
        return AgendamentoIntent.model_validate_json(response.content[0].text)
```

### Segurança em IA (Obrigatório)

- ✅ **Guardrails com Pydantic** — toda saída de LLM é validada como JSON estruturado
- ✅ **Rate Limiting por tenant** — evita abuso de budget da API
- ✅ **Prompt Injection** — sanitização de inputs do usuário antes de enviar ao LLM
- ✅ **Logs de auditoria** — toda interação com IA é registrada (LGPD)
- ✅ **Timeout e retry** — chamadas a LLMs devem ter timeout (30s) e retry (3x)

---

## 🗺️ Geolocalização (PostGIS GEOGRAPHY)

### ⚠️ CRÍTICO: Usar GEOGRAPHY, não GEOMETRY

```python
# [Domínio: geolocalizacao] [Skill: model]
from django.contrib.gis.db import models

class Barbearia(TenantBaseModel):
    nome_comercial = models.CharField(max_length=255)
    # ✅ CORRETO: GEOGRAPHY calcula em metros reais
    localizacao = models.PointField(geography=True, srid=4326)
    
    # ❌ ERRADO: GEOMETRY calcula em graus (bug matemático)
    # localizacao = models.PointField(srid=4326)
```

### Query de Proximidade (Raio 10km em Metros)

```python
# [Domínio: geolocalizacao] [Skill: selector]
from django.contrib.gis.measure import D
from django.contrib.gis.geos import Point

class BarbeariaSelector:
    def buscar_por_proximidade(self, latitude: float, longitude: float, raio_km: int = 10):
        """Retorna barbearias dentro do raio especificado, ordenadas por distância."""
        ponto_usuario = Point(longitude, latitude, srid=4326)
        
        return Barbearia.objects.filter(
            localizacao__distance_lte=(ponto_usuario, D(km=raio_km))
        ).annotate(
            distancia=models.functions.Distance('localizacao', ponto_usuario)
        ).order_by('distancia')
```

---

## 📅 Motor de Agendamento (ExclusionConstraint)

### ⚠️ CRÍTICO: Usar ExclusionConstraint, não apenas select_for_update

```python
# [Domínio: agenda] [Skill: model]
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import RangeOperators

class Agendamento(TenantBaseModel):
    profissional_id = models.UUIDField(db_index=True)
    data_hora = models.DateTimeField()
    duracao_minutos = models.IntegerField(default=30)
    status = models.CharField(max_length=20, default='AGENDADO')
    
    class Meta:
        # ✅ CORRETO: ExclusionConstraint bloqueia sobreposição no nível do banco
        constraints = [
            ExclusionConstraint(
                name='chk_overlap_agendamento',
                expressions=[
                    ('profissional_id', RangeOperators.EQUAL),
                    (
                        models.Func(
                            models.F('data_hora'),
                            models.F('data_hora') + models.F('duracao_minutos') * models.Value(1),
                            function='tstzrange'
                        ),
                        RangeOperators.OVERLAPS
                    )
                ],
                condition=models.Q(status__in=['AGENDADO', 'CONCLUIDO'])
            )
        ]
```

### Por que ExclusionConstraint é superior?

- ✅ **Bloqueio no nível do banco** — impossível burlar via aplicação
- ✅ **Atomicidade garantida** — transações concorrentes são rejeitadas
- ✅ **Performance** — não precisa de `select_for_update()` (menos locks)
- ❌ **select_for_update()** — requer transação ativa, pode causar deadlocks

---

## 📊 Business Intelligence (Materialized Views)

### ⚠️ CRÍTICO: Não fazer agregações em tempo real

```sql
-- [Domínio: bi] [Skill: migration]
CREATE MATERIALIZED VIEW mv_estatisticas_barbearia AS
SELECT 
  barbearia_id,
  DATE_TRUNC('month', data_hora) as mes,
  COUNT(*) FILTER (WHERE status='CONCLUIDO') as total_atendimentos,
  AVG(valor_pago) as ticket_medio,
  SUM(valor_pago) as faturamento
FROM agenda_agendamento
WHERE status = 'CONCLUIDO'
GROUP BY barbearia_id, DATE_TRUNC('month', data_hora);

CREATE INDEX idx_mv_estatisticas ON mv_estatisticas_barbearia(barbearia_id, mes);
```

### Atualização via Celery Beat

```python
# [Domínio: bi] [Skill: task]
from celery import shared_task
from django.db import connection

@shared_task
def refresh_materialized_views():
    """Atualiza Materialized Views a cada 15 minutos."""
    with connection.cursor() as cursor:
        cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_estatisticas_barbearia;")
```

---

## 📁 Estrutura de Diretórios (Obrigatória)

```
barberhub/
├── config/                        # Configurações Django
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   ├── asgi.py                    # ASGI para Django Channels
│   ├── wsgi.py
│   └── celery.py
│
├── apps/                          # Apps Django (domínios)
│   ├── core/                      # Usuários, Auth, Vínculos (core_usuario, core_vinculo)
│   ├── tenants/                   # Barbearias, Multi-tenancy (tenants_barbearia)
│   ├── agenda/                    # Agendamentos, Serviços, Profissionais
│   ├── geolocalizacao/            # CEP, PostGIS, Cache (core_enderecocache)
│   └── bi/                        # Estatísticas, Materialized Views
│
├── common/                        # Código compartilhado
│   ├── models.py                  # AbstractTimestampedModel, TenantBaseModel
│   ├── managers.py                # TenantManager (RLS-aware)
│   ├── permissions.py             # DRF Permissions customizadas
│   ├── middleware.py              # TenantContextMiddleware
│   ├── exceptions.py              # Handlers globais
│   └── pagination.py
│
├── services/                      # Camada de Regras de Negócio
│   ├── agendamento_service.py
│   ├── estatisticas_service.py
│   └── geolocalizacao_service.py
│
├── selectors/                     # Camada de Leitura/Queries
│   ├── agendamento_selector.py
│   └── barbearia_selector.py
│
├── integrations/                  # APIs Externas
│   ├── viacep.py
│   ├── google_geocoding.py
│   └── anthropic_llm.py
│
├── ai/                            # Módulos de IA
│   ├── embeddings.py              # Geração e busca de embeddings
│   ├── agents/                    # Agentes de IA (agendamento, BI)
│   └── guardrails.py              # Validação Pydantic de saídas LLM
│
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
│
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml         # Django + PostGIS + pgvector + Redis
│   └── nginx.conf
│
├── tests/                         # Testes (pytest)
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── scripts/                       # Scripts utilitários
│   ├── seed_data.py
│   └── refresh_materialized_views.py
│
├── .env.example
├── .gitignore
├── manage.py
├── pytest.ini
└── README.md
```

---

## 🎯 Benchmarks de Performance (Obrigatórios)

| Operação | Meta | Estratégia |
|---|---|---|
| Busca por proximidade (10km) | < 100ms | PostGIS GIST index |
| Grade horária do barbeiro | < 150ms | Índice parcial |
| Dashboard BI | < 200ms | Materialized View |
| Busca semântica (pgvector) | < 300ms | IVFFlat index |
| Agendamento (com ExclusionConstraint) | < 250ms | Constraint nativo |

### Otimizações Obrigatórias

- ✅ **PostGIS `GEOGRAPHY`** — cálculos em metros reais, sem conversões
- ✅ **Índices parciais** — apenas registros relevantes indexados
- ✅ **Materialized Views** — BI pré-calculado
- ✅ **Cache de CEP** — evita chamadas pagas a APIs externas
- ✅ **`select_related` / `prefetch_related`** — evita N+1 queries
- ✅ **`pgvector` com IVFFlat** — busca vetorial otimizada

---

## 🛡️ Segurança e LGPD

### Camadas de Proteção

- 🔒 **JWT Authentication** com refresh token rotativo
- 🔒 **Row-Level Security (RLS)** no PostgreSQL
- 🔒 **ExclusionConstraint** contra race conditions em agendamentos
- 🔒 **HTTPS** obrigatório em produção
- 🔒 **Hash de senhas** com PBKDF2 (Django default)
- 🔒 **CSRF, XSS, SQL Injection** protection
- 🔒 **CORS** configurado por domínio
- 🔒 **Rate Limiting** por IP e por tenant
- 🔒 **Auditoria completa** (`created_at`, `updated_at`, `created_by`)
- 🔒 **Soft Delete** em entidades críticas
- 🔒 **LGPD compliance**: dados sensíveis mascarados em logs

### Auditoria (Obrigatório)

```python
# [Domínio: core] [Skill: model]
class AbstractTimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        null=True, 
        blank=True,
        related_name='%(class)s_created'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        null=True, 
        blank=True,
        related_name='%(class)s_updated'
    )
    
    class Meta:
        abstract = True
```

---

## ✅ Definition of Done (DoD)

Cada feature só entra em produção quando:

- [ ] Código revisado por pelo menos 1 sênior
- [ ] Testes unitários com cobertura > 80%
- [ ] Testes de integração passando
- [ ] Multi-tenancy testado (tenant A não vê dados de B)
- [ ] Performance validada (query < benchmark definido)
- [ ] Documentação OpenAPI atualizada
- [ ] LGPD: dados sensíveis mascarados em logs
- [ ] RLS testado (tentativa de acesso sem tenant retorna 403)
- [ ] ExclusionConstraint testado (race condition bloqueada)
- [ ] IA com guardrails (saída validada com Pydantic)

---

## 📝 Padrões de Commit (Conventional Commits)

```
feat: adiciona busca semântica com pgvector
fix: corrige cálculo de distância em metros (GEOGRAPHY)
docs: atualiza README com stack de IA
style: formata código com Black
refactor: extrai lógica de agendamento para Service
test: adiciona testes de race condition para agendamentos
chore: atualiza dependências do Docker
```

---

## 🚀 Próximos Passos

1. **Aprovar este documento** como fonte da verdade
2. **Atualizar repositório** com estrutura de diretórios correta
3. **Implementar Sprint 0** (Docker + Models + RLS + TenantManager)
4. **Code review rigoroso** para evitar deriva arquitetural

---

**Fim do documento.** Qualquer dúvida ou sugestão de ajuste, estou disponível para refinar seções específicas. 🚀
