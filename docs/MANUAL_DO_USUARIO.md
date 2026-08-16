# Manual do Cofre Carmel

## 1. Finalidade

O Cofre Carmel organiza credenciais pessoais e compartilhadas da Carmel Hotéis. Senhas e observações ficam criptografadas no banco de dados.

## 2. Perfis de acesso

| Perfil | Permissões principais |
| --- | --- |
| Membro | Criar grupos e credenciais, gerenciar o próprio conteúdo e copiar credenciais compartilhadas consigo |
| Administrador | Permissões de membro e acesso ao painel administrativo |
| Proprietário | Mesmo acesso administrativo, reservado ao responsável principal pelo cofre |

Administradores não recebem permissão automática para revelar senhas criadas por outras pessoas.

## 3. Criar uma conta

1. Acesse `/cadastro/`.
2. Informe um usuário com até 150 caracteres.
3. Crie uma senha com pelo menos 8 caracteres que não seja comum, apenas numérica ou semelhante ao usuário.
4. Selecione **Solicitar cadastro**.
5. Aguarde a aprovação de um administrador.

O cadastro não permite acesso imediato. A conta e o vínculo com a Carmel permanecem inativos até a aprovação.

## 4. Entrar no sistema

1. Acesse `/conta/login/`.
2. Informe usuário e senha.
3. Selecione **Entrar**.

Após cinco tentativas incorretas para a mesma combinação de usuário e endereço IP, o acesso fica bloqueado por 15 minutos. Um administrador também pode remover o bloqueio pelo painel.

O botão **Modo escuro** alterna o tema da interface e guarda a preferência no navegador.

## 5. Organizar credenciais

### Criar um grupo

1. No cofre, selecione **Novo grupo**.
2. Informe um nome, como `Servidores`, `Windows` ou `Sistemas internos`.
3. Selecione **Salvar**.

Os nomes não podem se repetir na organização. O criador ou um administrador pode renomear e excluir o grupo. Excluir um grupo não exclui suas credenciais: elas voltam para **Sem grupo**.

### Exibição dos grupos

- Credenciais sem grupo aparecem primeiro.
- Os demais grupos podem ser expandidos ou recolhidos.
- A pesquisa encontra grupo, título, IP, equipamento, usuário ou site.

## 6. Cadastrar uma credencial

1. Selecione **Nova senha**.
2. Preencha os campos necessários.
3. Escolha quem pode acessar.
4. Selecione **Salvar**.

| Campo | Uso |
| --- | --- |
| Grupo | Organização opcional da credencial |
| Título | Nome usado para localizar a credencial |
| IP ou nome do equipamento | Servidor, estação ou endereço de rede |
| Usuário | Usuário utilizado no sistema de destino |
| Site | Endereço web opcional |
| Senha | Segredo criptografado |
| Observações | Informação adicional criptografada |

## 7. Escolher o compartilhamento

### Somente eu

- Apenas o criador acessa a credencial.
- A lista de usuários fica oculta.

### Usuários específicos

- A lista de usuários ativos é exibida.
- Marque uma ou mais pessoas.
- Somente os usuários marcados conseguem localizar e copiar a credencial.

### Todos da Carmel

- Todos os usuários ativos aparecem marcados.
- Qualquer membro ativo da Carmel consegue localizar e copiar a credencial.

Grupos servem apenas para organização e não concedem acesso.

## 8. Mostrar e copiar senhas

| Ação | Criador | Usuário autorizado |
| --- | --- | --- |
| Localizar a credencial | Sim | Sim |
| Copiar a senha | Sim | Sim |
| Mostrar a senha na tela | Sim | Não |
| Editar | Sim | Não |
| Excluir | Sim | Não |
| Alterar compartilhamento | Sim | Não |

Use **Mostrar** apenas quando necessário. O valor volta a ser ocultado após 30 segundos. A opção **Copiar** envia a senha diretamente para a área de transferência sem incluí-la no HTML inicial da página.

## 9. Editar ou excluir

- Use **Editar** no cartão de uma credencial criada por você.
- Deixe a senha vazia durante a edição para manter o valor atual.
- Use **Excluir** para remover definitivamente a credencial.

A exclusão não possui lixeira. Confirme o título antes de continuar.

## 10. Painel administrativo

O link **Painel administrativo** aparece para proprietários, administradores e usuários `staff` do Django.

### Usuários

O painel permite:

- aprovar cadastros;
- suspender acessos;
- alterar o perfil entre membro e administrador;
- encerrar sessões abertas;
- remover bloqueios causados por tentativas de login;
- pesquisar usuários.

O próprio administrador não pode suspender sua conta nem encerrar sua sessão pelo painel.

### Grupos

O painel apresenta o responsável, a quantidade de credenciais privadas e compartilhadas e permite editar ou excluir grupos.

### Atividades recentes

O histórico informa data, usuário responsável, ação, referência e endereço IP. Ele registra criação, alteração, exclusão, cópia, revelação, compartilhamento e ações administrativas.

As senhas e observações nunca são gravadas na auditoria.

## 11. Administração avançada do Django

A rota `/admin/` é destinada à manutenção técnica. Ela não substitui o painel administrativo do Cofre Carmel.

Use essa área apenas para:

- manutenção excepcional de cadastros;
- consulta técnica dos modelos;
- ações administrativas em lote;
- investigação de auditoria.

Eventos de auditoria são somente leitura. Os vínculos exibidos em **Cadastros de usuários** não oferecem exclusão pelo Django Admin.

## 12. Problemas comuns

### Cadastro aprovado, mas sem acesso

Confirme no painel se o usuário e o vínculo com a Carmel estão ativos.

### Acesso temporariamente bloqueado

Aguarde 15 minutos ou solicite a um administrador que use **Desbloquear**.

### Uma credencial não aparece

Verifique se você é o criador, foi selecionado individualmente ou se ela foi compartilhada com todos. Confirme também se não existe uma pesquisa ativa.

### Não consigo mostrar uma senha compartilhada

Esse é o comportamento esperado. Usuários autorizados podem copiar; somente o criador pode mostrar o valor na tela.

### Usuário não aparece na seleção

Somente usuários aprovados e ativos da Carmel são listados.

### O navegador não permite copiar

Confirme a permissão da área de transferência. Fora do ambiente local, a aplicação deve ser acessada por HTTPS para utilizar esse recurso com segurança.

## 13. Boas práticas

- Compartilhe somente com quem precisa do acesso.
- Prefira **Usuários específicos** quando o acesso não for geral.
- Revise periodicamente credenciais compartilhadas.
- Não cole senhas em mensagens, chamados ou documentos sem proteção.
- Troque a senha no sistema de destino quando alguém deixar de precisar dela.
- Bloqueie a estação ao se afastar e encerre a sessão em computadores compartilhados.
