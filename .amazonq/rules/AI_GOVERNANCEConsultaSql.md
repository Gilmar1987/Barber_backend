\# AI\_GOVERNANCE.md

\#\# Objetivo

Este documento define as diretrizes obrigatórias para qualquer código gerado pela IA neste projeto.

A IA deve priorizar:

\- Código limpo  
\- Escalabilidade  
\- Segurança  
\- Testabilidade  
\- Baixo acoplamento  
\- Alta coesão  
\- Fácil manutenção

Nunca gerar código apenas para funcionar.  
Sempre gerar código preparado para produção.

\---

\# Arquitetura

Utilizar arquitetura em camadas.

Presentation  
Application  
Domain  
Infrastructure

Nunca colocar regra de negócio na View.

Toda regra deve ficar na camada de Service.

A camada Repository deve acessar exclusivamente o banco de dados.

\---

\# Organização

Cada módulo deve possuir:

models.py

serializers.py

repositories.py

services.py

views.py

urls.py

permissions.py

validators.py

filters.py

tests/

\---

\# Banco de Dados

Banco PostgreSQL.

Sempre utilizar migrations.

Nunca executar SQL diretamente.

Usar ORM do Django.

Criar índices quando necessário.

Utilizar transações para operações críticas.

\---

\# API

Utilizar Django REST Framework.

Todas as respostas devem seguir um padrão.

Exemplo

{  
    "success": true,  
    "message": "...",  
    "data": {}  
}

Em caso de erro

{  
    "success": false,  
    "message": "...",  
    "errors": {}  
}

\---

\# Segurança

Utilizar JWT.

Nunca retornar informações sensíveis.

Validar permissões em todas as rotas.

Utilizar HTTPS.

Nunca deixar credenciais no código.

Sempre utilizar variáveis de ambiente.

\---

\# Docker

Toda aplicação deve possuir

Dockerfile

docker-compose.yml

.env.example

A aplicação deve iniciar apenas com

docker compose up

\---

\# Kubernetes / Rancher

Todo projeto deve possuir

Deployment

Service

Ingress

ConfigMap

Secret

Health Check

Readiness Probe

Liveness Probe

Resource Limits

\---

\# Código

Sempre utilizar type hints.

Criar docstrings.

Utilizar nomes descritivos.

Evitar duplicação.

Não utilizar números mágicos.

Criar constantes.

\---

\# Services

Toda regra de negócio deve ficar em Services.

Nunca colocar regra na View.

Nunca colocar regra no Serializer.

\---

\# Repository

Toda consulta ao banco deve passar pelo Repository.

Nunca acessar Model diretamente na View.

\---

\# Logs

Registrar

Login

Erros

Alterações

Exclusões

Acessos

\---

\# Auditoria

Toda alteração deve registrar

Usuário

Data

Hora

IP

Operação realizada

\---

\# Testes

Criar

Testes Unitários

Testes de Integração

Cobertura mínima de 80%.

\---

\# Documentação

Gerar automaticamente

Swagger

OpenAPI

README atualizado

\---

\# Git

Commits seguindo Conventional Commits.

Exemplo

feat:

fix:

refactor:

docs:

test:

chore:

\---

\# Performance

Utilizar

select\_related()

prefetch\_related()

Paginação

Cache quando necessário

Evitar consultas N+1

\---

\# Qualidade

Seguir

PEP8

SOLID

DRY

KISS

Clean Code

Clean Architecture

\---

\# IA

Sempre que gerar código:

1\. Explicar a solução.

2\. Gerar código completo.

3\. Gerar testes.

4\. Atualizar documentação.

5\. Explicar impactos da alteração.

6\. Não remover funcionalidades existentes.

7\. Perguntar antes de realizar mudanças destrutivas.

8\. Reutilizar componentes existentes.

9\. Priorizar segurança.

10\. Priorizar legibilidade.

\---

\# Objetivo Final

Todo código produzido deve estar pronto para ambiente corporativo, ser escalável, seguro, bem documentado e facilmente mantido por equipes de desenvolvimento.  
