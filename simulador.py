"""Processo didático: motor, esteira e sensor simulados.

NÃO é a comunicação OPC UA. Essa conexão será implementada na Etapa 06,
após identificar os NodeIds do Open Industry Project da turma.
"""
import random
from datetime import datetime

from banco_dados import EstadoProcesso, Medicao, abrir_sessao, registrar_evento, ler_estado


def executar_comando(comando: str, usuario: str, velocidade: int | None = None) -> tuple[bool, str]:
    with abrir_sessao() as db:
        obj = db.get(EstadoProcesso, 1)
        if obj is None:
            return False, "O estado do processo não foi inicializado."

        if comando == "ligar":
            if obj.motor_ligado:
                return False, "O motor já está ligado."
            obj.motor_ligado, obj.velocidade = True, 600
            evento, detalhes = "Motor ligado", "Partida com velocidade inicial de 600 RPM"
        elif comando == "desligar":
            if not obj.motor_ligado:
                return False, "O motor já está desligado."
            obj.motor_ligado, obj.velocidade, obj.sensor_ativo = False, 0, False
            evento, detalhes = "Motor desligado", "Parada solicitada pela interface"
        elif comando == "velocidade":
            if not obj.motor_ligado:
                registrar_evento("Motor 01", "Comando recusado", usuario, "WARNING",
                                 "Tentativa de alterar velocidade com motor desligado", db=db)
                db.commit()
                return False, "O motor está desligado. Ligue o motor antes de ajustar a velocidade."
            if velocidade is None or not isinstance(velocidade, int) or not 0 <= velocidade <= 1800:
                return False, "A velocidade deve estar entre 0 e 1800 RPM."
            obj.velocidade = velocidade
            evento, detalhes = "Velocidade alterada", f"Nova velocidade: {velocidade} RPM"
        elif comando == "zerar":
            obj.pecas_produzidas = 0
            evento, detalhes = "Contador zerado", "Zeragem autorizada pela interface"
        else:
            return False, "Comando desconhecido."

        registrar_evento("Motor 01" if comando != "zerar" else "Esteira 01", evento, usuario,
                         detalhes=detalhes, db=db)
        db.commit()
        return True, detalhes


def atualizar_simulacao(intervalo_segundos: int = 3) -> dict:
    """Gera no máximo uma leitura por intervalo, compartilhada pelo banco local."""
    agora = datetime.now()
    with abrir_sessao() as db:
        obj = db.get(EstadoProcesso, 1)
        if obj is None:
            raise RuntimeError("Processo não inicializado.")
        if obj.ultimo_tick and (agora - obj.ultimo_tick).total_seconds() < intervalo_segundos:
            return ler_estado()

        obj.ultimo_tick = agora
        if obj.motor_ligado:
            alvo = 37.0 + 12.0 * obj.velocidade / 1800.0
            obj.temperatura = max(24.0, min(85.0, 0.65 * obj.temperatura + 0.35 * alvo + random.uniform(-0.8, 0.8)))
            obj.sensor_ativo = bool(obj.velocidade > 0 and random.random() < obj.velocidade / 3600.0)
            if obj.sensor_ativo:
                obj.pecas_produzidas += 1
        else:
            obj.sensor_ativo = False
            obj.temperatura = max(25.0, 0.85 * obj.temperatura + 0.15 * 26.0 + random.uniform(-0.2, 0.2))

        db.add(Medicao(temperatura=obj.temperatura, velocidade=obj.velocidade,
                       motor_ligado=obj.motor_ligado, sensor_ativo=obj.sensor_ativo,
                       pecas_produzidas=obj.pecas_produzidas, data_hora=agora))
        db.commit()
    return ler_estado()
