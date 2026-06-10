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

def calcular_timestamp_dt_final_semana(data_str):
    """
    Calcula o timestamp de corte das aulas.

    Regra: o curso começa na segunda e as aulas ficam disponíveis até
    a terça-feira da semana seguinte. Como a automação precisa bloquear
    a partir da quarta-feira, usamos D+9 às 00:00.

    Exemplo: início em 22/06 -> corte em 01/07 00:00.
    """
    try:
        data_corte = calcular_data_especifica(data_str, 9)
        return gerar_timestamp(data_corte, "00:00", 0)
    except Exception:
        return 0


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
    """
    Aplica os dados do template oficial do WhatsApp em todos os pontos do JSON.

    Importante: no JSON exportado pelo Unnichat, o template aparece em mais de
    um lugar:
      1. dentro de message.template;
      2. no templateId da mensagem;
      3. em alguns blocos, também existe um template "irmão" do message.

    Antes a troca acontecia só dentro de message.template. Por isso, ao importar
    no Unnichat, a tela ainda podia mostrar o template antigo no seletor.
    """
    if not dados_template:
        return json_data

    # Estrutura de cadastro manual:
    # se algum campo ainda estiver em branco ou com "COLE_AQUI",
    # a automação não força a troca do template no JSON.
    campos_obrigatorios = ["nome", "connectionId", "wabaId", "userId", "id"]
    for campo in campos_obrigatorios:
        valor = str(dados_template.get(campo, "")).strip()
        if not valor or "COLE_AQUI" in valor:
            return json_data

    def atualizar_template_obj(template_obj):
        """Atualiza o objeto interno de template sem apagar componentes/botões."""
        if not isinstance(template_obj, dict):
            return

        template_obj["name"] = dados_template["nome"]
        template_obj["id"] = dados_template["id"]
        template_obj["connectionId"] = dados_template["connectionId"]
        template_obj["wabaId"] = dados_template["wabaId"]
        template_obj["userId"] = dados_template["userId"]

        # Mantém o padrão mais seguro para template já aprovado.
        if dados_template.get("status"):
            template_obj["status"] = dados_template["status"]
        elif template_obj.get("status"):
            template_obj["status"] = "APPROVED"

        if dados_template.get("category"):
            template_obj["category"] = dados_template["category"]

        if dados_template.get("language"):
            template_obj["language"] = dados_template["language"]

    def atualizar_mensagem_template(msg_obj):
        """Atualiza o bloco message quando ele é de envio de template."""
        if not isinstance(msg_obj, dict):
            return

        msg_obj["templateId"] = dados_template["id"]
        atualizar_template_obj(msg_obj.get("template"))

        # Algumas exportações guardam o template serializado em string.
        if "templateDataJson" in msg_obj:
            try:
                template_json = json.loads(msg_obj["templateDataJson"])
                atualizar_template_obj(template_json)
                msg_obj["templateDataJson"] = json.dumps(template_json, ensure_ascii=False)
            except Exception:
                pass

    def percorrer(obj):
        if isinstance(obj, dict):
            # Caso 1: estamos no nó inteiro; atualiza message e o template irmão.
            if isinstance(obj.get("message"), dict) and obj["message"].get("type") == "send_template":
                atualizar_mensagem_template(obj["message"])
                atualizar_template_obj(obj.get("template"))

            # Caso 2: estamos diretamente dentro do objeto message.
            if obj.get("type") == "send_template" or "templateDataJson" in obj:
                atualizar_mensagem_template(obj)

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
        },
        'Entrega - Certificado Digital':{
            'nome': "m1_entrega_certificado_curso_c1",
            'connectionId': 'ouLDZiM3pEddrZuTGJVw',
            'wabaId': '551316877339100',
            'userId': '3jNt3SinWzW08N7iqGhu473b7M53',
            'id': "1550361646687896"
        },
        'Entrega - Certificado Digital Congresso': {
            'nome': "m1_entrega_certificado_congresso_c1",
            'connectionId': 'ouLDZiM3pEddrZuTGJVw',
            'wabaId': '551316877339100',
             'userId': '3jNt3SinWzW08N7iqGhu473b7M53',
            'id': "1300209292304188"
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
        },
        'Entrega - Certificado Digital':{
            'nome': "m1_entrega_certificado_curso_c2",
            'connectionId': 'ouLDZiM3pEddrZuTGJVw',
            'wabaId': '551316877339100',
            'userId': '3jNt3SinWzW08N7iqGhu473b7M53',
            'id': "3312044972308387"
        },
        'Entrega - Certificado Digital Congresso': {
            'nome': "m1_entrega_certificado_congresso_c2",
            'connectionId': 'ouLDZiM3pEddrZuTGJVw',
            'wabaId': '551316877339100',
            'userId': '3jNt3SinWzW08N7iqGhu473b7M53',
            'id': "1758624955153309"
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
        },
        'Entrega - Certificado Digital':{
            'nome': "m2_entrega_certificado_curso_c3",
            'connectionId': 'ouLDZiM3pEddrZuTGJVw',
            'wabaId': '551316877339100',
            'userId': '3jNt3SinWzW08N7iqGhu473b7M53',
            'id': "1764809034485592"
        },
        'Entrega - Certificado Digital Congresso': {
            'nome': "m1_entrega_certificado_congresso_c3",
            'connectionId': 'ouLDZiM3pEddrZuTGJVw',
            'wabaId': '551316877339100',
            'userId': '3jNt3SinWzW08N7iqGhu473b7M53',
            'id': "26826007523729394"
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
        },
        'Entrega - Certificado Digital':{
            'nome': "m1_entrega_certificado_curso_c4",
            'connectionId': 'ouLDZiM3pEddrZuTGJVw',
            'wabaId': '551316877339100',
            'userId': '3jNt3SinWzW08N7iqGhu473b7M53',
            'id': "2338332203320440"
        },
        'Entrega - Certificado Digital Congresso': {
            'nome': "m1_entrega_certificado_congresso_c4",
            'connectionId': 'ouLDZiM3pEddrZuTGJVw',
            'wabaId': '551316877339100',
            'userId': '3jNt3SinWzW08N7iqGhu473b7M53',
            'id': "2003930783851763"
        }
    },
}

