import json
import os
from datetime import datetime, timedelta

def extenso_mes(data_str):
    """Converte '16/02' para '16 de fevereiro'."""
    meses = {
        "01": "janeiro", "02": "fevereiro", "03": "março", "04": "abril",
        "05": "maio", "06": "junho", "07": "julho", "08": "agosto",
        "09": "setembro", "10": "outubro", "11": "novembro", "12": "dezembro"
    }
    try:
        dia, mes = data_str.split("/")
        nome_mes = meses.get(mes, "")
        return f"{int(dia)} de {nome_mes}"
    except:
        return data_str

def gerar_timestamp(data_str, hora_str, offset=0):
    """Gera timestamp Unix ajustado para fuso -3h (Brasília) com delay por curso."""
    try:
        data_completa = f"{data_str}/2026 {hora_str}"
        dt = datetime.strptime(data_completa, "%d/%m/%Y %H:%M")
        dt_ajustado = dt + timedelta(hours=3, seconds=offset)
        return int(dt_ajustado.timestamp())
    except:
        return 0

def calcular_data_especifica(data_str, dias_adicionais):
    """Calcula uma data futura (D+X) a partir de uma data base."""
    try:
        data_completa = f"{data_str}/2026"
        dt_inicio = datetime.strptime(data_completa, "%d/%m/%Y")
        dt_alvo = dt_inicio + timedelta(days=dias_adicionais)
        return dt_alvo.strftime("%d/%m")
    except:
        return data_str

def limpar_para_json(texto):
    """Remove caracteres que quebram a estrutura do arquivo JSON."""
    if not texto: return ""
    return str(texto).replace('"', '').replace('\n', ' ').replace('\r', '').strip()

def calcular_delay_retomada(total_cursos):
    """
    Retorna o delay em segundos por curso baseado no total de cursos do fluxo de RETOMADA.
    Tabela:
      até 20 cursos  → 120s (2 min)
      21 a 30 cursos →  60s (1 min)
      31 a 50 cursos →  45s
      51+ cursos     →  40s
    """
    if total_cursos <= 20:
        return 120
    elif total_cursos <= 30:
        return 60
    elif total_cursos <= 50:
        return 45
    else:
        return 40


def obter_template_whatsapp(conta, fluxo, tipo_evento="curso"):
    """
    Busca o template de WhatsApp pela conta e pelo fluxo.

    Para congressos, tenta primeiro chaves específicas que você pode cadastrar
    manualmente no TEMPLATES_WHATSAPP, por exemplo:
      - "Fluxo 1 Congresso"
      - "Congresso Fluxo 1"
      - "SC1 Congresso"

    Se nenhuma chave específica existir, usa o template normal como fallback.
    """
    templates_conta = TEMPLATES_WHATSAPP.get(conta, {})

    if tipo_evento == "congresso":
        chaves_congresso = [
            f"{fluxo} Congresso",
            f"Congresso {fluxo}",
            f"{fluxo} - Congresso",
            f"{fluxo}_Congresso",
        ]
        for chave in chaves_congresso:
            if chave in templates_conta:
                return templates_conta[chave]

    return templates_conta.get(fluxo)


def aplicar_linguagem_congresso(json_data):
    """Troca textos de curso/aula para congresso/palestra sem mexer em links e IDs."""

    def converter_texto(texto):
        if not isinstance(texto, str):
            return texto

        texto_lower = texto.lower()
        if (
            texto_lower.startswith("http")
            or "www." in texto_lower
            or "connectionid" in texto_lower
            or "wabaid" in texto_lower
            or "userid" in texto_lower
        ):
            return texto

        substituicoes = [
            ("Cursos", "Congressos"),
            ("cursos", "congressos"),
            ("CURSOS", "CONGRESSOS"),
            ("Curso", "Congresso"),
            ("curso", "congresso"),
            ("CURSO", "CONGRESSO"),
            ("Aulas", "Palestras"),
            ("aulas", "palestras"),
            ("AULAS", "PALESTRAS"),
            ("Aula", "Palestra"),
            ("aula", "palestra"),
            ("AULA", "PALESTRA"),
        ]
        for origem, destino in substituicoes:
            texto = texto.replace(origem, destino)

            texto = texto.replace("Acessar Palestras e Mat.", "Acessar Palestra/PDF")
            texto = texto.replace("Acessar palestras e mat.", "Acessar Palestra/PDF")
            texto = texto.replace("ACESSAR PALESTRAS E MAT.", "Acessar Palestra/PDF")

            return texto

    def percorrer(obj, chave_pai=""):
        if isinstance(obj, dict):
            for chave, valor in obj.items():
                chave_lower = str(chave).lower()
                if isinstance(valor, str):
                    # Evita alterar campos técnicos de integração.
                    if any(bloqueado in chave_lower for bloqueado in ["id", "link", "webhook", "url"]):
                        continue
                    obj[chave] = converter_texto(valor)
                else:
                    percorrer(valor, chave)
        elif isinstance(obj, list):
            for item in obj:
                percorrer(item, chave_pai)

    percorrer(json_data)
    return json_data


