"""Seis telas da Etapa 04, ampliando o exemplo 'telas.py' das aulas."""
from __future__ import annotations

import os
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from autenticacao import autenticar, criar_hash, tem_permissao
from banco_dados import (cadastrar_usuario, editar_usuario, ler_estado,
                         listar_eventos, listar_medicoes, listar_usuarios)
from classe_gerenciador import ler_logs_cloudwatch, ler_logs_local
from simulador import atualizar_simulacao, executar_comando


# ==============================================================
# TELA 01 — LOGIN
# ==============================================================
def tela_login(log, modo_demo: bool):
    st.title("🔐 Sistema Supervisório Industrial")
    st.caption("Projeto Integrador | Engenharia de Controle e Automação | SENAI")
    st.subheader("Autenticação")

    with st.form("form_login", clear_on_submit=False):
        usuario = st.text_input("Usuário", placeholder="Digite seu usuário")
        senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")
        entrar = st.form_submit_button("Entrar", use_container_width=True)

    if entrar:
        if autenticar(usuario, senha, log):
            st.rerun()
        st.error("Usuário ou senha inválidos, ou conta desativada.")

    if modo_demo:
        st.divider()
        st.info("**Ambiente demonstrativo:** as contas abaixo são apenas para testes locais. "
                "Não publique a aplicação com o modo de demonstração ativo.")
        st.code("admin / admin123\noperador / operador123\nengenheiro / engenheiro123", language="text")


# ==============================================================
# TELA 02 — PROCESSOS
# ==============================================================
def _desenho_esteira(estado: dict):
    ligado = bool(estado["motor_ligado"] and estado["velocidade"] > 0)
    ativo = "ligado" if ligado else "parado"
    velocidade = max(0.4, 2.5 - estado["velocidade"] / 1100) if ligado else 0
    sensor_cor = "#efb934" if estado["sensor_ativo"] else "#64748b"
    estado_texto = "EM OPERAÇÃO" if ligado else "PARADA"
    html = f"""
    <style>
      .planta {{font-family:Arial,sans-serif;background:#111e2a;color:#e5edf7;
               border-radius:14px;padding:22px;overflow:hidden;}}
      .planta .cab {{display:flex;justify-content:space-between;align-items:center;gap:12px;
                   font-size:14px;margin-bottom:20px}}
      .planta .status {{background:{'#126b52' if ligado else '#4b5563'};
                      padding:6px 12px;border-radius:16px;font-weight:700;font-size:12px;}}
      .linha {{position:relative;display:flex;align-items:center;height:120px;}}
      .motor {{width:82px;z-index:2;background:#0e74ae;border:2px solid #6ac9f7;
               border-radius:12px;padding:16px 4px;text-align:center;font-weight:700;font-size:12px;}}
      .esteira {{flex:1;height:65px;position:relative;overflow:hidden;
                border:5px solid #8494a7;border-radius:8px;
                background:repeating-linear-gradient(90deg,#283f54 0px,#283f54 27px,#34546b 27px,#34546b 34px);}}
      .esteira.ligado:after {{content:'';position:absolute;inset:0;background:repeating-linear-gradient(90deg,
                   transparent 0px,transparent 32px,#b5d3e22b 32px,#b5d3e22b 42px);
                   animation:mov {velocidade:.2f}s linear infinite;}}
      .caixa {{position:absolute;z-index:1;left:38%;top:7px;width:43px;height:43px;
               border:3px solid #dfaf68;background:#b57d3b;border-radius:4px;
               {'animation:peca 6s linear infinite;' if ligado else ''}}}
      .sensor {{width:60px;text-align:center;z-index:2;font-size:12px;}}
      .sensor .ponto {{width:17px;height:17px;border-radius:100%;background:{sensor_cor};margin:8px auto;
                       box-shadow:0 0 12px {sensor_cor};}}
      .rodape {{display:flex;flex-wrap:wrap;gap:12px;margin-top:12px;font-size:12px;color:#c1d3e1;}}
      @keyframes mov {{from {{transform:translateX(0)}} to {{transform:translateX(-42px)}}}}
      @keyframes peca {{0% {{left:-50px}} 100% {{left:calc(100% + 5px)}}}}
    </style>
    <div class="planta" aria-label="Representação ilustrativa da esteira e do motor">
      <div class="cab"><strong>CÉLULA DE TRANSPORTE — DEMONSTRAÇÃO</strong>
        <span class="status">{estado_texto}</span></div>
      <div class="linha">
        <div class="motor">⚙<div>MOTOR 01</div></div>
        <div class="esteira {ativo}"><div class="caixa"></div></div>
        <div class="sensor">SENSOR 01<div class="ponto"></div></div>
      </div>
      <div class="rodape"><span>Motor: {'LIGADO' if estado['motor_ligado'] else 'DESLIGADO'}</span>
      <span>Velocidade: {estado['velocidade']} RPM</span>
      <span>Peças: {estado['pecas_produzidas']}</span></div>
    </div>
    """
    st.html(html)


