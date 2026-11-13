"""Autenticação inspirada no arquivo de aula, agora com persistência no banco."""
import bcrypt
import streamlit as st
from banco_dados import procurar_usuario


def criar_hash(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def autenticar(usuario: str, senha: str, log) -> bool:
    nome = usuario.strip().lower()
    dados = procurar_usuario(nome) if nome else None
    valido = bool(dados and dados["ativo"] and verificar_senha(senha, dados["senha_hash"]))
    if not valido:
        log.registrar("WARNING", "Tentativa de login inválida", usuario=nome or "(vazio)")
        return False
    st.session_state.logado = True
    st.session_state.usuario = nome
    st.session_state.perfil = dados["perfil"]
    log.registrar("INFO", "Login realizado", usuario=nome)
    return True


def logout(log):
    log.registrar("INFO", "Logout realizado", usuario=st.session_state.get("usuario") or "(desconhecido)")
    st.session_state.logado = False
    st.session_state.usuario = None
    st.session_state.perfil = None
    st.rerun()


PERMISSOES = {
    "admin": {"Processos", "Banco de Dados", "Gráficos", "Cadastro de Usuários", "Monitoramento de Segurança"},
    "operador": {"Processos", "Gráficos"},
    "engenheiro": {"Processos", "Banco de Dados", "Gráficos", "Monitoramento de Segurança"},
}


def tem_permissao(perfil: str, tela: str) -> bool:
    return tela in PERMISSOES.get(perfil, set())
