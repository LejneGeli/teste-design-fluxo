def data_curta(semana):
    """
    Converte 13/04/2026 para 13/04.
    """
    if not semana:
        return ""

    partes = str(semana).split("/")
    if len(partes) >= 2:
        return f"{partes[0]}/{partes[1]}"

    return str(semana)


def abertura_para_linha(abertura):
    """
    Converte um documento da coleção aberturas para o formato antigo de linha da planilha.
    Opção A: manter compatibilidade com o core.py.
    """
    nome_curso = abertura.get("nomeCurso", "")
    semana_completa = abertura.get("semana", "")
    semana_curta = data_curta(semana_completa)

    codigo_abertura = abertura.get("codigoAbertura", "")
    curso_id = abertura.get("cursoId", "")
    webhook = abertura.get("webhookUnnichat", "")

    codigo_cert = abertura.get("codigoSiteCert", "")
    codigo_aulas = abertura.get("codigoSiteAula", "")
    codigo_pdf = abertura.get("codigoSitePDF", "")

    link_hotmart = (
        abertura.get("linkPagamentoUTM")
        or abertura.get("linkPagamentoCert")
        or ""
    )

    link_certificado = abertura.get("linkCertificado", "")
    link_pdf = abertura.get("linkEbook", "")

    bonus = abertura.get("bonus") or {}
    bonus_nome = bonus.get("nome", "") if isinstance(bonus, dict) else ""

    # linha fake com tamanho suficiente para os índices usados no core.py
    linha = [""] * 49

    linha[0] = nome_curso
    linha[1] = semana_curta
    linha[4] = webhook
    linha[6] = curso_id
    linha[9] = codigo_abertura

    # Tags padronizadas
    linha[11] = f"Foi pra Planilha - {nome_curso} {semana_curta}"
    linha[12] = f"Inscrição - {nome_curso} {semana_curta}"
    linha[13] = f"Cancelar Inscrição - {nome_curso} {semana_curta}"
    linha[14] = f"Iniciar F. - {nome_curso} {semana_curta}"
    linha[15] = f"Fluxo 2 - {nome_curso} {semana_curta}"
    linha[16] = f"Fluxo 3 - {nome_curso} {semana_curta}"
    linha[17] = f"Fluxo 4 - {nome_curso} {semana_curta}"
    linha[18] = f"Fluxo 5 - {nome_curso} {semana_curta}"
    linha[19] = f"Fluxo 6 - {nome_curso} {semana_curta}"
    linha[20] = f"Fluxo 7 - {nome_curso} {semana_curta}"
    linha[21] = f"Fluxo 8 - {nome_curso} {semana_curta}"
    linha[22] = f"Presente - {nome_curso} {semana_curta}"
    linha[23] = f"{nome_curso} - Certificado Digital"
    linha[24] = f"Inscritos {semana_curta}"

    linha[27] = ""
    linha[28] = ""
    linha[31] = abertura.get("fraseGatilho", "")
    linha[32] = bonus_nome

    linha[33] = link_hotmart
    linha[34] = codigo_cert
    linha[35] = codigo_aulas
    linha[36] = codigo_pdf

    # Tags de retroativo / retomada
    linha[38] = f"Clicou SC1 - {nome_curso} {semana_curta}"
    linha[39] = f"Cancelar SC1 - {nome_curso} {semana_curta}"
    linha[40] = f"Clicou SC2 - {nome_curso} {semana_curta}"
    linha[41] = f"Cancelar SC2 - {nome_curso} {semana_curta}"
    linha[42] = f"Clicou SC - {nome_curso} {semana_curta}"
    linha[43] = f"Cancelar SC - {nome_curso} {semana_curta}"
    linha[44] = f"Clicou Retomada - {nome_curso} {semana_curta}"
    linha[45] = f"Cancelar Retomada - {nome_curso} {semana_curta}"

    linha[47] = link_certificado
    linha[48] = link_pdf

    return linha


def aberturas_para_dados_planilha(aberturas):
    """
    Cria uma lista no mesmo estilo do dados_planilha antigo.
    """
    dados = []

    # Linha fake de cabeçalho
    dados.append(["Curso", "Semana"])

    for abertura in aberturas:
        dados.append(abertura_para_linha(abertura))

    return dados