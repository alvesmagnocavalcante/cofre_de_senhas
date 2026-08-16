# Documentação técnica do Cofre Carmel

## 1. Escopo

Aplicação web interna em Django para armazenamento criptografado, organização e compartilhamento controlado de credenciais da Carmel Hotéis.

## 2. Tecnologias

| Componente | Tecnologia |
| --- | --- |
| Linguagem | Python 3.12 ou superior |
| Framework | Django 6.1 |
| Criptografia | `cryptography` com Fernet/MultiFernet |
| Proteção de login | `django-axes` |
| Banco | PostgreSQL por `DATABASE_URL`, com SQLite local como alternativa |
| Dependências e execução | `uv` |
| Interface | Templates Django, CSS e JavaScript nativo |

As versões efetivas e restrições estão em `pyproject.toml` e `uv.lock`.

## 3. Estrutura do projeto

| Caminho | Responsabilidade |
| --- | --- |
| `app/settings.py` | Configuração do Django, segurança, login e ambiente |
| `app/urls.py` | Rotas gerais, autenticação e Django Admin |
| `gerenciador/models.py` | Organização, usuários, grupos, credenciais e auditoria |
| `gerenciador/forms.py` | Validação dos cadastros e credenciais |
| `gerenciador/access.py` | Autorização e decoradores de acesso |
| `gerenciador/queries.py` | Consultas do cofre e consolidação do painel |
| `gerenciador/security.py` | Criptografia e descriptografia |
| `gerenciador/services.py` | Auditoria, sessões, aprovação e bloqueios |
| `gerenciador/views.py` | Casos de uso e respostas HTTP |
| `gerenciador/signals.py` | Vínculo automático com a organização Carmel |
| `templates/` | Interface renderizada no servidor |
| `static/` | CSS, JavaScript, logotipo e ilustração |
| `gerenciador/tests.py` | Testes funcionais e de segurança |

## 4. Modelo de domínio

| Modelo | Finalidade |
| --- | --- |
| `Organization` | Organização proprietária dos dados |
| `Membership` | Vínculo, perfil e situação de um usuário |
| `VaultGroup` | Agrupamento visual das credenciais |
| `VaultItem` | Metadados, segredo, observações e compartilhamento |
| `AuditEvent` | Registro das ações sensíveis e administrativas |

Relações principais:

- uma organização possui vínculos, grupos, credenciais e eventos;
- um usuário possui um vínculo único por organização;
- uma credencial possui um criador e um grupo opcional;
- `VaultItem.shared_with` representa os destinatários do compartilhamento específico;
- a exclusão de um grupo usa `SET_NULL` e preserva as credenciais;
- criadores e responsáveis de auditoria usam `PROTECT` onde a remoção prejudicaria a rastreabilidade.

## 5. Autorização

O sistema usa a organização com `slug=carmel`, definida em `gerenciador/constants.py`.

### Entrada nas áreas protegidas

1. O Django confirma a autenticação da sessão.
2. `membership_required` busca um vínculo ativo com a Carmel.
3. A consulta aplica a visibilidade da credencial.
4. A própria view valida autoria e método HTTP para ações sensíveis.

### Regra de visibilidade

Uma credencial é retornada quando pelo menos uma condição é verdadeira:

- `created_by` é o usuário atual;
- `visibility` é `organization`;
- `visibility` é `specific` e o usuário está em `shared_with`.

### Matriz de autorização

| Operação | Criador | Destinatário | Administrador não criador |
| --- | --- | --- | --- |
| Listar metadados | Sim | Conforme compartilhamento | Sim |
| Copiar segredo | Sim | Conforme compartilhamento | Sim |
| Revelar segredo | Sim | Não | Sim |
| Editar ou excluir | Sim | Não | Sim |
| Alterar compartilhamento | Sim | Não | Sim |
| Administrar usuários e grupos | Conforme perfil | Conforme perfil | Sim |

O perfil administrativo concede controle completo sobre as credenciais da organização. Cópias, revelações e alterações continuam registradas na auditoria.

## 6. Criptografia

`VaultItem.secret_encrypted` e `VaultItem.notes_encrypted` armazenam bytes produzidos pelo Fernet. O banco não recebe o texto puro desses campos.

`MultiFernet` utiliza:

- a primeira chave para novas criptografias;
- todas as chaves configuradas para descriptografia, na ordem informada.

Em desenvolvimento, quando `VAULT_ENCRYPTION_KEYS` está vazia, uma chave é derivada de `SECRET_KEY`. Esse comportamento existe apenas para facilitar a execução local e não deve ser usado em produção.

### Gerar uma chave