def normalizar_chave(texto):
    """Normaliza textos para comparação simples entre planilhas."""
    return str(texto or "").strip().casefold()


def montar_link_inscricao_instagram(linha):
    """
    Monta o link de inscrição usado nos fluxos de Instagram.

    Regra atual:
      1. usar o código do curso da coluna G da aba Cursos 2026;
      2. NÃO usar a coluna J, porque ela contém código do curso + abertura;
      3. se a coluna G estiver vazia, tentar reaproveitar um link cessetembro.com.br
         já presente na linha como fallback de segurança.
    """
    codigo_curso = limpar_para_json(linha[6]) if len(linha) > 6 else ""
    if codigo_curso:
        if codigo_curso.startswith("http"):
            return codigo_curso
        return f"https://cessetembro.com.br/{codigo_curso.lstrip('/')}"

    for valor in linha:
        valor_str = str(valor or "").strip()
        if (
            "cessetembro.com.br/" in valor_str
            and "setecertificados.com.br" not in valor_str
            and "webhook" not in valor_str.lower()
        ):
            return valor_str

    return ""


def formatar_data_tag_instagram(data_inicio_curso):
    """Formata a data usada no final das tags do Instagram.

    As tags do Unnichat precisam identificar a semana com ano completo,
    por exemplo: [22/06/2026]. A tela normalmente recebe só DD/MM,
    então esta função completa o ano automaticamente.
    """
    data = str(data_inicio_curso or "").strip()
    if not data:
        return data

    # Remove espaços extras e possíveis colchetes, caso a data venha reaproveitada
    # de algum texto/template.
    data = data.replace("[", "").replace("]", "").strip()

    partes = [parte.strip() for parte in data.split("/") if parte.strip()]

    # Entrada padrão da interface: DD/MM -> DD/MM/2026
    if len(partes) == 2:
        dia, mes = partes
        return f"{dia.zfill(2)}/{mes.zfill(2)}/2026"

    # Caso já venha com ano, apenas normaliza DD/MM/AAAA.
    if len(partes) == 3:
        dia, mes, ano = partes
        return f"{dia.zfill(2)}/{mes.zfill(2)}/{ano}"

    return data


def montar_tags_instagram(nome_curso, data_inicio_curso, origem):
    """
    Monta as tags dos fluxos de Instagram mantendo o mesmo padrão visual
    para Comentário e Story.
    """
    data_tag = formatar_data_tag_instagram(data_inicio_curso)
    return {
        "interesse": f"[{nome_curso}] - Interesse [G] [{origem}]",
        "depois": f"[{nome_curso}] - Deixa para Depois [G] [{origem}]",
        "click_m1": f"[{nome_curso}] - Clicou inscrever-se [G] [M1] [{origem}] [{data_tag}]",
        "click_dd": f"[{nome_curso}] - Clicou inscrever-se [G] [DD] [{origem}] [{data_tag}]",
        "click_m2": f"[{nome_curso}] - Clicou inscrever-se [G] [M2] [{origem}] [{data_tag}]",
        "click_cursos": f"[{nome_curso}] - Clicou + Cursos [G] [DD] [{origem}]",
    }