@st.fragment(run_every=3)
def monitorar_processo():
    """Atualiza as informações simuladas sem redesenhar toda a aplicação."""
    estado = atualizar_simulacao()
    a, b, c, d = st.columns(4)
    a.metric("Temperatura", f"{estado['temperatura']:.1f} °C")
    b.metric("Velocidade", f"{estado['velocidade']} RPM")
    c.metric("Peças produzidas", estado["pecas_produzidas"])
    d.metric("Sensor 01", "ACIONADO" if estado["sensor_ativo"] else "LIVRE")
    _desenho_esteira(estado)
    if estado["temperatura"] >= 65:
        st.error("🚨 Temperatura acima do limite demonstrativo de 65 °C.")
    elif not estado["motor_ligado"]:
        st.info("Motor desligado. A esteira está parada.")
    else:
        st.success("Processo operando no modo de demonstração.")

    dados = pd.DataFrame(listar_medicoes(30))
    if not dados.empty:
        st.subheader("Histórico recente de temperatura")
        st.line_chart(dados, x="Data/Hora", y="Temperatura (°C)")


def tela_processo(log):
    st.title("⚙️ Controle do Processo")
    st.caption("Simulação local de uma célula de transporte de peças | Atualização automática a cada 3 segundos")
    st.warning("**Modo simulado:** motor, temperatura e sensor não estão ligados ao CLP. "
               "A integração OPC UA será acrescentada na Etapa 06, após configurar os endereços das variáveis.")
    atual = ler_estado()
    st.subheader("Motor 01 — comandos de operação")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🟢 Ligar motor", use_container_width=True, disabled=atual["motor_ligado"]):
            ok, mensagem = executar_comando("ligar", st.session_state.usuario)
            log.registrar("INFO" if ok else "WARNING", mensagem, st.session_state.usuario)
            st.rerun()
    with c2:
        if st.button("🔴 Desligar motor", use_container_width=True, disabled=not atual["motor_ligado"]):
            ok, mensagem = executar_comando("desligar", st.session_state.usuario)
            log.registrar("INFO" if ok else "WARNING", mensagem, st.session_state.usuario)
            st.rerun()
    with c3:
        if st.button("↺ Zerar contador", use_container_width=True):
            ok, mensagem = executar_comando("zerar", st.session_state.usuario)
            log.registrar("INFO" if ok else "WARNING", mensagem, st.session_state.usuario)
            st.rerun()

    with st.form("form_velocidade"):
        velocidade = st.slider("Velocidade do Motor (RPM)", 0, 1800,
                               value=int(atual["velocidade"]), step=100)
        aplicar = st.form_submit_button("Aplicar velocidade")
    if aplicar:
        ok, mensagem = executar_comando("velocidade", st.session_state.usuario, velocidade)
        log.registrar("INFO" if ok else "WARNING", mensagem, st.session_state.usuario)
        (st.success if ok else st.warning)(mensagem)
    st.divider()
    st.subheader("Monitoramento do processo")
    monitorar_processo()