```powershell
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Rotacionar chaves

1. Gere uma nova chave.
2. Configure `VAULT_ENCRYPTION_KEYS=CHAVE_NOVA,CHAVE_ANTIGA`.
3. Reinicie a aplicação.
4. Mantenha a chave antiga enquanto existirem valores criptografados com ela.

O projeto ainda não possui um comando de recriptografia em lote. Remover uma chave antiga antes de recriptografar os registros torna esses dados ilegíveis.

## 7. Proteções implementadas

- CSRF nas operações `POST`;
- cookies de sessão `HttpOnly` e `SameSite=Lax`;
- redirecionamento HTTPS, cookies seguros e HSTS quando `DEBUG=false`;
- bloqueio de enquadramento por `X-Frame-Options: DENY`;
- `nosniff` para tipos de conteúdo;
- bloqueio após cinco falhas por usuário e IP durante 15 minutos;
- respostas de revelação com `Cache-Control: no-store, private`;
- segredo ausente do HTML inicial e da auditoria;
- revelação automaticamente ocultada após 30 segundos;
- seleção de destinatários limitada a membros ativos;
- consultas sempre limitadas à organização do vínculo ativo.

## 8. Auditoria

`record_audit` armazena organização, usuário responsável, tipo de ação, identificador, título da referência, endereço IP e data. São auditadas ações sobre credenciais, compartilhamento, grupos, usuários, sessões e bloqueios. Segredos e observações não são incluídos.

## 9. Instalação local

### Pré-requisitos

- Python 3.12 ou superior;
- `uv` instalado;
- acesso à internet para instalar dependências;
- acesso do navegador ao Google Fonts é opcional, pois existe uma fonte alternativa local.

### Preparação

```powershell
uv sync
Copy-Item .env.example .env
uv run python manage.py migrate
uv run python manage.py createsuperuser
```

### Execução

```powershell
uv run python manage.py runserver
```

| Área | Endereço local |
| --- | --- |
| Cofre | `http://127.0.0.1:8000/` |
| Cadastro | `http://127.0.0.1:8000/cadastro/` |
| Login | `http://127.0.0.1:8000/conta/login/` |
| Painel próprio | `http://127.0.0.1:8000/painel/` |
| Django Admin | `http://127.0.0.1:8000/admin/` |

A migração de dados cria a organização Carmel. O sinal `post_save` vincula novas contas automaticamente a ela.

## 10. Variáveis de ambiente

| Variável | Obrigatória em produção | Finalidade |
| --- | --- | --- |
| `DJANGO_DEBUG` | Sim | Use `false` em produção |
| `DJANGO_SECRET_KEY` | Sim | Assinatura e segurança interna do Django |
| `VAULT_ENCRYPTION_KEYS` | Sim | Chaves Fernet separadas por vírgula |
| `DJANGO_ALLOWED_HOSTS` | Sim | Hosts aceitos, separados por vírgula |
| `DATABASE_URL` | Sim | URI de conexão PostgreSQL fornecida pela Aiven |
| `DATABASE_CONN_MAX_AGE` | Não | Persistência da conexão em segundos; padrão 60 |
| `DATABASE_CA_CERT` | Recomendado | Caminho absoluto do certificado CA da Aiven |
| `DJANGO_HSTS_SECONDS` | Não | Duração do HSTS; padrão 31536000 |
| `EMAIL_HOST` | Não | Servidor SMTP |
| `EMAIL_PORT` | Não | Porta SMTP; padrão 587 |
| `EMAIL_HOST_USER` | Não | Usuário SMTP |
| `EMAIL_HOST_PASSWORD` | Não | Senha SMTP |
| `EMAIL_USE_TLS` | Não | TLS no SMTP; padrão `true` |

Exemplo mínimo:

```text
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=<valor-longo-e-aleatorio>
VAULT_ENCRYPTION_KEYS=<chave-fernet>
DJANGO_ALLOWED_HOSTS=cofre.carmelhoteis.com.br
DATABASE_URL=postgres://usuario:senha@host:porta/defaultdb?sslmode=require
```

Não grave esses valores no repositório.

### Configurar o PostgreSQL da Aiven

1. Copie `.env.example` para `.env`.
2. Na Aiven, revele e copie a **Service URI** completa.
3. Cole a URI em `DATABASE_URL` sem espaços ou quebras de linha.
4. Para maior segurança, baixe o certificado CA, salve-o fora do repositório e informe o caminho em `DATABASE_CA_CERT`.
5. Execute `uv run python manage.py migrate`.
6. Execute `uv run python manage.py check`.

Com apenas `sslmode=require`, o tráfego usa TLS, mas o certificado do servidor não é validado. Quando `DATABASE_CA_CERT` está configurada, o sistema força `sslmode=verify-full` e valida a CA e o hostname.

A senha deve estar codificada como URL. A URI copiada da Aiven normalmente já está no formato adequado. Não envie a senha por mensagens nem a inclua em capturas de tela.

## 11. Rotas principais