def aplicar_template_whatsapp(json_data, dados_template):
    if not dados_template:
        return json_data

    def percorrer(obj):
        if isinstance(obj, dict):
            if obj.get("type") == "send_template" or "templateDataJson" in obj:
                obj["templateId"] = dados_template["id"]

                if "template" in obj and isinstance(obj["template"], dict):
                    obj["template"]["name"] = dados_template["nome"]
                    obj["template"]["connectionId"] = dados_template["connectionId"]
                    obj["template"]["wabaId"] = dados_template["wabaId"]
                    obj["template"]["userId"] = dados_template["userId"]
                    obj["template"]["id"] = dados_template["id"]

                if "templateDataJson" in obj:
                    try:
                        template_json = json.loads(obj["templateDataJson"])
                        template_json["name"] = dados_template["nome"]
                        template_json["id"] = dados_template["id"]
                        template_json["connectionId"] = dados_template["connectionId"]
                        template_json["wabaId"] = dados_template["wabaId"]
                        template_json["userId"] = dados_template["userId"]
                        obj["templateDataJson"] = json.dumps(template_json, ensure_ascii=False)
                    except Exception:
                        pass

            for valor in obj.values():
                percorrer(valor)

        elif isinstance(obj, list):
            for item in obj:
                percorrer(item)

    percorrer(json_data)
    return json_data