def processar_instagram(
    linha,
    data_ancora,
    path_template,
    num_fluxo,
    origem,
):
    """
    Processa templates de Instagram.

    Esses fluxos usam uma aba auxiliar, Instagram_Infos, para buscar o número
    do gatilho. O restante é montado automaticamente a partir do curso,
    da data da semana e do padrão de tags.
    """
    nome_curso = limpar_para_json(linha[0]) if linha else ""
    num_fluxo = limpar_para_json(num_fluxo)
    link_inscricao = montar_link_inscricao_instagram(linha)

    tags = montar_tags_instagram(nome_curso, data_ancora, origem)

    with open(path_template, "r", encoding="utf-8") as f:
        conteudo = f.read()

    prefixo = "comentario" if origem == "Comentário" else "story"

    substituicoes = {
        "{{curso}}": nome_curso,
        "{{num_fluxo}}": num_fluxo,
        "{{link_inscricao}}": link_inscricao,
        "{{data_inicio_curso}}": data_ancora,

        f"{{{{tag_ig_{prefixo}_interesse}}}}": tags["interesse"],
        f"{{{{tag_ig_{prefixo}_depois}}}}": tags["depois"],
        f"{{{{tag_ig_{prefixo}_click_m1}}}}": tags["click_m1"],
        f"{{{{tag_ig_{prefixo}_click_dd}}}}": tags["click_dd"],
        f"{{{{tag_ig_{prefixo}_click_m2}}}}": tags["click_m2"],
        f"{{{{tag_ig_{prefixo}_click_cursos}}}}": tags["click_cursos"],
    }

    for tag, valor in substituicoes.items():
        conteudo = conteudo.replace(tag, str(valor))

    return json.loads(conteudo)

def data_curta(semana):
    if not semana:
        return ""

    partes = str(semana).split("/")
    if len(partes) >= 2:
        return f"{partes[0]}/{partes[1]}"

    return str(semana)


