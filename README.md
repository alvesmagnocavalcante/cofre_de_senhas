# Cofre Carmel Hotéis

Sistema interno em Django para a organização Carmel, com criptografia Fernet em repouso, compartilhamento controlado e auditoria de acesso.

## Documentação

- [Manual do usuário e do administrador](docs/MANUAL_DO_USUARIO.md)
- [Documentação técnica e operacional](docs/DOCUMENTACAO_TECNICA.md)

## Executar localmente

```powershell
uv sync
Copy-Item .env.example .env
uv run python manage.py migrate
uv run python manage.py runserver
```

Acesse `http://127.0.0.1:8000/cadastro/`. Em desenvolvimento, a chave do cofre é derivada da `SECRET_KEY` somente para facilitar o primeiro uso.

Todo usuário criado pela tela de cadastro entra automaticamente na organização Carmel.

Novos cadastros permanecem inativos até aprovação no painel próprio em `/painel/` ou pelo Django Admin.

## Configuração de produção

Gere chaves independentes:

```powershell
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Defina obrigatoriamente:

```text
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=<chave-longa-aleatoria>
VAULT_ENCRYPTION_KEYS=<chave-fernet>
DJANGO_ALLOWED_HOSTS=senhas.exemplo.com
DATABASE_URL=postgres://<usuario>:<senha>@<host>:<porta>/<banco>?sslmode=require
```

O arquivo `.env` é carregado automaticamente e não entra no Git. Se a senha do banco possuir caracteres especiais, use a URI copiada diretamente da Aiven ou codifique esses caracteres no formato de URL.

Para rotacionar a criptografia sem perder acesso, configure `VAULT_ENCRYPTION_KEYS=CHAVE_NOVA,CHAVE_ANTIGA`. Novos valores usam a primeira chave; as demais permanecem disponíveis para leitura. Faça backup das chaves fora do banco. Perdê-las torna os segredos irrecuperáveis.

## Regras implementadas

- Todo usuário cadastrado pertence automaticamente à Carmel.
- Cadastros públicos exigem aprovação administrativa antes do primeiro acesso.
- Cinco falhas de login bloqueiam a combinação usuário/IP por 15 minutos.
- **Somente eu**: apenas o criador localiza, copia, revela, edita ou exclui; nem administradores possuem acesso.
- **Usuários específicos**: destinatários selecionados localizam e copiam; o criador e administradores controlam a credencial.
- **Todos da Carmel**: membros ativos localizam e copiam; o criador e administradores controlam a credencial.
- Administradores controlam credenciais compartilhadas, mas não acessam credenciais pessoais de outros usuários.
- Senhas e observações são criptografadas no banco.
- Credenciais podem ser organizadas em grupos e registrar IP ou nome do equipamento.
- O criador ou um administrador pode renomear grupos sem perder as credenciais vinculadas.
- O painel próprio em `/painel/` apresenta indicadores, pesquisa, aprovações, suspensões, alteração de perfil, encerramento de sessões, desbloqueio de login, gestão de grupos e auditoria recente.
- Revelação e cópia exigem `POST` com CSRF, não aceitam cache e geram auditoria.
- Segredos nunca são enviados na renderização HTML nem gravados na auditoria.

## Antes de produção

- Use PostgreSQL e TLS no proxy reverso.
- Armazene as chaves em um gerenciador de segredos, nunca no repositório.
- Configure backup criptografado e teste restauração.
- Adicione autenticação em dois fatores, acesso corporativo e política de sessão centralizada.
- Restrinja o Django Admin a administradores e rede confiável.

## Docker de produção

Construir a imagem:

```powershell
docker build -t cofre-carmel:latest .
```

Aplicar migrações como uma etapa única da implantação:

```powershell
docker run --rm --env-file .env cofre-carmel:latest python manage.py migrate
```

O comando padrão da imagem inicia o Gunicorn na porta `8000`. Coloque o contêiner atrás de um proxy reverso com HTTPS e não inclua o `.env` na imagem.

## Testes

```powershell
uv run python manage.py test
uv run python manage.py check
```

Execute `python manage.py check --deploy` com as variáveis reais de produção carregadas; a configuração de desenvolvimento gera alertas intencionais nesse comando.