| Método | Rota | Uso |
| --- | --- | --- |
| GET | `/` | Lista e pesquisa do cofre |
| GET, POST | `/cadastro/` | Solicitação de cadastro |
| GET, POST | `/senhas/nova/` | Nova credencial |
| GET, POST | `/senhas/<uuid>/editar/` | Edição pelo criador |
| POST | `/senhas/<uuid>/excluir/` | Exclusão pelo criador |
| POST | `/senhas/<uuid>/revelar/` | Revelação ou cópia autorizada |
| GET, POST | `/grupos/novo/` | Novo grupo |
| GET, POST | `/grupos/<uuid>/editar/` | Renomear grupo |
| POST | `/grupos/<uuid>/excluir/` | Excluir grupo |
| GET | `/painel/` | Painel administrativo |

As operações administrativas de usuário ficam sob `/painel/usuarios/<id>/` e aceitam `POST`.

## 12. Testes e verificações

```powershell
uv run python manage.py test
uv run python manage.py check
uv run python manage.py makemigrations --check
uvx ruff check app gerenciador --exclude gerenciador/migrations
```

Com as variáveis reais de produção carregadas:

```powershell
uv run python manage.py check --deploy
```

## 13. Migrações

Após alterar modelos:

```powershell
uv run python manage.py makemigrations
uv run python manage.py migrate
```

Revise migrações que removem ou transformam campos. A migração `0007` preserva o compartilhamento antigo ao converter `is_shared` para os níveis de visibilidade atuais.

## 14. Backup e restauração

O backup funcional exige, no mesmo ponto no tempo:

- banco `db.sqlite3` ou backup do banco adotado em produção;
- conjunto completo de chaves em `VAULT_ENCRYPTION_KEYS`;
- `DJANGO_SECRET_KEY` usada pelo ambiente;
- versão do código e migrações aplicadas.

Teste a restauração em ambiente isolado. Um backup do banco sem as chaves Fernet não permite recuperar senhas e observações.

## 15. Implantação

Antes de produção:

1. Defina todas as variáveis obrigatórias.
2. Execute migrações e testes.
3. Execute o contêiner Gunicorn atrás de proxy reverso com TLS.
4. Restrinja `/admin/` à rede administrativa.
5. Confirme o carregamento dos arquivos estáticos pelo WhiteNoise.
6. Automatize backup criptografado e restauração testada.
7. Monitore erros, falhas de login e eventos administrativos.

### Imagem Docker

O `Dockerfile` usa duas etapas:

- `builder`: instala as versões travadas pelo `uv.lock` e executa `collectstatic`;
- `runtime`: contém Python, aplicação, ambiente virtual e arquivos estáticos.

O processo final roda com usuário sem privilégios e inicia `app.wsgi` pelo Gunicorn. A imagem não contém `.env`, banco SQLite, backups ou certificados locais.

```powershell
docker build -t cofre-carmel:latest .
```

Execute migrações uma vez antes de iniciar ou atualizar as réplicas:

```powershell
docker run --rm --env-file .env cofre-carmel:latest python manage.py migrate
```

O comando padrão da imagem equivale a:

```text
gunicorn app.wsgi:application --config gunicorn.conf.py
```

Variáveis opcionais do processo:

| Variável | Padrão | Uso |
| --- | --- | --- |
| `PORT` | `8000` | Porta interna HTTP |
| `GUNICORN_WORKERS` | `2` | Quantidade de processos |
| `GUNICORN_THREADS` | `2` | Linhas de execução por processo |
| `GUNICORN_TIMEOUT` | `30` | Limite de uma requisição em segundos |
| `DJANGO_TRUST_PROXY_SSL_HEADER` | `false` | Confia em `X-Forwarded-Proto` enviado pelo proxy |

Ative `DJANGO_TRUST_PROXY_SSL_HEADER=true` somente quando o contêiner não estiver diretamente exposto e o proxy confiável remover o cabeçalho recebido do cliente antes de definir seu próprio valor.

Não execute `migrate` automaticamente em todas as réplicas. Use uma etapa única de implantação para evitar concorrência entre alterações de esquema.

### Limitações atuais

- SQLite continua disponível apenas quando `DATABASE_URL` não está definida;
- não há autenticação multifator;
- não existe comando de recriptografia em lote;
- a retenção da auditoria ainda não está automatizada;
- Inter depende do Google Fonts, com a fonte do sistema como alternativa;
- o proxy reverso e o certificado HTTPS pertencem à infraestrutura de implantação.

O PostgreSQL é selecionado automaticamente quando `DATABASE_URL` está definida.

## 16. Manutenção segura

- Nunca registre segredos em logs, testes ou mensagens de erro.
- Não altere `visible_items` sem testes de autorização.
- Toda nova ação sensível deve aceitar `POST`, validar CSRF e gerar auditoria.
- Preserve a auditoria das ações administrativas sobre credenciais de terceiros.
- Execute testes antes e depois de cada migração.
- Atualize dependências somente após revisar segurança e compatibilidade.