# ==============================================================
# TELA 03 — BANCO DE DADOS
# ==============================================================
def tela_banco_dados():
    st.title("🗃️ Acesso ao Banco de Dados")
    st.caption("Eventos operacionais armazenados no banco de dados configurado")
    registros = pd.DataFrame(listar_eventos())
    if registros.empty:
        st.info("Nenhum evento registrado. Execute comandos na tela de Processos para gerar registros.")
        return

    registro_min, registro_max = registros["Data/Hora"].min().date(), registros["Data/Hora"].max().date()
    col1, col2 = st.columns(2)
    with col1:
        periodo = st.date_input("Período", value=(registro_min, registro_max),
                                min_value=registro_min, max_value=registro_max)
    with col2:
        equipamento = st.selectbox("Equipamento", ["Todos"] + sorted(registros["Equipamento"].unique().tolist()))
    f1, f2 = st.columns(2)
    with f1:
        evento = st.selectbox("Tipo de evento", ["Todos"] + sorted(registros["Evento"].unique().tolist()))
    with f2:
        usuario = st.selectbox("Usuário", ["Todos"] + sorted(registros["Usuário"].unique().tolist()))

    if isinstance(periodo, (list, tuple)) and len(periodo) == 2:
        inicio, fim = periodo
        registros = registros[registros["Data/Hora"].dt.date.between(inicio, fim)]
    if equipamento != "Todos":
        registros = registros[registros["Equipamento"] == equipamento]
    if evento != "Todos":
        registros = registros[registros["Evento"] == evento]
    if usuario != "Todos":
        registros = registros[registros["Usuário"] == usuario]

    st.metric("Eventos encontrados", len(registros))
    st.dataframe(registros, use_container_width=True, hide_index=True)
    st.download_button("Baixar CSV dos eventos", data=registros.to_csv(index=False).encode("utf-8-sig"),
                       file_name="eventos_processo.csv", mime="text/csv")


# ==============================================================
# TELA 04 — GRÁFICOS
# ==============================================================
def tela_graficos():
    st.title("📈 Gráficos e Indicadores")
    st.caption("Análise dos dados históricos de operação")
    medidas = pd.DataFrame(listar_medicoes())
    eventos = pd.DataFrame(listar_eventos())
    if medidas.empty:
        st.info("Ainda não há medições. Abra a tela de Processos para iniciar a aquisição demonstrativa.")
        return

    st.subheader("Indicadores")
    c1, c2, c3 = st.columns(3)
    c1.metric("Medições registradas", len(medidas))
    c2.metric("Temperatura média", f"{medidas['Temperatura (°C)'].mean():.1f} °C")
    c3.metric("Última contagem de peças", int(medidas["Peças produzidas"].iloc[-1]))

    st.subheader("Evolução do processo")
    metrica = st.selectbox("Selecione a variável", ["Temperatura (°C)", "Velocidade (RPM)", "Peças produzidas"])
    st.line_chart(medidas, x="Data/Hora", y=metrica)

    st.subheader("Eventos registrados por tipo")
    if eventos.empty:
        st.info("Ainda não há eventos operacionais.")
    else:
        contagem = eventos.groupby("Evento").size().reset_index(name="Quantidade")
        st.bar_chart(contagem, x="Evento", y="Quantidade")
    st.caption("Os indicadores usam registros históricos reais do banco de dados. "
               "A origem das medições nesta versão é simulada.")


# ==============================================================
# TELA 05 — CADASTRO DE USUÁRIOS
# ==============================================================
def tela_cadastro_usuarios(log):
    st.title("👥 Cadastro de Usuários")
    if not tem_permissao(st.session_state.perfil, "Cadastro de Usuários"):
        st.error("Acesso não autorizado.")
        log.registrar("WARNING", "Tentativa de acesso não autorizado ao cadastro", st.session_state.usuario)
        st.stop()

    st.subheader("Novo usuário")
    with st.form("form_cadastrar", clear_on_submit=True):
        nome = st.text_input("Nome de usuário", max_chars=60)
        senha = st.text_input("Senha inicial", type="password")
        perfil = st.selectbox("Perfil", ["operador", "engenheiro", "admin"])
        cadastrar = st.form_submit_button("Cadastrar")
    if cadastrar:
        if len(senha) < 8:
            st.error("A senha deve ter pelo menos 8 caracteres.")
        else:
            ok, msg = cadastrar_usuario(nome, criar_hash(senha), perfil)
            (st.success if ok else st.warning)(msg)
            if ok:
                log.registrar("INFO", f"Usuário {nome.strip().lower()} cadastrado com perfil {perfil}", st.session_state.usuario)
                st.rerun()

    st.divider()
    st.subheader("Usuários cadastrados")
    lista = pd.DataFrame(listar_usuarios())
    st.dataframe(lista, use_container_width=True, hide_index=True)
    if lista.empty:
        return

    st.subheader("Editar usuário")
    selecao = st.selectbox("Selecionar usuário", lista["Usuário"].tolist())
    atual = lista.loc[lista["Usuário"] == selecao].iloc[0]
    with st.form("form_editar_usuario"):
        novo_perfil = st.selectbox("Perfil de acesso", ["admin", "operador", "engenheiro"],
                                   index=["admin", "operador", "engenheiro"].index(atual["Perfil"]))
        ativo = st.checkbox("Usuário ativo", value=bool(atual["Ativo"]))
        nova_senha = st.text_input("Nova senha (deixe em branco para manter)", type="password")
        salvar = st.form_submit_button("Salvar alterações")
    if salvar:
        if nova_senha and len(nova_senha) < 8:
            st.error("A nova senha deve conter pelo menos 8 caracteres.")
        else:
            hash_senha = criar_hash(nova_senha) if nova_senha else None
            ok, msg = editar_usuario(selecao, novo_perfil, ativo, hash_senha, st.session_state.usuario)
            (st.success if ok else st.warning)(msg)
            if ok:
                log.registrar("INFO", f"Cadastro de {selecao} atualizado", st.session_state.usuario)
                st.rerun()


