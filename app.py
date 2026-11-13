"""Sistema Supervisório Industrial — Projeto Integrador SENAI / Etapa 04.

Rodar a partir desta pasta:
    streamlit run app.py
"""
import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from autenticacao import PERMISSOES, logout, tem_permissao  # noqa: E402
from banco_dados import inicializar_banco, procurar_usuario  # noqa: E402
from classe_gerenciador import GerenciadorLog  # noqa: E402
from telas import (tela_banco_dados, tela_cadastro_usuarios, tela_graficos,
                   tela_login, tela_monitoramento, tela_processo)  # noqa: E402


st.set_page_config(page_title="Supervisório Industrial | SENAI", page_icon="🏭",
                   layout="wide", initial_sidebar_state="expanded")

ARQUIVO_LOG = "sistema.log"
MODO_DEMO = os.getenv("APP_MODO_DEMO", "1") == "1"

log = GerenciadorLog(ARQUIVO_LOG)
try:
    inicializar_banco(modo_demo=MODO_DEMO)
except Exception as erro:
    st.error("Falha ao preparar o banco de dados. Verifique o DATABASE_URL e as tabelas.")
    st.code(f"{type(erro).__name__}: {erro}")
    st.stop()

for chave, valor in {"logado": False, "usuario": None, "perfil": None}.items():
    if chave not in st.session_state:
        st.session_state[chave] = valor

if not st.session_state.logado:
    tela_login(log, MODO_DEMO)
    st.stop()

# Revoga acesso se a conta foi desativada ou se o perfil mudou.
usuario_atual = procurar_usuario(st.session_state.usuario)
if not usuario_atual or not usuario_atual["ativo"]:
    st.session_state.logado = False
    st.session_state.usuario = None
    st.session_state.perfil = None
    st.warning("Sua conta está indisponível. Faça login novamente.")
    st.rerun()
if usuario_atual["perfil"] != st.session_state.perfil:
    st.session_state.perfil = usuario_atual["perfil"]

st.sidebar.title("🏭 Supervisório Industrial")
st.sidebar.caption("Projeto Integrador — SENAI")
st.sidebar.write(f"👤 **{st.session_state.usuario}**")
st.sidebar.write(f"Perfil: **{st.session_state.perfil}**")
if MODO_DEMO:
    st.sidebar.info("Ambiente de demonstração")
st.sidebar.divider()

opcoes = ["Processos", "Banco de Dados", "Gráficos", "Cadastro de Usuários", "Monitoramento de Segurança"]
opcoes = [tela for tela in opcoes if tem_permissao(st.session_state.perfil, tela)]
tela_atual = st.sidebar.radio("Navegação", opcoes)

st.sidebar.divider()
if st.sidebar.button("Sair", use_container_width=True):
    logout(log)

# Proteção também é aplicada na execução, não só no menu.
if not tem_permissao(st.session_state.perfil, tela_atual):
    log.registrar("WARNING", f"Tentativa de acesso não autorizado a {tela_atual}", st.session_state.usuario)
    st.error("Acesso não autorizado.")
    st.stop()

if tela_atual == "Processos":
    tela_processo(log)
elif tela_atual == "Banco de Dados":
    tela_banco_dados()
elif tela_atual == "Gráficos":
    tela_graficos()
elif tela_atual == "Cadastro de Usuários":
    tela_cadastro_usuarios(log)
elif tela_atual == "Monitoramento de Segurança":
    tela_monitoramento(log, ARQUIVO_LOG)

st.divider()
st.caption("SENAI | Sistema Supervisório Industrial — Etapa 04 — Projeto Integrador")