def montar_dados_curso(abertura, tipo_fluxo="SC1"):
    nome_curso = limpar_para_json(abertura.get("nomeCurso", ""))
    semana = data_curta(abertura.get("semana", ""))

    tag_foi_plan = f"Foi pra Planilha - {nome_curso} {semana}"
    tag_insc_curso = f"Inscrição - {nome_curso} {semana}"
    tag_cancel = f"Cancelar Inscrição - {nome_curso} {semana}"

    dados = {
        "nome_curso": nome_curso,
        "webhook_link": abertura.get("webhookUnnichat", ""),
        "cd_curso_abert": limpar_para_json(abertura.get("codigoAbertura", "")),

        "tag_foi_plan": limpar_para_json(tag_foi_plan),
        "tag_insc_curso": limpar_para_json(tag_insc_curso),
        "tag_cancel": limpar_para_json(tag_cancel),

        "tag_atrasados_f1": limpar_para_json(f"Iniciar F. - {nome_curso} {semana}"),
        "tag_inicio_f2": limpar_para_json(f"Fluxo 2 - {nome_curso} {semana}"),
        "tag_inicio_f3": limpar_para_json(f"Fluxo 3 - {nome_curso} {semana}"),
        "tag_inicio_f4": limpar_para_json(f"Fluxo 4 - {nome_curso} {semana}"),
        "tag_inicio_f5": limpar_para_json(f"Fluxo 5 - {nome_curso} {semana}"),
        "tag_inicio_f6": limpar_para_json(f"Fluxo 6 - {nome_curso} {semana}"),
        "tag_inicio_f7": limpar_para_json(f"Fluxo 7 - {nome_curso} {semana}"),
        "tag_inicio_f8": limpar_para_json(f"Fluxo 8 - {nome_curso} {semana}"),

        "tag_presente_f8": limpar_para_json(f"Presente - {nome_curso} {semana}"),
        "tag_cert": limpar_para_json(f"{nome_curso} - Certificado Digital"),
        "tag_insc_geral": limpar_para_json(f"Inscritos {semana}"),

        "vol_pdf_2": "",
        "titulo_pdf": "",
        "gatilho_fx": limpar_para_json(abertura.get("fraseGatilho", "")),
        "bonus_cursos": limpar_para_json((abertura.get("bonus") or {}).get("nome", "")),

        "link_hotmart_raw": abertura.get("linkPagamentoUTM") or abertura.get("linkPagamentoCert", ""),
        "cd_cert": limpar_para_json(abertura.get("codigoSiteCert", "")),
        "cd_aulas": limpar_para_json(abertura.get("codigoSiteAula", "")),
        "cd_pdf": limpar_para_json(abertura.get("codigoSitePDF", "")),

        "tag_clicou_sc1": limpar_para_json(f"Clicou SC1 - {nome_curso} {semana}"),
        "tag_cancelar_sc1": limpar_para_json(f"Cancelar SC1 - {nome_curso} {semana}"),
        "tag_clicou_sc2": limpar_para_json(f"Clicou SC2 - {nome_curso} {semana}"),
        "tag_cancelar_sc2": limpar_para_json(f"Cancelar SC2 - {nome_curso} {semana}"),
        "tag_clicou_sc": limpar_para_json(f"Clicou SC - {nome_curso} {semana}"),
        "tag_cancelar_sc": limpar_para_json(f"Cancelar SC - {nome_curso} {semana}"),

        "tag_clicou_ret_plan": limpar_para_json(f"Clicou Retomada - {nome_curso} {semana}"),
        "tag_cancelar_ret_plan": limpar_para_json(f"Cancelar Retomada - {nome_curso} {semana}"),

        "link_cert_img": limpar_para_json(abertura.get("linkCertificado", "")),
        "link_pdf": limpar_para_json(abertura.get("linkEbook", "")),
    }

    if tipo_fluxo == "SC1":
        dados["tag_clicou_retro"] = dados["tag_clicou_sc1"]
        dados["tag_cancelar_retro"] = dados["tag_cancelar_sc1"]
    elif tipo_fluxo == "SC2":
        dados["tag_clicou_retro"] = dados["tag_clicou_sc2"]
        dados["tag_cancelar_retro"] = dados["tag_cancelar_sc2"]
    else:
        dados["tag_clicou_retro"] = dados["tag_clicou_sc"]
        dados["tag_cancelar_retro"] = dados["tag_cancelar_sc"]

    return dados

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

        # --- 2. MAPEAMENTO GERAL DO FIRESTORE ---
    dados_curso = montar_dados_curso(linha, tipo_fluxo)

    nome_curso       = dados_curso["nome_curso"]
    webhook_link     = dados_curso["webhook_link"]
    cd_curso_abert   = dados_curso["cd_curso_abert"]
    tag_foi_plan     = dados_curso["tag_foi_plan"]
    tag_insc_curso   = dados_curso["tag_insc_curso"]
    tag_cancel       = dados_curso["tag_cancel"]
    tag_atrasados_f1 = dados_curso["tag_atrasados_f1"]
    tag_inicio_f2    = dados_curso["tag_inicio_f2"]
    tag_inicio_f3    = dados_curso["tag_inicio_f3"]
    tag_inicio_f4    = dados_curso["tag_inicio_f4"]
    tag_inicio_f5    = dados_curso["tag_inicio_f5"]
    tag_inicio_f6    = dados_curso["tag_inicio_f6"]
    tag_inicio_f7    = dados_curso["tag_inicio_f7"]
    tag_inicio_f8    = dados_curso["tag_inicio_f8"]
    tag_presente_f8  = dados_curso["tag_presente_f8"]
    tag_cert         = dados_curso["tag_cert"]
    tag_insc_geral   = dados_curso["tag_insc_geral"]
    vol_pdf_2        = dados_curso["vol_pdf_2"]
    titulo_pdf       = dados_curso["titulo_pdf"]
    gatilho_fx       = dados_curso["gatilho_fx"]
    bonus_cursos     = dados_curso["bonus_cursos"]
    link_hotmart_raw = dados_curso["link_hotmart_raw"]
    cd_cert          = dados_curso["cd_cert"]
    cd_aulas         = dados_curso["cd_aulas"]
    cd_pdf           = dados_curso["cd_pdf"]

    tag_clicou_retro   = dados_curso["tag_clicou_retro"]
    tag_cancelar_retro = dados_curso["tag_cancelar_retro"]

    tag_clicou_ret_plan   = dados_curso["tag_clicou_ret_plan"]
    tag_cancelar_ret_plan = dados_curso["tag_cancelar_ret_plan"]

    link_cert_img = dados_curso["link_cert_img"]
    link_pdf = dados_curso["link_pdf"]

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
    dt_final_semana = calcular_timestamp_dt_final_semana(data_ancora)
    dt_final_semana_format = calcular_data_especifica(data_ancora, 9)

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

    substituicoes = {
        "{{NOME_CURSO}}":                   nome_curso,
        "{{curso}}":                        nome_curso,
        "{{GATILHO_INICIO_FX}}":            gatilho_fx,
        "{{TAG_FOI_PLANILHA}}":             tag_foi_plan,
        "{{TAG_INSC_CURSO}}":               tag_insc_curso,
        "{{TAG_INSC_GERAL}}":               tag_insc_geral,
        "{{TAG_CANCEL_CURSO}}":             tag_cancel,
        "{{TAG_CERT_CURSO}}":               tag_cert,
        "{{tag_cert_comprado}}":            tag_cert,
        "{{CD_CURSO_CERT}}":                cd_cert,
        "{{CD_CURSO_AULAS}}":               cd_aulas,
        "{{CD_CURSO_PDF}}":                 cd_pdf,
        "{{CD_CURSO_ABERT}}":               cd_curso_abert,
        "{{VOL_PDF_2}}":                    vol_pdf_2,
        "{{BONUS_CURSOS}}":                 bonus_cursos,
        "{{LINK_WEBHOOK_PLANILHA}}":        webhook_link,
        "{{DT_INICIO_CURSO_EXT}}":          data_extenso,
        "{{DT_INICIO_CURSO_FORMAT}}":       data_ancora,
        "{{data_inicio_ext}}":              data_extenso,
        "{{DT_AULAS_DISP_CURSO_FORMAT}}":   data_aulas_ate,
        "{{dt_final_semana}}":              str(dt_final_semana),
        "{{DT_FINAL_SEMANA}}":              str(dt_final_semana),
        "{{DT_FINAL_SEMANA_FORMAT}}":       dt_final_semana_format,
        "{{DT_FIM_CERT_FORMAT}}":           data_prazo_cert,
        "{{LINK_CERTIFICADO_IMG}}":         link_cert_img,
        "{{link_cert_img}}":                link_cert_img,
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
        "{{DT_SC_1930_VARIA}}":             str(gerar_timestamp(data_envio_base, "19:30", offset_atual)),
        "{{DT_SC_2130_VARIA}}":             str(gerar_timestamp(data_envio_base, "21:30", offset_atual)),
        "{{DT_SC_DS_0750_VARIA}}":          str(gerar_timestamp(data_envio_ds, "07:50", offset_atual)),
        # Timestamps SC2
        "{{DT_SC2_1330_VARIA}}":            str(gerar_timestamp(data_envio_base, "13:30", offset_atual)),
        "{{DT_SC2_1930_VARIA}}":            str(gerar_timestamp(data_envio_base, "19:30", offset_atual)),
        "{{DT_SC2_2130_VARIA}}":            str(gerar_timestamp(data_envio_base, "21:30", offset_atual)),
        "{{DT_SC2_DS_0800_VARIA}}":         str(gerar_timestamp(data_envio_ds, "08:00", offset_atual)),
        # Timestamps SC3
        "{{DT_SC3_1400_VARIA}}":            str(gerar_timestamp(data_envio_base, "14:00", offset_atual)),
        "{{DT_RETOMADA_0800_VARIA}}":       str(gerar_timestamp(data_envio_base, "08:00", offset_atual)),
        "{{DT_SC3_1900_VARIA}}":            str(gerar_timestamp(data_envio_base, "19:30", offset_atual)),
        "{{DT_SC3_2100_VARIA}}":            str(gerar_timestamp(data_envio_base, "21:30", offset_atual)),
        "{{DT_SC3_DS_0740_VARIA}}":         str(gerar_timestamp(data_envio_ds, "07:40", offset_atual)),
        # Timestamps SC0
        "{{dt_sc0_1300}}":                  str(gerar_timestamp(data_envio_base, "13:00", offset_atual)),
        "{{dt_sc0_1830}}":                  str(gerar_timestamp(data_envio_base, "18:30", offset_atual)),
        "{{dt_sc0_2030}}":                  str(gerar_timestamp(data_envio_base, "20:30", offset_atual)),
        "{{dt_sc0_depois_0730}}":           str(gerar_timestamp(data_envio_ds, "07:30", offset_atual)),
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
        "{{utm_sc}}":                       f"utm_source={tipo_fluxo}",
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
