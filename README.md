# Projeto Integrador — Etapa 04 — Sistema Supervisório Industrial

Aplicação **Streamlit** com as **seis telas** exigidas no enunciado do SENAI, baseada nos quatro códigos de aula enviados (`app.py`, `autenticacao.py`, `classe_gerenciador.py`, `telas.py`).

## O que funciona nesta versão

1. **Login:** autenticação `bcrypt` e autorização por perfil.
2. **Processos:** motor simulado, comandos de ligar/desligar, RPM, esteira em HTML/CSS, sensor, contador, temperatura atualizada automaticamente a cada 3 s.
3. **Banco de Dados:** consulta de eventos operacionais persistidos, filtros e exportação CSV.
4. **Gráficos:** histórico de temperatura, velocidade, contagem e quantidade de eventos.
5. **Cadastro de Usuários:** criação, alteração, ativação/desativação e troca de senha, apenas para administradores.
6. **Monitoramento de Segurança:** logs com níveis `INFO`, `WARNING`, `ERROR` e `CRITICAL`, identificação de tentativas de login inválidas; CloudWatch disponível se configurado.

## Instalação (Windows CMD ou PowerShell)

Extraia o ZIP e entre na pasta que contém `app.py`:

```bat
cd Projeto_Integrador_Etapa04
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```

Caso `py` não esteja disponível, use `python -m venv .venv`.

A aplicação abrirá em `http://localhost:8501`.

**Contas de teste no modo demonstração (APP_MODO_DEMO=1):**

| Usuário | Senha | Acesso |
|---|---|---|
| `admin` | `admin123` | Todas as telas |
| `operador` | `operador123` | Processos, Gráficos |
| `engenheiro` | `engenheiro123` | Todas exceto Cadastro |

**Importante:** as contas são somente para estudo e devem ser removidas/desabilitadas antes de publicar o projeto. O aplicativo as gera quando o modo demo está ativo e o usuário ainda não existe. Desativar o modo demo não remove usuários já criados; remova-os ou mude as senhas no cadastro.

## Banco de dados

- **Teste imediato:** por padrão, os dados são persistidos no arquivo SQLite `dados_supervisorio.db`, criado automaticamente na pasta do projeto. Essa opção substitui **temporariamente** o MySQL para simplificar os testes.
- **Requisito final:** configurar **MySQL**, como definido no enunciado. Crie o banco de dados `supervisorio` no MySQL e uma conta com permissões adequadas. Edite `DATABASE_URL` no arquivo `.env`, por exemplo: `mysql+pymysql://usuario:senha@127.0.0.1:3306/supervisorio`. As tabelas serão criadas na primeira inicialização. Para senhas com caracteres especiais na URL, aplique codificação de URL. Se iniciar um banco vazio com `APP_MODO_DEMO=0`, defina temporariamente `ADMIN_INICIAL_USUARIO` e `ADMIN_INICIAL_SENHA` (pelo menos 12 caracteres) no `.env` para criar o primeiro administrador; depois retire essas variáveis do `.env`.
- Nenhuma senha do banco deve ser enviada ao GitHub; `.env` está no `.gitignore`.

## Logs / CloudWatch

Os logs são escritos localmente em `sistema.log` através da classe `GerenciadorLog`.

Para enviar também ao **AWS CloudWatch**, crie previamente um *log group* e um *log stream* na AWS, configure credenciais/permissões IAM para `logs:PutLogEvents` e `logs:FilterLogEvents`, preencha `AWS_REGION`, `CLOUDWATCH_LOG_GROUP`, `CLOUDWATCH_LOG_STREAM`, e marque `CLOUDWATCH_ATIVO=1` no `.env`. O envio é feito por evento e a consulta da tela pode ser realizada no CloudWatch. Sem credenciais ou configuração, o sistema continua funcionando apenas com logs locais. **A integração CloudWatch não foi validada em uma conta AWS nesta entrega.**

## Limites desta entrega

- O motor, o sensor e a temperatura são **simulados em Python**, não estão conectados a um CLP. A integração **OPC UA + Open Industry Project** está reservada para a Etapa 06, após obtermos os `NodeIds` corretos do simulador da aula.
- A esteira em HTML/CSS é **ilustrativa**, e sua animação depende do estado simulado do processo.
- A publicação na **AWS EC2** da Aula 05 é opcional e **não está configurada** neste ZIP.
- O exemplo de Aula 06 usa PostgreSQL no RDS; este projeto utiliza SQLite no modo demonstração e aceita MySQL na configuração final, conforme o enunciado.
- Não deixe a aplicação de demonstração exposta publicamente. Para um ambiente real são necessários HTTPS, segurança de sessão, configurações de rede e proteção adicional contra ataques.

## Organização

```text
Projeto_Integrador_Etapa04/
├── app.py                  # Inicialização e navegação
├── autenticacao.py         # bcrypt, sessão e permissões
├── telas.py                # As seis telas
├── classe_gerenciador.py   # Logs locais / CloudWatch opcional
├── banco_dados.py          # Modelos SQLAlchemy: SQLite ou MySQL
├── simulador.py            # Motor / sensor / temperatura (demonstração)
├── requirements.txt
├── .env.example
├── .gitignore
└── tests/
    └── test_dados.py
```

## Sequência para apresentar em sala

1. Entrar como `admin` e demonstrar as seis telas.
2. Iniciar o motor, alterar a velocidade, observar temperatura e contador.
3. Consultar os comandos registrados em **Banco de Dados**.
4. Analisar **Gráficos** com os dados persistidos.
5. Cadastrar um usuário, desativá-lo ou alterar seu perfil.
6. Sair, executar tentativas de login inválidas e entrar novamente para observar **Monitoramento de Segurança**.
7. Entrar como `operador` e demonstrar a restrição de navegação.

## Teste automático parcial

```bat
python -m pip install pytest
python -m pytest -q
```

Os testes cobrem o banco de dados e o simulador, sem conexão com Streamlit ou AWS. Esta entrega não inclui teste automatizado de ponta a ponta das interfaces.
