# 💈 BarberHub SaaS

> **Plataforma SaaS multi-tenant para gestão inteligente de barbearias, construída com Django, PostgreSQL + PostGIS + pgvector e IA generativa.**

[![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.x-green?logo=django)](https://www.djangoproject.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791?logo=postgresql)](https://www.postgresql.org/)
[![PostGIS](https://img.shields.io/badge/PostGIS-3.4-87C540)](https://postgis.net/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📖 Sobre o Projeto

O **BarberHub SaaS** é uma plataforma de gerenciamento de barbearias baseada no modelo **Software as a Service (SaaS) headless/decentralizada**, permitindo que múltiplas barbearias utilizem o mesmo sistema com **isolamento total de dados** garantido em múltiplas camadas (JWT + Custom Managers + Row-Level Security do PostgreSQL).

O sistema foi projetado para atender três perfis distintos de usuários, com foco em **performance, segurança e inteligência artificial como diferencial competitivo**.

### 🎯 Objetivos Estratégicos

- ✅ Agendamento inteligente com proteção contra race conditions
- ✅ Busca por geolocalização em metros reais (PostGIS `GEOGRAPHY`)
- ✅ Multi-tenancy com isolamento em nível de banco (RLS)
- ✅ Business Intelligence com Materialized Views
- ✅ IA generativa para busca semântica e agendamento por linguagem natural
- ✅ API REST escalável, documentada e testada
- ✅ Conformidade com LGPD (auditoria completa de alterações)

---

## 👥 Perfis de Usuário

| Perfil | Descrição | Interface |
|---|---|---|
| 👤 **Cliente Final** | Usuário do marketplace global que busca barbearias próximas e agenda serviços | App Mobile (Flutter) |
| ✂️ **Barbeiro** | Profissional que gerencia sua agenda diária e acompanha comissões | App Mobile (Flutter) |
| 🏪 **Dono** | Administrador do tenant que visualiza BI e gerencia a operação | Painel Web (React/Next.js) |

---

## 🚀 Funcionalidades por Perfil

### 👤 Cliente Final
- Cadastro e autenticação via JWT
- Busca de barbearias por proximidade (raio de 10km em **metros reais**)
- **🆕 Busca semântica de serviços por IA** (ex: "quero algo pra relaxar")
- **🆕 Agendamento por linguagem natural** (voz ou texto)
- Agendamento online com grade dinâmica
- Cancelamento e histórico de atendimentos
- Avaliação dos serviços

### ✂️ Barbeiro
- Agenda diária em tempo real
- Controle de status dos atendimentos
- Visualização de comissões semanais
- Histórico de produtividade
- **🆕 Suporte a múltiplas barbearias** (modelo freelancer)

### 🏪 Dono da Barbearia
- Gestão completa (serviços, profissionais, horários, folgas)
- Dashboard financeiro com **Materialized View** (performance em milissegundos)
- **🆕 BI Assistente por linguagem natural** (ex: "Por que meu faturamento caiu?")
- Ranking de serviços e profissionais
- Ticket Médio, Receita Mensal, Taxa de Ocupação
- Controle de comissões

---

## 🛠️ Stack Tecnológica

### Backend
| Tecnologia | Versão | Propósito |
|---|---|---|
| **Python** | 3.12+ | Linguagem base |
| **Django** | 5.x | Framework web |
| **Django REST Framework** | 3.15+ | API REST |
| **Django Channels** | 4.x | WebSockets / SSE para streaming de IA |
| **Celery** | 5.4+ | Tarefas assíncronas |
| **Celery Beat** | — | Agendamento de tarefas (atualização de MVs) |
| **SimpleJWT** | — | Autenticação JWT com refresh token |
| **PydanticAI** | — | Guardrails e validação de saída de LLMs |

### Banco de Dados
| Tecnologia | Propósito |
|---|---|
| **PostgreSQL 16** | Banco principal com RLS ativo |
| **PostGIS 3.4** | Geolocalização com `GEOGRAPHY` (metros reais) |
| **pgvector** | Embeddings de IA para busca semântica |
| **Redis** | Cache, sessões e broker do Celery |

### IA & Machine Learning
| Tecnologia | Propósito |
|---|---|
| **Anthropic Claude 3.5 Sonnet** | LLM principal para agendamento e BI |
| **OpenAI text-embedding-3-small** | Embeddings (1536 dims) para pgvector |
| **XGBoost / Scikit-learn** | Predição de no-show (Fase 4) |

### Frontend
- **Web:** React + Next.js + ApexCharts
- **Mobile:** Flutter

### Infraestrutura
- Docker + Docker Compose
- Nginx (reverse proxy)
- Gunicorn (ASGI/WSGI)
- Locust (testes de carga)

---

## 🏛️ Arquitetura do Sistema

### Diagrama de Camadas

```
┌─────────────────────────────────────────────────────────────┐
│                    CAMADA DE CLIENTES                        │
│  [App Cliente]    [Painel Dono]    [App Barbeiro]           │
│   (Flutter)        (Next.js)        (Flutter)               │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTPS + JWT
┌────────────────────────────▼────────────────────────────────┐
│              API GATEWAY (Django + DRF)                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 1. Middleware JWT → extrai tenant_id do payload      │  │
│  │ 2. Middleware RLS → seta contexto no PostgreSQL      │  │
│  │ 3. DRF Routers → roteamento de endpoints             │  │
│  │ 4. Services Layer → regras de negócio                │  │
│  │ 5. Selectors Layer → queries otimizadas              │  │
│  │ 6. ORM Django → SQL com travas multi-tenant          │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│              CAMADA DE PERSISTÊNCIA                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ PostgreSQL   │  │ PostGIS      │  │ pgvector         │ │
│  │ (RLS ativo)  │  │ (GEOGRAPHY)  │  │ (embeddings IA)  │ │
│  └──────────────┘  └──────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Arquitetura em Camadas (Clean Architecture Adaptada)

```
Presentation Layer (Views/ViewSets)
           ↓
   API Layer (Serializers)
           ↓
Authentication Layer (JWT)
           ↓
Permission Layer (DRF Permissions + RLS)
           ↓
   Service Layer (Regras de Negócio)
           ↓
  Selector Layer (Queries Otimizadas)
           ↓
Repository / ORM (Django ORM + Custom Managers)
           ↓
     Database (PostgreSQL + PostGIS + pgvector)
```

---

## 📁 Estrutura do Projeto

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
│   ├── core/                      # Usuários, Auth, Vínculos
│   ├── tenants/                   # Barbearias, Multi-tenancy
│   ├── agenda/                    # Agendamentos, Serviços, Profissionais
│   ├── geolocalizacao/            # CEP, PostGIS, Cache
│   └── bi/                        # Estatísticas, Materialized Views
│
├── common/                        # Código compartilhado
│   ├── models.py                  # AbstractTimestampedModel
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

## 🔐 Multi-tenancy: Defesa em Profundidade

O isolamento de dados é implementado em **5 camadas sobrepostas** (Defense in Depth):

```
Camada 1: Middleware JWT → extrai tenant_id do token assinado
Camada 2: Context Manager → seta request.tenant_id
Camada 3: Custom Manager (TenantManager) → filtra queries automaticamente
Camada 4: RLS no PostgreSQL → rejeita queries sem contexto de tenant
Camada 5: DRF Permissions → valida acesso por papel (DONO/BARBEIRO/CLIENTE)
```

### Exemplo de RLS no PostgreSQL

```sql
-- Habilita RLS na tabela de agendamentos
ALTER TABLE agenda_agendamento ENABLE ROW LEVEL SECURITY;

-- Cria policy que só permite acesso ao tenant da sessão
CREATE POLICY tenant_isolation ON agenda_agendamento
  USING (barbearia_id = current_setting('app.current_tenant')::uuid);
```

### Exemplo de Middleware Django

```python
class TenantContextMiddleware:
    def __call__(self, request):
        tenant_id = request.user.tenant_id  # extraído do JWT
        with connection.cursor() as cursor:
            cursor.execute(
                "SET LOCAL app.current_tenant = %s", 
                [str(tenant_id)]
            )
        return self.get_response(request)
```

> ⚠️ **Garantia:** Mesmo que um desenvolvedor esqueça de filtrar por tenant no código, o PostgreSQL rejeitará a query. Vazamento de dados é matematicamente impossível.

---

## 🧠 IA como Diferencial Competitivo

### Casos de Uso Implementados

| # | Feature | Tecnologia | Complexidade |
|---|---|---|---|
| 1 | **Busca semântica de serviços** | pgvector + OpenAI embeddings | Média |
| 2 | **Agendamento por linguagem natural** | Anthropic Claude + PydanticAI | Alta |
| 3 | **BI Assistente (Text-to-SQL seguro)** | Claude + Guardrails Pydantic | Alta |
| 4 | **Predição de No-Show** | XGBoost + Celery | Média |

### Exemplo: Agendamento por Voz/Chat

```python
# O cliente envia: "Quero cortar amanhã à tarde com Carlos"
# O LLM extrai: {profissional: "Carlos", data: "amanhã", periodo: "tarde"}
# A API retorna slots disponíveis automaticamente
```

### Segurança em IA

- ✅ **Guardrails com Pydantic:** toda saída de LLM é validada como JSON estruturado
- ✅ **Rate Limiting por tenant:** evita abuso de budget da API
- ✅ **Prompt Injection:** sanitização de inputs do usuário
- ✅ **Logs de auditoria:** toda interação com IA é registrada (LGPD)

---

## 🛡️ Segurança

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

### Proteção contra Race Conditions

```python
# Constraint que impede dois agendamentos sobrepostos
# para o mesmo profissional no mesmo intervalo
ALTER TABLE agenda_agendamento ADD CONSTRAINT chk_overlap
  EXCLUDE USING GIST (
    profissional_id WITH =,
    tstzrange(data_hora, data_hora + (duracao || ' minutes')::interval) WITH &&
  ) WHERE (status IN ('AGENDADO', 'CONCLUIDO'));
```

---

## 🚀 Como Executar

### Pré-requisitos

- Docker + Docker Compose
- Git
- Make (opcional, para automações)

### 1. Clonar o Repositório

```bash
git clone https://github.com/seu-usuario/barberhub.git
cd barberhub
```

### 2. Configurar Variáveis de Ambiente

```bash
cp .env.example .env
```

Edite o `.env` com suas credenciais (veja seção abaixo).

### 3. Subir os Containers

```bash
docker-compose up -d
```

Isso iniciará:
- Django (porta 8000)
- PostgreSQL 16 + PostGIS 3.4 + pgvector (porta 5432)
- Redis (porta 6379)
- Celery Worker
- Celery Beat

### 4. Executar Migrações

```bash
docker-compose exec web python manage.py migrate
```

### 5. Criar Superusuário

```bash
docker-compose exec web python manage.py createsuperuser
```

### 6. Acessar

- **API:** http://localhost:8000/api/v1/
- **Swagger:** http://localhost:8000/swagger/
- **ReDoc:** http://localhost:8000/redoc/
- **Admin Django:** http://localhost:8000/admin/

### Execução Local (sem Docker)

```bash
# Criar ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements/dev.txt

# Configurar PostgreSQL local com PostGIS + pgvector
# (veja docs/database-setup.md)

# Executar migrações
python manage.py migrate

# Rodar servidor
python manage.py runserver

# Em outro terminal, rodar Celery
celery -A config worker -l info
celery -A config beat -l info
```

---

## 🔧 Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
# Django
SECRET_KEY=sua-chave-super-secreta-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_SETTINGS_MODULE=config.settings.dev

# Banco de Dados
DATABASE_URL=postgis://barberhub:barberhub@db:5432/barberhub
POSTGRES_USER=barberhub
POSTGRES_PASSWORD=barberhub
POSTGRES_DB=barberhub

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# JWT
JWT_SECRET_KEY=outra-chave-super-secreta
JWT_ACCESS_TOKEN_LIFETIME=60  # minutos
JWT_REFRESH_TOKEN_LIFETIME=1440  # minutos (1 dia)

# APIs Externas
VIACEP_ENABLED=True
GOOGLE_GEOCODING_API_KEY=sua-chave-google-aqui

# IA
ANTHROPIC_API_KEY=sua-chave-anthropic-aqui
OPENAI_API_KEY=sua-chave-openai-aqui
LLM_MODEL=claude-3-5-sonnet-20241022
EMBEDDING_MODEL=text-embedding-3-small

# Email (produção)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.seuprovedor.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=seu-email
EMAIL_HOST_PASSWORD=sua-senha
```

---

## 🧪 Testes

### Executar Todos os Testes

```bash
# Com Docker
docker-compose exec web pytest

# Local
pytest

# Com cobertura
pytest --cov=apps --cov=services --cov=selectors --cov-report=html

# Abrir relatório de cobertura
open htmlcov/index.html
```

### Tipos de Testes

| Tipo | Comando | Descrição |
|---|---|---|
| **Unitários** | `pytest tests/unit/` | Services, Selectors, Utils |
| **Integração** | `pytest tests/integration/` | APIs, Multi-tenancy, RLS |
| **E2E** | `pytest tests/e2e/` | Fluxos completos |
| **Carga** | `locust -f locustfile.py` | Testes de performance |

### Cobertura Mínima

- **Serviços:** 90%
- **Selectors:** 85%
- **Views/API:** 80%
- **Models:** 70%

---

## 🎯 Qualidade de Código

### Ferramentas

| Ferramenta | Propósito |
|---|---|
| **Black** | Formatação automática |
| **Ruff** | Linting ultrarrápido |
| **isort** | Ordenação de imports |
| **MyPy** | Tipagem estática |
| **pre-commit** | Hooks de validação |
| **pytest** | Testes |
| **pytest-cov** | Cobertura |
| **Locust** | Testes de carga |

### Instalação de Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

### Padrões Obrigatórios

1. ✅ Views são finas — toda lógica vai para Services/Selectors
2. ✅ Models nunca são acessados diretamente nas views — sempre via Selectors
3. ✅ Toda query multi-tenant usa `TenantManager` (nunca `objects.all()`)
4. ✅ Toda criação/alteração passa por Service (validação + auditoria)
5. ✅ Toda API pública tem testes unitários + integração
6. ✅ Toda feature nova deve passar pelo code review de pelo menos 1 sênior

---

## 🗺️ Roadmap

### ✅ Sprint 0 — Fundação (Concluída)
- [x] Setup Docker Compose (Django + PostGIS + pgvector + Redis)
- [x] Custom User Model + JWT Auth
- [x] AbstractTimestampedModel + TenantManager + RLS
- [x] Model `tenants_barbearia` com GEOGRAPHY

### 🚧 Sprint 1 — Geolocalização (Em andamento)
- [ ] Integração ViaCEP + Google Geocoding
- [ ] `core_enderecocache` com índice único
- [ ] US01: Busca por proximidade (raio 10km em metros)
- [ ] Testes de performance PostGIS

### 📋 Sprint 2 — Agenda e Multi-tenant
- [ ] `core_servico`, `core_profissional`, `core_vinculo`
- [ ] `core_horario_funcionamento` + `core_folga`
- [ ] US02: Motor de agendamento com ExclusionConstraint
- [ ] US03 + US04: Endpoints do barbeiro
- [ ] Testes de race condition

### 📋 Sprint 3 — BI e Dashboard
- [ ] US05: EstatísticasService + Materialized View
- [ ] US06: Blindagem multi-tenant (testes de invasão)
- [ ] Celery Beat para atualização da MV
- [ ] Integração com ApexCharts no frontend

### 📋 Sprint 4 — IA e Diferenciais
- [ ] pgvector + embeddings de serviços
- [ ] US01.1: Busca semântica
- [ ] US02.1: Agendamento por linguagem natural (Anthropic)
- [ ] US05.1: BI Assistente com guardrails Pydantic

### 📋 Sprint 5 — Hardening
- [ ] Testes de carga (Locust)
- [ ] Auditoria de segurança (pentest interno)
- [ ] LGPD: logs de auditoria, política de retenção
- [ ] Documentação OpenAPI (Swagger) completa

### 📋 Fase Futura
- [ ] Predição de No-Show (XGBoost)
- [ ] Recomendação automática de horários
- [ ] Integração com pagamentos (Stripe/Mercado Pago)
- [ ] Notificações push (Firebase)
- [ ] App mobile offline-first

---

## 🤝 Como Contribuir

Contribuições são bem-vindas! Siga o fluxo:

1. **Fork** o projeto
2. Crie uma **branch** para sua feature (`git checkout -b feature/nova-feature`)
3. **Commit** suas mudanças (`git commit -m 'feat: adiciona nova feature'`)
   - Siga o padrão [Conventional Commits](https://www.conventionalcommits.org/)
4. **Push** para a branch (`git push origin feature/nova-feature`)
5. Abra um **Pull Request**

### Padrões de Commit

- `feat:` nova funcionalidade
- `fix:` correção de bug
- `docs:` alterações na documentação
- `style:` formatação, sem alteração de lógica
- `refactor:` refatoração de código
- `test:` adição ou correção de testes
- `chore:` tarefas de manutenção

### Definition of Done (DoD)

Cada feature só entra em produção quando:
- [ ] Código revisado por pelo menos 1 sênior
- [ ] Testes unitários com cobertura > 80%
- [ ] Testes de integração passando
- [ ] Multi-tenancy testado (tenant A não vê dados de B)
- [ ] Performance validada (query < 200ms)
- [ ] Documentação OpenAPI atualizada
- [ ] LGPD: dados sensíveis mascarados em logs

---

## 📚 Documentação da API

Após executar o projeto, acesse:

- **Swagger UI:** http://localhost:8000/swagger/
- **ReDoc:** http://localhost:8000/redoc/
- **OpenAPI JSON:** http://localhost:8000/api/v1/schema/

### Endpoints Principais

```
POST   /api/v1/auth/login/              # Login (retorna JWT)
POST   /api/v1/auth/refresh/            # Refresh token
POST   /api/v1/auth/register/           # Cadastro

GET    /api/v1/barbearias/              # Lista barbearias (com busca geo)
GET    /api/v1/barbearias/{id}/         # Detalhe da barbearia
POST   /api/v1/barbearias/              # Cria barbearia (DONO)

GET    /api/v1/servicos/                # Lista serviços da barbearia
GET    /api/v1/servicos/busca-semantica/?q=relaxar  # Busca por IA

GET    /api/v1/profissionais/{id}/agenda/?data=2026-07-08  # Grade horária
POST   /api/v1/agendamentos/            # Cria agendamento

GET    /api/v1/minha-agenda/            # Agenda do barbeiro logado
GET    /api/v1/minhas-comissoes/        # Comissões do barbeiro

GET    /api/v1/estatisticas/            # BI do dono
POST   /api/v1/estatisticas/pergunta/   # BI Assistente (IA)
```

---

## 📊 Performance

### Benchmarks Esperados

| Operação | Meta | Estratégia |
|---|---|---|
| Busca por proximidade (10km) | < 100ms | PostGIS GIST index |
| Grade horária do barbeiro | < 150ms | Índice parcial |
| Dashboard BI | < 200ms | Materialized View |
| Busca semântica (pgvector) | < 300ms | IVFFlat index |
| Agendamento (com ExclusionConstraint) | < 250ms | Constraint nativo |

### Otimizações Aplicadas

- ✅ **PostGIS `GEOGRAPHY`**: cálculos em metros reais, sem conversões
- ✅ **Índices parciais**: apenas registros relevantes indexados
- ✅ **Materialized Views**: BI pré-calculado
- ✅ **Cache de CEP**: evita chamadas pagas a APIs externas
- ✅ **`select_related` / `prefetch_related`**: evita N+1 queries
- ✅ **`pgvector` com IVFFlat**: busca vetorial otimizada

---

## 📄 Licença

Este projeto está licenciado sob a **MIT License** — veja o arquivo [LICENSE](LICENSE) para detalhes.

---

## 👨‍💻 Autor

**Gilmar Rodrigues Campelo**

Projeto desenvolvido como estudo de arquitetura de software, desenvolvimento backend com Django e construção de uma plataforma SaaS escalável para gestão de barbearias, com foco em **boas práticas de engenharia, segurança multi-tenant e inteligência artificial aplicada**.

- 📧 Email: [seu-email@exemplo.com]
- 💼 LinkedIn: [seu-linkedin]
- 🐙 GitHub: [seu-github]

---

## 🙏 Agradecimentos

- Comunidade Django
- Comunidade PostGIS
- Anthropic e OpenAI (pelas APIs de IA)
- Todos os contribuidores

---

<div align="center">

**Feito com ❤️ e muito ☕ por Gilmar Rodrigues Campelo**

[⬆ Voltar ao topo](#-barberhub-saas)

</div>