# ==============================================================
# TELA 06 — MONITORAMENTO DE SEGURANÇA
# ==============================================================
def tela_monitoramento(log, arquivo):
    st.title("🛡️ Monitoramento de Segurança")
    if not tem_permissao(st.session_state.perfil, "Monitoramento de Segurança"):
        st.error("Acesso não autorizado.")
        log.registrar("WARNING", "Tentativa de acesso não autorizado ao monitoramento", st.session_state.usuario)
        st.stop()

    fontes = ["Arquivo de logs local"]
    if os.getenv("CLOUDWATCH_ATIVO", "0") == "1":
        fontes.append("AWS CloudWatch")
    fonte = st.selectbox("Origem dos logs", fontes)
    try:
        logs = ler_logs_cloudwatch() if fonte == "AWS CloudWatch" else ler_logs_local(arquivo)
    except Exception as erro:
        st.error(f"Não foi possível consultar o CloudWatch: {type(erro).__name__}. Confira as credenciais e permissões AWS.")
        return

    if logs.empty:
        st.info("Nenhum registro de segurança encontrado.")
        return
    logs["data"] = pd.to_datetime(logs["data"], errors="coerce")
    logs = logs.dropna(subset=["data"])
    if logs.empty:
        st.warning("O arquivo de logs não possui datas válidas para análise.")
        return

    st.subheader("Eventos por severidade")
    indicadores = ["INFO", "WARNING", "ERROR", "CRITICAL"]
    cols = st.columns(5)
    cols[0].metric("Total", len(logs))
    for i, tipo in enumerate(indicadores, 1):
        cols[i].metric(tipo, int((logs["nivel"] == tipo).sum()))

    st.divider()
    minutos = st.number_input("Período de análise (minutos)", min_value=1, max_value=10080, value=60, step=5)
    desde = datetime.now() - timedelta(minutes=int(minutos))
    invalidas = logs[
        (logs["data"] >= pd.Timestamp(desde)) &
        logs["mensagem"].astype(str).str.contains("Tentativa de login inválida", case=False, regex=False, na=False)
    ]
    qtd = len(invalidas)
    st.metric("Tentativas inválidas no período", qtd)
    if qtd >= 3:
        st.error("🚨 ALERTA: três ou mais tentativas de login inválidas foram identificadas no período.")
    elif qtd > 0:
        st.warning("Atenção: há tentativas inválidas recentes.")
    else:
        st.success("Nenhuma tentativa inválida foi identificada no período.")
    st.caption("Critério didático: três tentativas inválidas no período. A análise não prova a ocorrência de um ataque.")

    contagem = logs["nivel"].value_counts().rename_axis("Nível").reset_index(name="Quantidade")
    st.bar_chart(contagem, x="Nível", y="Quantidade")

    nivel = st.selectbox("Filtro por nível", ["Todos"] + indicadores)
    exibicao = logs if nivel == "Todos" else logs[logs["nivel"] == nivel]
    st.subheader("Eventos registrados")
    st.dataframe(exibicao.sort_values("data", ascending=False), use_container_width=True, hide_index=True)