TEMPLATES_WHATSAPP = {
    "Conta_1": {
        "Fluxo 1": {
            "nome": "m1_segunda_gratuito_curso_c1",
            "connectionId": "ouLDZiM3pEddrZuTGJVw",
            "wabaId": "551316877339100",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "2351281792011799"
        },
        "Fluxo 1 Congresso": {
            "nome": "m1_segunda_gratuito_congresso_c1",
            "connectionId": "ouLDZiM3pEddrZuTGJVw",
            "wabaId": "551316877339100",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "963935253260325"
        },
        "Fluxo 2": {
            "nome": "m1_terca_gratuito_curso_c1",
            "connectionId": "ouLDZiM3pEddrZuTGJVw",
            "wabaId": "551316877339100",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "1224032236224575"
        },
        "Fluxo 2 Congresso": {
            "nome": "m1_terca_gratuito_congresso_c1",
            "connectionId": "ouLDZiM3pEddrZuTGJVw",
            "wabaId": "551316877339100",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "2181188712698535"
        },       
        "Fluxo 7": {
            "nome": "m1_quarta_gratuito_curso_c1",
            "connectionId": "ouLDZiM3pEddrZuTGJVw",
            "wabaId": "551316877339100",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53" ,
            "id": "3877399019065544"
        }, 
        "Fluxo 7 Congresso": {
            "nome": "m1_quarta_gratuito_congresso_c1",
            "connectionId": "ouLDZiM3pEddrZuTGJVw",
            "wabaId": "551316877339100",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "1663317388284499"
        },
        "SC1": {
            "nome": "m1_terca_sc1_curso_c1",
            "connectionId": "ouLDZiM3pEddrZuTGJVw",
            "wabaId": "551316877339100",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "2204131727075346"
        },
        "SC1 Congresso": {
            "nome": "m1_terca_sc1_congresso_c1",
            "connectionId": "ouLDZiM3pEddrZuTGJVw",
            "wabaId": "551316877339100",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "2311199216071077"
        },
        "SC2":{
            "nome": "m1_quinta_sc2_curso_c1",
            "connectionId": "ouLDZiM3pEddrZuTGJVw",
            "wabaId": "551316877339100",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53" ,
            "id": "939470922406268"
        }, 
        "SC2 Congresso": {
            "nome": "m1_quinta_sc2_congresso_c1",
            "connectionId": "ouLDZiM3pEddrZuTGJVw",
            "wabaId": "551316877339100",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "1908162669901036"
        },
        "SC3": {
            "nome": "m1_quinta_sc3_curso_c1",
            "connectionId": "ouLDZiM3pEddrZuTGJVw" ,
            "wabaId": "551316877339100",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "1263805545421820"
        },
        "SC3 Congresso": {
            "nome": "m1_quinta_sc3_congresso_c1",
            "connectionId": "ouLDZiM3pEddrZuTGJVw",
            "wabaId": "551316877339100",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "1515771696739423"
        }
    },
    "Conta_2": {
        "Fluxo 1": {
            "nome": "m1_segunda_gratuito_curso_c2",
            "connectionId": "OXU0Zg19Qgu5G4HauCdC",
            "wabaId": "643489112180162",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "1543760574427026"
        },
        "Fluxo 1 Congresso": {
            "nome": "m1_segunda_gratuito_congresso_c2",
            "connectionId": "OXU0Zg19Qgu5G4HauCdC",
            "wabaId": "643489112180162",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "1984470522461741"
        },
        "Fluxo 2": {
            "nome": "m1_terca_gratuito_curso_c2",
            "connectionId": "OXU0Zg19Qgu5G4HauCdC",
            "wabaId": "643489112180162",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "4432723350280208"
        },
        "Fluxo 2 Congresso": {
            "nome": "m1_terca_gratuito_congresso_c2",
            "connectionId": "OXU0Zg19Qgu5G4HauCdC",
            "wabaId": "643489112180162",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "823186110287063"
        },
        "Fluxo 7": {
            "nome": "m1_quarta_gratuito_curso_c2",
            "connectionId": "OXU0Zg19Qgu5G4HauCdC",
            "wabaId": "643489112180162",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53" ,
            "id": "26688921900744732"
        },
        "Fluxo 7 Congresso": {
            "nome": "m1_quarta_gratuito_congresso_c2",
            "connectionId": "OXU0Zg19Qgu5G4HauCdC",
            "wabaId": "643489112180162",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "1876987939624672"
        },
        "SC1": {
            "nome": "m1_terca_sc1_curso_c2",
            "connectionId": "OXU0Zg19Qgu5G4HauCdC",
            "wabaId": "643489112180162",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "4404558556458070"
        }, 
        "SC1 Congresso": {
            "nome": "m1_terca_sc1_congresso_c2",
            "connectionId": "OXU0Zg19Qgu5G4HauCdC",
            "wabaId": "643489112180162",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "2117207822462821"
        },
        "SC2":{
            "nome": "m1_quinta_sc2_curso_c2",
            "connectionId": "OXU0Zg19Qgu5G4HauCdC",
            "wabaId": "643489112180162",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53" ,
            "id": "1561244302678164"
        }, 
        "SC2 Congresso": {
            "nome": "m1_quinta_sc2_congresso_c2",
            "connectionId": "OXU0Zg19Qgu5G4HauCdC",
            "wabaId": "643489112180162",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "2183233749095726"
        },
        "SC3": {
            "nome": "m1_quinta_sc3_curso_c2",
            "connectionId": "OXU0Zg19Qgu5G4HauCdC" ,
            "wabaId": "643489112180162",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "1351355953500204" 
        },
        "SC3 Congresso": {
            "nome": "m1_quinta_sc3_congresso_c2",
            "connectionId": "OXU0Zg19Qgu5G4HauCdC",
            "wabaId": "643489112180162",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "945328344776651"
        }
    },
    "Conta_3": {
            "Fluxo 1": {
            "nome": "m1_segunda_gratuito_curso_c3",
            "connectionId": "KeL8BkXcV3WWwW6j7MHc",
            "wabaId": "1488880795714059",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "2853631534991765"
        },
        "Fluxo 1 Congresso": {
            "nome": "m1_segunda_gratuito_congresso_c3",
            "connectionId": "KeL8BkXcV3WWwW6j7MHc",
            "wabaId": "1488880795714059",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "1920212902714412"
        },
        "Fluxo 2": {
            "nome": "m1_terca_gratuito_curso_c3",
            "connectionId": "KeL8BkXcV3WWwW6j7MHc",
            "wabaId": "1488880795714059",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "823556080800952"
        },
        "Fluxo 2 Congresso": {
            "nome": "m1_terca_gratuito_congresso_c3",
            "connectionId": "KeL8BkXcV3WWwW6j7MHc",
            "wabaId": "1488880795714059",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "1338801454803295"
        },
        "Fluxo 7": {
            "nome": "m1_quarta_gratuito_curso_c3",
            "connectionId": "KeL8BkXcV3WWwW6j7MHc",
            "wabaId": "1488880795714059",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53" ,
            "id": "1267302135598246"
        }, 
        "Fluxo 7 Congresso": {
            "nome": "m1_quarta_gratuito_congresso_c3",
            "connectionId": "KeL8BkXcV3WWwW6j7MHc",
            "wabaId": "1488880795714059",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "1267302135598246"
        },
        "SC1": {
            "nome": "m1_terca_sc1_curso_c3",
            "connectionId": "KeL8BkXcV3WWwW6j7MHc",
            "wabaId": "1488880795714059",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "1455864015527736"
        }, 
        "SC1 Congresso": {
            "nome": "m1_terca_sc1_congresso_c3",
            "connectionId": "KeL8BkXcV3WWwW6j7MHc",
            "wabaId": "1488880795714059",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "1647824836263779"
        },
        "SC2":{
            "nome": "m1_quinta_sc2_curso_c3",
            "connectionId": "KeL8BkXcV3WWwW6j7MHc",
            "wabaId": "1488880795714059",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53" ,
            "id": "3517092801775768"
        }, 
        "SC2 Congresso": {
            "nome": "m1_quinta_sc2_congresso_c3",
            "connectionId": "KeL8BkXcV3WWwW6j7MHc",
            "wabaId": "1488880795714059",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "1683629602827188"
        },
        "SC3": {
            "nome": "m1_quinta_sc3_congresso_c3",
            "connectionId": "KeL8BkXcV3WWwW6j7MHc" ,
            "wabaId": "1488880795714059",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "1494247202091960" 
        },
        "SC3 Congresso": {
            "nome": "m1_quinta_sc3_congresso_c3",
            "connectionId": "KeL8BkXcV3WWwW6j7MHc",
            "wabaId": "1488880795714059",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "890898067333698"
        }
    },
    "Conta_4": {
        "Fluxo 1": {
            "nome": "m1_segunda_gratuito_curso_c4",
            "connectionId": "tOgoXMt8I9a21Pj1BiJx",
            "wabaId": "4237462246578095",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "2853631534991765"
        },
        "Fluxo 1 Congresso": {
            "nome": "m1_segunda_gratuito_congresso_c4",
            "connectionId": "tOgoXMt8I9a21Pj1BiJx",
            "wabaId": "4237462246578095",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "1503338854734344"
        },
        "Fluxo 2": {
            "nome": "m1_terca_gratuito_curso_c4",
            "connectionId": "tOgoXMt8I9a21Pj1BiJx",
            "wabaId": "4237462246578095",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "1671339140859416"
        },
        "Fluxo 2 Congresso": {
            "nome": "m1_terca_gratuito_congresso_c4",
            "connectionId": "tOgoXMt8I9a21Pj1BiJx",
            "wabaId": "4237462246578095",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "1271267434584841"
        },
        "Fluxo 7": {
            "nome": "m1_quarta_gratuito_curso_c4",
            "connectionId": "tOgoXMt8I9a21Pj1BiJx",
            "wabaId": "4237462246578095",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53" ,
            "id": "3096299253905186"
        }, 
        "Fluxo 7 Congresso": {
            "nome": "m1_quarta_gratuito_congresso_c4",
            "connectionId": "tOgoXMt8I9a21Pj1BiJx",
            "wabaId": "4237462246578095",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "1636155757658988"
        },
        "SC1": {
            "nome": "m1_terca_sc1_curso_c4",
            "connectionId": "tOgoXMt8I9a21Pj1BiJx",
            "wabaId": "4237462246578095",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "1956234691946131"
        }, 
        "SC1 Congresso": {
            "nome": "m1_terca_sc1_congresso_c4",
            "connectionId": "tOgoXMt8I9a21Pj1BiJx",
            "wabaId": "4237462246578095",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "1295130972804753"
        },
        "SC2":{
            "nome": "m1_quinta_sc2_curso_c4",
            "connectionId": "tOgoXMt8I9a21Pj1BiJx",
            "wabaId": "4237462246578095",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53" ,
            "id": "1265321088710437"
        }, 
        "SC2 Congresso": {
            "nome": "m1_quinta_sc2_congresso_c4",
            "connectionId": "tOgoXMt8I9a21Pj1BiJx",
            "wabaId": "4237462246578095",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "1355314149773137"
        },
        "SC3": {
            "nome": "m1_quinta_sc3_curso_c4",
            "connectionId": "tOgoXMt8I9a21Pj1BiJx" ,
            "wabaId": "4237462246578095",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "828526586972488"
        },
        "SC3 Congresso": {
            "nome": "m1_quinta_sc3_congresso_c4",
            "connectionId": "tOgoXMt8I9a21Pj1BiJx",
            "wabaId": "4237462246578095",
            "userId": "3jNt3SinWzW08N7iqGhu473b7M53",
            "id": "1459372082386644"
        }
    },
}



