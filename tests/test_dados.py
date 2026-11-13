"""Testes de banco e processo que não dependem de AWS ou servidor Streamlit."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def preparar(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(tmp_path / "teste.db"))
    from banco_dados import obter_engine, inicializar_banco
    obter_engine.cache_clear()
    inicializar_banco(modo_demo=False)
    yield
    obter_engine().dispose()
    obter_engine.cache_clear()


def test_estado_inicial(preparar):
    from banco_dados import ler_estado, listar_usuarios
    estado = ler_estado()
    assert estado["motor_ligado"] is False
    assert estado["velocidade"] == 0
    assert listar_usuarios() == []


def test_motor_e_historico(preparar):
    from banco_dados import listar_eventos, listar_medicoes
    from simulador import executar_comando, atualizar_simulacao
    assert executar_comando("velocidade", "operador", 600)[0] is False
    assert executar_comando("ligar", "operador")[0] is True
    assert executar_comando("velocidade", "operador", 1200)[0] is True
    estado = atualizar_simulacao()
    assert estado["motor_ligado"] is True
    assert estado["velocidade"] == 1200
    assert len(listar_medicoes()) == 1
    assert len(listar_eventos()) >= 3
    assert executar_comando("desligar", "operador")[0] is True
    assert atualizar_simulacao()["motor_ligado"] is False


def test_crud_usuarios(preparar):
    from banco_dados import cadastrar_usuario, procurar_usuario, editar_usuario
    assert cadastrar_usuario("ana", "hash_exemplo", "engenheiro")[0] is True
    assert cadastrar_usuario("ana", "hash_exemplo", "engenheiro")[0] is False
    assert procurar_usuario("ana")["perfil"] == "engenheiro"
    assert editar_usuario("ana", "operador", False, None, "admin")[0] is True
    assert procurar_usuario("ana")["ativo"] is False


def test_ultimo_admin_nao_pode_ser_desativado(preparar):
    from banco_dados import cadastrar_usuario, editar_usuario
    assert cadastrar_usuario("chefe", "hash_exemplo", "admin")[0] is True
    ok, msg = editar_usuario("chefe", "operador", False, None, "outro_admin")
    assert not ok
    assert "administrador" in msg