def processar_curso(
    linha,
    data_ancora,
    path_template,
    index_curso,
    tipo_fluxo="SC1",
    data_disparo=None,
    ano_retomada=None,
    total_cursos=None,
    dados_template_whatsapp=None,
    usar_delay_retomada=False,
    modo_congresso=False,
):
    # --- 1. LÓGICA DE DEFINIÇÃO DA DATA DE DISPARO ---
    if data_disparo:
        data_envio_base = data_disparo
    else:
        data_referencia = data_ancora
        if tipo_fluxo == "SC1":
            data_envio_base = calcular_data_especifica(data_referencia, 8)
        elif tipo_fluxo == "SC2":
            data_envio_base = calcular_data_especifica(data_referencia, 17)
        elif tipo_fluxo == "F2.1":
            data_envio_base = calcular_data_especifica(data_referencia, 1)
        elif tipo_fluxo == "SC0":
            data_envio_base = calcular_data_especifica(data_referencia, 3)
        elif tipo_fluxo in ["SC3", "RETOMADA"] or "Retroativo" in str(tipo_fluxo):
            data_envio_base = calcular_data_especifica(data_referencia, 24)
        elif tipo_fluxo == "Docs":
            data_envio_base = calcular_data_especifica(data_referencia, 31)
        else:
            data_envio_base = calcular_data_especifica(data_referencia, 1)

    data_envio_ds = calcular_data_especifica(data_envio_base, 1)

    # --- 2. MAPEAMENTO GERAL DA PLANILHA ---
    nome_curso       = limpar_para_json(linha[0])   # A  - Nome do curso
    webhook_link     = linha[4]                     # E  - WEBHOOK Unnichat
    cd_curso_abert   = limpar_para_json(linha[9])   # J  - Código curso + abertura
    tag_foi_plan     = limpar_para_json(linha[11])  # L  - Tag "Foi pra Planilha"
    tag_insc_curso   = limpar_para_json(linha[12])  # M  - Tag "Inscrição"
    tag_cancel       = limpar_para_json(linha[13])  # N  - Tag "Cancelar Inscrição"
    tag_atrasados_f1 = limpar_para_json(linha[14])  # O  - Tag "Iniciar F."
    tag_inicio_f2    = limpar_para_json(linha[15])  # P  - Tag "Fluxo 2"
    tag_inicio_f3    = limpar_para_json(linha[16])  # Q  - Tag "Fluxo 3"
    tag_inicio_f4    = limpar_para_json(linha[17])  # R  - Tag "Fluxo 4"
    tag_inicio_f5    = limpar_para_json(linha[18])  # S  - Tag "Fluxo 5"
    tag_inicio_f6    = limpar_para_json(linha[19])  # T  - Tag "Fluxo 6"
    tag_inicio_f7    = limpar_para_json(linha[20])  # U  - Tag "Fluxo 7"
    tag_inicio_f8    = limpar_para_json(linha[21])  # V  - Tag "Fluxo 8"
    tag_presente_f8  = limpar_para_json(linha[22])  # W  - Tag "Presente"
    tag_cert         = limpar_para_json(linha[23])  # X  - Tag Certificado Digital
    tag_insc_geral   = limpar_para_json(linha[24])  # Y  - Tag "Inscritos DD/MM"
    vol_pdf_2        = limpar_para_json(linha[27])  # AB - Volume 2 do PDF
    titulo_pdf       = limpar_para_json(linha[28])  # AC - Título do PDF volume 3
    gatilho_fx       = limpar_para_json(linha[31])  # AF - Gatilho de início do fluxo
    bonus_cursos     = limpar_para_json(linha[32])  # AG - Bônus
    link_hotmart_raw = linha[33]                    # AH - Link Hotmart com XXXXXXXXXXXXXXXXX
    cd_cert          = limpar_para_json(linha[34])  # AI - Código certificado
    cd_aulas         = limpar_para_json(linha[35])  # AJ - Código aulas
    cd_pdf           = limpar_para_json(linha[36])  # AK - Código PDF

    # COLUNAS SC (usadas apenas no modo Retroativo)
    if tipo_fluxo == "SC1":
        tag_clicou_retro   = limpar_para_json(linha[38]) if len(linha) > 38 else ""  # AM
        tag_cancelar_retro = limpar_para_json(linha[39]) if len(linha) > 39 else ""  # AN
    elif tipo_fluxo == "SC2":
        tag_clicou_retro   = limpar_para_json(linha[40]) if len(linha) > 40 else ""  # AO
        tag_cancelar_retro = limpar_para_json(linha[41]) if len(linha) > 41 else ""  # AP
    else:  # SC0, SC3 e outros
        tag_clicou_retro   = limpar_para_json(linha[42]) if len(linha) > 42 else ""  # AQ
        tag_cancelar_retro = limpar_para_json(linha[43]) if len(linha) > 43 else ""  # AR

    # COLUNAS RETOMADA: AS (44) = Clicou, AT (45) = Cancelar
    tag_clicou_ret_plan   = limpar_para_json(linha[44]) if len(linha) > 44 else ""  # AS
    tag_cancelar_ret_plan = limpar_para_json(linha[45]) if len(linha) > 45 else ""  # AT

    # IMAGEM CERTIFICADO: AV (47)
    link_cert_img = limpar_para_json(linha[47]) if len(linha) > 47 else ""  # AV

    # LINK PDF VOLUME 3: AW (48)
    link_pdf = limpar_para_json(linha[48]) if len(linha) > 48 else ""  # AW

    # --- 3. LÓGICA DE TAGS DINÂMICAS ---
    tag_fluxo_nome = tipo_fluxo  # SC0 → "SC0", SC3 → "SC3", cada um com seu nome

    if "Retroativo" in str(tipo_fluxo):
        tag_clicou_sc_final   = tag_clicou_retro
        tag_cancelar_sc_final = tag_cancelar_retro
    else:
        tag_clicou_sc_final   = f"Clicou - {tag_fluxo_nome} - {data_ancora} - {nome_curso}"
        tag_cancelar_sc_final = f"Cancelar Envios - {tag_fluxo_nome} - {data_ancora} - {nome_curso}"

    dias_para_voltar = 1 if (tipo_fluxo in ["SC1", "F2.1"]) else 3
    segunda_referencia_tags = calcular_data_especifica(data_envio_base, -dias_para_voltar)

    tag_sem1 = f"Inscritos {segunda_referencia_tags}"
    tag_sem2 = f"Inscritos {calcular_data_especifica(segunda_referencia_tags, 7)}"
    tag_sem3 = f"Inscritos {calcular_data_especifica(segunda_referencia_tags, 14)}"

    # --- 4. DELAY ---
    # Fluxos normais SEMPRE usam 2 minutos por curso.
    # A regra dinâmica (+20 = 1min, +30 = 45s, +50 = 40s) fica isolada
    # somente para o fluxo RETOMADA, quando o app.py autorizar com usar_delay_retomada=True.
    if usar_delay_retomada:
        if total_cursos is not None and total_cursos > 0:
            delay_por_curso = calcular_delay_retomada(total_cursos)
        else:
            delay_por_curso = 120
    else:
        delay_por_curso = 120

    offset_atual = index_curso * delay_por_curso
    data_extenso = extenso_mes(data_ancora)
    data_prazo_cert = calcular_data_especifica(data_ancora, 2)
    data_aulas_ate  = calcular_data_especifica(data_ancora, 8)

    def fix_link_padrao(utm):
        return link_hotmart_raw.replace("XXXXXXXXXXXXXXXXX", utm) if link_hotmart_raw else ""

    def fix_link_sc(sufixo):
        if not link_hotmart_raw: return ""
        link_limpo = link_hotmart_raw.replace("||", "").replace("|", "")
        return link_limpo.replace("XXXXXXXXXXXXXXXXX", f"{tipo_fluxo}_T1|{sufixo}|") + "||"

    def fix_link_retomada(sufixo):
        if not link_hotmart_raw: return ""
        ano = ano_retomada if ano_retomada else "2023"
        return link_hotmart_raw.replace("XXXXXXXXXXXXXXXXX||", f"RETOMADA{ano}_T1|{sufixo}|")

    with open(path_template, 'r', encoding='utf-8') as f:
        conteudo = f.read()

    # Quando SC0, renomeia o fluxo no template (que é o mesmo do SC3)
    if tipo_fluxo == "SC0":
        conteudo = conteudo.replace("SC3 ", "SC0 ")

    substituicoes = {
        "{{NOME_CURSO}}":                   nome_curso,
        "{{GATILHO_INICIO_FX}}":            gatilho_fx,
        "{{TAG_FOI_PLANILHA}}":             tag_foi_plan,
        "{{TAG_INSC_CURSO}}":               tag_insc_curso,
        "{{TAG_INSC_GERAL}}":               tag_insc_geral,
        "{{TAG_CANCEL_CURSO}}":             tag_cancel,
        "{{TAG_CERT_CURSO}}":               tag_cert,
        "{{CD_CURSO_CERT}}":                cd_cert,
        "{{CD_CURSO_AULAS}}":               cd_aulas,
        "{{CD_CURSO_PDF}}":                 cd_pdf,
        "{{CD_CURSO_ABERT}}":               cd_curso_abert,
        "{{VOL_PDF_2}}":                    vol_pdf_2,
        "{{BONUS_CURSOS}}":                 bonus_cursos,
        "{{LINK_WEBHOOK_PLANILHA}}":        webhook_link,
        "{{DT_INICIO_CURSO_EXT}}":          data_extenso,
        "{{DT_INICIO_CURSO_FORMAT}}":       data_ancora,
        "{{DT_AULAS_DISP_CURSO_FORMAT}}":   data_aulas_ate,
        "{{DT_FIM_CERT_FORMAT}}":           data_prazo_cert,
        "{{LINK_CERTIFICADO_IMG}}":         link_cert_img,
        "{{TAG_INIC_F_CURSO}}":             tag_atrasados_f1,
        "{{TAG_INIC_F2_CURSO}}":            tag_inicio_f2,
        "{{TAG_INIC_F3_CURSO}}":            tag_inicio_f3,
        "{{TAG_INIC_F4_CURSO}}":            tag_inicio_f4,
        "{{TAG_INIC_F5_CURSO}}":            tag_inicio_f5,
        "{{TAG_INIC_F6_CURSO}}":            tag_inicio_f6,
        "{{TAG_INIC_F7_CURSO}}":            tag_inicio_f7,
        "{{TAG_INIC_F8_CURSO}}":            tag_inicio_f8,
        "{{TAG_PRESENTE_F8_CURSO}}":        tag_presente_f8,
        "{{LINK_PDF_VOL_3}}":               link_pdf,
        "{{VOL_PDF_3}}":                    titulo_pdf,
        # Links Hotmart — fluxos padrão
        "{{LINK_HOTMART_F1_M1_CURSO}}":     fix_link_padrao("apis15c"),
        "{{LINK_HOTMART_F4_M1_CURSO}}":     fix_link_padrao("apiq8c"),
        "{{LINK_HOTMART_F5_M1_CURSO}}":     fix_link_padrao("apiq12c"),
        "{{LINK_HOTMART_F6_M1_CURSO}}":     fix_link_padrao("apiq18c"),
        "{{LINK_HOTMART_F7_M1_CURSO}}":     fix_link_padrao("apiq20c"),
        "{{LINK_HOTMART_F7_M2_CURSO}}":     fix_link_padrao("apiq21c"),
        "{{LINK_HOTMART_F7_M3_CURSO}}":     fix_link_padrao("apiq20t"),
        "{{LINK_HOTMART_F7_M4_CURSO}}":     fix_link_padrao("apiq21t"),
        "{{LINK_HOTMART_F8_M1_CURSO}}":     fix_link_padrao("apiq15c"),
        # Timestamps — Fluxo 1
        "{{DT_VARIA_11_F1}}":               str(gerar_timestamp(data_ancora, "11:00", offset_atual)),
        "{{DT_VARIA_14_F1}}":               str(gerar_timestamp(data_ancora, "14:00", offset_atual)),
        "{{DT_VARIA_15_F1}}":               str(gerar_timestamp(data_ancora, "15:00", offset_atual)),
        "{{DT_VARIA_19_F1}}":               str(gerar_timestamp(data_ancora, "19:00", offset_atual)),
        "{{DT_VARIA_20_F1}}":               str(gerar_timestamp(data_ancora, "20:00", offset_atual)),
        "{{DT_VARIA_21_F7}}":               str(gerar_timestamp(data_prazo_cert, "21:00", offset_atual)),
        "{{DT_VARIA_22_F7}}":               str(gerar_timestamp(data_prazo_cert, "22:00", offset_atual)),
        "{{DT_ANTES_INIC_CURSO}}":          str(gerar_timestamp(data_ancora, "08:00", 0)),
        "{{DT_ANTES_FIM_CERT}}":            str(gerar_timestamp(data_prazo_cert, "10:00", 0)),
        # Tags SC
        "{{TAG_CLICOU_SC}}":                tag_clicou_sc_final,
        "{TAG_CLICOU_SC}":                  tag_clicou_sc_final,
        "{{TAG_CANCELAR_ENVIOS_SC}}":       tag_cancelar_sc_final,
        "{TAG_CANCELAR_ENVIOS_SC}":         tag_cancelar_sc_final,
        # Tags semana
        "{TAG_INSC_SEMANA1}":               tag_sem1,
        "{TAG_INSC_SEMANA2}":               tag_sem2,
        "{TAG_INSC_SEMANA3}":               tag_sem3,
        # Timestamps SC1
        "{{DT_SC_1230_VARIA}}":             str(gerar_timestamp(data_envio_base, "12:30", offset_atual)),
        "{{DT_SC_1900_VARIA}}":             str(gerar_timestamp(data_envio_base, "19:00", offset_atual)),
        "{{DT_SC_2100_VARIA}}":             str(gerar_timestamp(data_envio_base, "21:00", offset_atual)),
        "{{DT_SC_DS_0740_VARIA}}":          str(gerar_timestamp(data_envio_ds, "07:40", offset_atual)),
        # Timestamps SC2
        "{{DT_SC2_1330_VARIA}}":            str(gerar_timestamp(data_envio_base, "13:30", offset_atual)),
        "{{DT_SC2_1930_VARIA}}":            str(gerar_timestamp(data_envio_base, "19:30", offset_atual)),
        "{{DT_SC2_2130_VARIA}}":            str(gerar_timestamp(data_envio_base, "21:30", offset_atual)),
        "{{DT_SC2_DS_0800_VARIA}}":         str(gerar_timestamp(data_envio_ds, "08:00", offset_atual)),
        # Timestamps SC3
        "{{DT_SC3_1400_VARIA}}":            str(gerar_timestamp(data_envio_base, "14:00", offset_atual)),
        "{{DT_RETOMADA_0800_VARIA}}":       str(gerar_timestamp(data_envio_base, "08:00", offset_atual)),
        "{{DT_SC3_1900_VARIA}}":            str(gerar_timestamp(data_envio_base, "19:00", offset_atual)),
        "{{DT_SC3_2100_VARIA}}":            str(gerar_timestamp(data_envio_base, "21:00", offset_atual)),
        "{{DT_SC3_DS_0740_VARIA}}":         str(gerar_timestamp(data_envio_ds, "07:40", offset_atual)),
        # Links SC
        "{{LINK_HOTMART_SC_M1_T1}}":        fix_link_sc("M1"),
        "{{LINK_HOTMART_SC_M2_T1}}":        fix_link_sc("M2"),
        "{{LINK_HOTMART_SC_M3_T1}}":        fix_link_sc("M3"),
        "{{LINK_HOTMART_SC_M4_T1}}":        fix_link_sc("M4"),
        "{{LINK_HOTMART_SC_M5_T1}}":        fix_link_sc("M5"),
        "{{LINK_HOTMART_SC_M6_T1}}":        fix_link_sc("M6"),
        "{{LINK_HOTMART_SC_M7_T1}}":        fix_link_sc("M7"),
        "{{LINK_HOTMART_SC_M8_T1}}":        fix_link_sc("M8"),
        "{{LINK_HOTMART_SC_rep1_T1}}":      fix_link_sc("rep1"),
        "{{LINK_HOTMART_SC_rep2_T1}}":      fix_link_sc("rep2"),
        "{{LINK_HOTMART_SC_mudei1_T1}}":    fix_link_sc("mudei1"),
        "{{LINK_HOTMART_SC_mudei2_T1}}":    fix_link_sc("mudei2"),
        "{{UTM_SC_LOJA}}":                  f"utm_source={tipo_fluxo}",
        "{{LINK_HOTMART_SC2.1}}":           fix_link_padrao("novat"),
        # Retomada
        "{{DELAY_RETOMADA_S}}":             str(delay_por_curso),
        "{{TAG_CLICOU_RETOMADA}}":          tag_clicou_ret_plan,
        "{{TAG_CANCELAR_ENVIOS_RETOMADA}}": tag_cancelar_ret_plan,
        "{{LINK_HOTMART_RETOMADA_M1}}":     fix_link_retomada("M1"),
        "{{LINK_HOTMART_RETOMADA_M2}}":     fix_link_retomada("M2"),
        "{{LINK_HOTMART_RETOMADA_M3}}":     fix_link_retomada("M3"),
        "{{LINK_HOTMART_RETOMADA_M4}}":     fix_link_retomada("M4"),
        "{{LINK_HOTMART_RETOMADA_M5}}":     fix_link_retomada("M5"),
        "{{LINK_HOTMART_RETOMADA_M6}}":     fix_link_retomada("M6"),
        "{{LINK_HOTMART_RETOMADA_M7}}":     fix_link_retomada("M7"),
        "{{LINK_HOTMART_RETOMADA_M8}}":     fix_link_retomada("M8"),
        "{{LINK_HOTMART_RETOMADA_mudei1}}": fix_link_retomada("mudei1"),
        "{{LINK_HOTMART_RETOMADA_mudei2}}": fix_link_retomada("mudei2"),
        "{{LINK_HOTMART_RETOMADA_rep1}}":   fix_link_retomada("rep1"),
        "{{LINK_HOTMART_RETOMADA_rep2}}":   fix_link_retomada("rep2"),
        "{{UTM_RETOMADA_LOJA}}":            f"utm_source=RETOMADA{ano_retomada if ano_retomada else '2023'}",
    }

    for tag, valor in substituicoes.items():
        conteudo = conteudo.replace(tag, str(valor))

    json_data = json.loads(conteudo)
    json_data = aplicar_template_whatsapp(json_data, dados_template_whatsapp)

    if modo_congresso:
        json_data = aplicar_linguagem_congresso(json_data)

    return json_data
