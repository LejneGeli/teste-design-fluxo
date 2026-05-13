import streamlit as st
import json
import io
import zipfile
import re
import os
import sys
import base64
from PIL import Image

# Garante que o Python encontra src/ independente de onde o Streamlit é iniciado
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from src.drive_sync import (
        conectar_planilha,
        buscar_mapeamento_contas,
        buscar_cores_linhas,
    )
except Exception as e:
    import streamlit as st
    st.error(f"Erro ao importar drive_sync.py: {e}")
    st.stop()
    
from src.core import processar_curso, obter_template_whatsapp

# Configuração da Interface
favicon_path = os.path.join(BASE_DIR, "logo-site.png")

if os.path.exists(favicon_path):
    favicon = Image.open(favicon_path)
else:
    favicon = "⚙️"

st.set_page_config(
    page_title="CESS Automation Web",
    page_icon=favicon,
    layout="centered"
)

# Diretório base sempre relativo ao próprio app.py (resolve problema de cwd)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def template_path(nome_arquivo):
    return os.path.join(BASE_DIR, "templates", nome_arquivo)


def image_to_base64(path):
    try:
        with open(path, "rb") as img:
            return base64.b64encode(img.read()).decode()
    except FileNotFoundError:
        return ""

LOGO_PATH = os.path.join(BASE_DIR, "logo_automacao_fluxo.png")
LOGO_B64 = image_to_base64(LOGO_PATH)


def aplicar_design():
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        :root {{
            --bg:#05080f;
            --panel:rgba(10,26,48,.84);
            --line:rgba(61,151,255,.28);
            --text:#f3f7ff;
            --muted:#a8b8d8;
            --blue:#2f9bff;
        }}

        html, body, [data-testid="stAppViewContainer"] {{
            background:
                radial-gradient(circle at 12% 88%, rgba(0,78,190,.34), transparent 18rem),
                radial-gradient(circle at 82% 15%, rgba(0,125,255,.12), transparent 20rem),
                linear-gradient(135deg,#030508 0%,#07101f 42%,#020409 100%) !important;
            color:var(--text);
            font-family:'Inter',sans-serif;
        }}

        [data-testid="stHeader"], [data-testid="stToolbar"] {{
            background:transparent !important;
        }}

        /* Moldura principal dinâmica: cresce junto com o conteúdo da página */
        .block-container,
        [data-testid="stMainBlockContainer"] {{
            max-width:1040px !important;
            width:100% !important;
            padding-top:3.2rem !important;
            padding-left:1.5rem !important;
            padding-right:1.5rem !important;
            padding-bottom:2.4rem !important;
            margin:3.5rem auto 2.5rem auto !important;
            position:relative;
            z-index:1;
            border:1px solid rgba(28,113,255,.35);
            border-radius:18px;
            background:rgba(3,10,22,.22);
            box-shadow:0 0 42px rgba(0,91,255,.20), inset 0 0 70px rgba(10,88,180,.08);
        }}

        .cess-panel {{
            width:100%;
            padding:32px 38px 28px;
            border:1px solid var(--line);
            border-radius:18px;
            background:
                linear-gradient(180deg,rgba(15,41,73,.90),rgba(8,20,36,.84)),
                repeating-linear-gradient(90deg,rgba(255,255,255,.018) 0 1px,transparent 1px 8px);
            box-shadow:0 30px 90px rgba(0,0,0,.52), inset 0 1px 0 rgba(255,255,255,.06);
            backdrop-filter:blur(14px);
            margin-bottom:24px;
        }}

        .cess-top {{
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:22px;
            margin-bottom:26px;
        }}

        .cess-brand {{
            display:flex;
            align-items:center;
            gap:22px;
        }}
        .cess-logo-wrap {{
            width:76px;
            height:76px;
            display:flex;
            align-items:center;
            justify-content:center;
            flex:0 0 76px;
        }}
        .cess-brand img {{
            width:70px;
            height:70px;
            object-fit:contain;
            display:block;
            filter:drop-shadow(0 0 18px rgba(46,155,255,.42));
            transform: translateY(-13px);
        }}

        .cess-title {{
            font-size:2.15rem;
            font-weight:800;
            letter-spacing:-.045em;
            margin:0;
            line-height:1.05;
        }}

        .cess-subtitle {{
            color:var(--muted);
            font-size:.92rem;
            margin-top:8px;
        }}

        .cess-badge {{
            border:1px solid rgba(77,159,255,.24);
            background:rgba(5,12,25,.55);
            color:#dceaff;
            padding:8px 14px;
            border-radius:999px;
            font-size:.76rem;
            font-weight:700;
            white-space:nowrap;
        }}

        .steps {{
            display:grid;
            grid-template-columns:repeat(3, 1fr);
            gap:18px;
            padding:8px 0 22px;
            border-bottom:1px solid rgba(73,150,255,.30);
            margin-bottom:24px;
        }}

        .step {{
            display:flex;
            align-items:center;
            justify-content:center;
            gap:10px;
            color:#c7d6ef;
            font-weight:600;
        }}

        .step span {{
            width:30px;
            height:30px;
            display:inline-flex;
            align-items:center;
            justify-content:center;
            border-radius:50%;
            border:1px solid rgba(120,168,255,.36);
            background:rgba(0,0,0,.28);
            color:#dce9ff;
            font-weight:800;
        }}

        .step.active span {{
            background:linear-gradient(135deg,#5ab2ff,#166fd5);
            border-color:transparent;
            color:white;
            box-shadow:0 0 20px rgba(47,155,255,.45);
        }}

        .section-title {{ font-size:1.28rem; font-weight:800; margin-bottom:6px; }}
        .section-copy {{ color:var(--muted); margin-bottom:0; }}

        label, [data-testid="stWidgetLabel"] p {{
            color:#eef5ff !important;
            font-weight:600 !important;
        }}

        [data-baseweb="select"] > div,
        [data-testid="stTextInput"] input,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] > div {{
            background:rgba(8,15,32,.78) !important;
            border:1px solid rgba(109,154,220,.34) !important;
            border-radius:10px !important;
            color:white !important;
            min-height:48px;
            box-shadow:inset 0 0 0 1px rgba(255,255,255,.02);
        }}

        [data-testid="stTextInput"] input:focus {{
            border-color:rgba(58,156,255,.85) !important;
            box-shadow:0 0 0 3px rgba(58,156,255,.18) !important;
        }}

        .stButton > button,
        [data-testid="stDownloadButton"] button {{
            min-height:54px;
            border-radius:12px !important;
            border:1px solid rgba(91,84,255,.65) !important;
            background:linear-gradient(90deg,rgba(44,28,127,.96),rgba(21,55,137,.95)) !important;
            color:#fff !important;
            font-weight:800 !important;
            box-shadow:0 0 26px rgba(65,60,255,.22), inset 0 1px 0 rgba(255,255,255,.10);
            transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease;
        }}

        .stButton > button:hover,
        [data-testid="stDownloadButton"] button:hover {{
            transform:translateY(-10px);
            border-color:rgba(81,171,255,.85) !important;
            box-shadow:0 0 34px rgba(50,145,255,.30), inset 0 1px 0 rgba(255,255,255,.14);
        }}

        [data-testid="stCheckbox"] label {{
            background:rgba(6,14,30,.36);
            border:1px solid rgba(94,148,220,.16);
            border-radius:12px;
            padding:12px 14px;
            width:100%;
        }}

        hr {{
            border-color:rgba(75,151,255,.24) !important;
            margin:1.4rem 0 !important;
        }}

        [data-testid="stAlert"] {{
            border-radius:12px;
            border:0 !important;
            background:transparent !important;
            box-shadow:none !important;
            padding-left:0 !important;
            padding-right:0 !important;
        }}

        .cess-status {{
            margin:16px 0 6px;
            padding:0;
            border:0;
            background:transparent;
            color:#cfe0ff;
            font-size:.94rem;
            font-weight:600;
        }}
        .cess-status.success {{ color:#53f29a; }}
        .cess-status.warning {{ color:#ffd166; }}
        .cess-status.error {{ color:#ff7676; }}
        .cess-status.info {{ color:#65b7ff; }}

        .cess-footer {{
            display:flex;
            justify-content:flex-end;
            align-items:center;
            gap:10px;
            color:#eef4ff;
            font-size:.84rem;
            margin-top:24px;
        }}

        .cess-footer span {{
            background:rgba(255,255,255,.08);
            border-radius:999px;
            padding:5px 12px;
            font-weight:800;
        }}

        [data-testid="stCaptionContainer"] {{
            text-align:center;
            color:rgba(225,236,255,.76) !important;
        }}

        @media (max-width:900px) {{
            .block-container,
            [data-testid="stMainBlockContainer"] {{
                margin:1.2rem auto 1.2rem auto !important;
                padding-top:2.5rem !important;
                padding-left:1rem !important;
                padding-right:1rem !important;
            }}
            .cess-panel {{ padding:24px 20px; }}
            .cess-top {{ display:grid; grid-template-columns:1fr; }}
            .steps {{ grid-template-columns:1fr; }}
            .step {{ justify-content:flex-start; }}
            .cess-title {{ font-size:1.45rem; }}
        }}
    </style>
    """, unsafe_allow_html=True)

def render_header(etapa=1):
    active_1 = "active" if etapa == 1 else ""
    active_2 = "active" if etapa == 2 else ""
    active_3 = "active" if etapa == 3 else ""
    logo_html = f'<div class="cess-logo-wrap"><img src="data:image/png;base64,{LOGO_B64}" alt="Logo CESS Automation"></div>' if LOGO_B64 else ''
    st.markdown(f"""
    <div class="cess-panel">
        <div class="cess-top">
            <div class="cess-brand">
                {logo_html}
                <div>
                    <h1 class="cess-title">CESS • Gerador de Fluxos</h1>
                    <div class="cess-subtitle">Gere e baixe seus arquivos JSON de automação de forma simples e rápida.</div>
                </div>
            </div>
            <div class="cess-badge">CESS Automation System · 2026</div>
        </div>
        <div class="steps">
            <div class="step {active_1}"><span>1</span> Configurar</div>
            <div class="step {active_2}"><span>2</span> Gerar Fluxo</div>
            <div class="step {active_3}"><span>3</span> Download</div>
        </div>
        <div class="section-title">Vamos começar</div>
        <div class="section-copy">Preencha as informações abaixo para gerar seu fluxo de automação.</div>
    </div>
    """, unsafe_allow_html=True)

def status_visual(mensagem, tipo="info"):
    st.markdown(f'<div class="cess-status {tipo}">{mensagem}</div>', unsafe_allow_html=True)

aplicar_design()

# Mapeamento Global dos Fluxos
TEMPLATES = {
    "1":  {"nome": "Inscrição",     "path": template_path("esqueleto_fluxo_insc.json"),    "subpasta": "Fluxo_insc"},
    "2":  {"nome": "Pré-Inscrição", "path": template_path("esqueleto_fluxo_pre_insc.json"),"subpasta": "Fluxo_pre_insc"},
    "3":  {"nome": "Fluxo 1",       "path": template_path("esqueleto_fluxo_1.json"),        "subpasta": "Fluxo_1"},
    "4":  {"nome": "Fluxo 2",       "path": template_path("esqueleto_fluxo_2.json"),        "subpasta": "Fluxo_2"},
    "15": {"nome": "F2.1",          "path": template_path("esqueleto_fluxo_2.1.json"),      "subpasta": "Fluxo_F2_1"},
    "5":  {"nome": "Fluxo 3",       "path": template_path("esqueleto_fluxo_3.json"),        "subpasta": "Fluxo_3"},
    "6":  {"nome": "Fluxo 4",       "path": template_path("esqueleto_fluxo_4.json"),        "subpasta": "Fluxo_4"},
    "7":  {"nome": "Fluxo 5",       "path": template_path("esqueleto_fluxo_5.json"),        "subpasta": "Fluxo_5"},
    "17": {"nome": "F5.1",          "path": template_path("esqueleto_fluxo_5.1.json"),      "subpasta": "Fluxo_F5_1"},
    "8":  {"nome": "Fluxo 6",       "path": template_path("esqueleto_fluxo_6.json"),        "subpasta": "Fluxo_6"},
    "9":  {"nome": "Fluxo 7",       "path": template_path("esqueleto_fluxo_7.json"),        "subpasta": "Fluxo_7"},
    "19": {"nome": "SC0",           "path": template_path("esqueleto_fluxo_sc3.json"),      "subpasta": "Fluxo_SC0"},
    "11": {"nome": "SC1",           "path": template_path("esqueleto_fluxo_sc1.json"),      "subpasta": "Fluxo_SC1"},
    "12": {"nome": "SC2",           "path": template_path("esqueleto_fluxo_sc2.json"),      "subpasta": "Fluxo_SC2"},
    "13": {"nome": "SC3",           "path": template_path("esqueleto_fluxo_sc3.json"),      "subpasta": "Fluxo_SC3"},
    "18": {"nome": "Retroativo",    "path": template_path("esqueleto_fluxo_sc3.json"),      "subpasta": "Fluxo_Retroativo"},
    "16": {"nome": "RETOMADA",      "path": template_path("esqueleto_retomada.json"),       "subpasta": "Fluxo_Retomada"},
    "14": {"nome": "Docs",          "path": template_path("esqueleto_docs.json"),           "subpasta": "Fluxo_Docs"}
}

etapa_atual = 3 if "zip_gerado" in st.session_state else (2 if "cursos" in st.session_state else 1)
render_header(etapa_atual)

# --- 1. CONFIGURAÇÃO DE ENTRADA ---
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        fluxo_label = st.selectbox(
            "Selecione o Fluxo:", 
            ["Inscrição", "Pré-Inscrição", "F1", "F2", "F2.1", "F3", "F4", "F5", "F5.1", "F6", "F7", "SC0", "SC1", "SC2", "SC3", "Retroativo", "RETOMADA", "Docs (Em breve) 🔒", "GERAR TODOS"],
            index=None,
            placeholder="Escolha uma opção"
        )
        map_labels = {
            "Inscrição":"1", "Pré-Inscrição":"2", "F1":"3", "F2":"4", "F2.1":"15", "F3":"5", 
            "F4":"6", "F5":"7", "F5.1":"17", "F6":"8", "F7":"9", "SC0":"19", "SC1":"11", "SC2":"12", 
            "SC3":"13", "Retroativo":"18", "RETOMADA":"16", "Docs (Em breve) 🔒": "14", "GERAR TODOS":"99"
        }
        id_fluxo = map_labels.get(fluxo_label)

    with col2:
        data_semana = st.text_input("Data do Curso (para as tags de Clique):", value="", placeholder="Ex: 16/02")

# --- LÓGICA ESPECÍFICA PARA RETOMADA ---
ano_retomada = None
if fluxo_label == "RETOMADA":
    status_visual("📂 Configuração de Retomada", "info")
    nome_fluxo_retomada = st.text_input("Nome do Fluxo (Ex: Retomada - T 2023):", placeholder="Retomada - T 2023")
    match_ano = re.search(r"202\d", nome_fluxo_retomada)
    if match_ano:
        ano_retomada = match_ano.group(0)
    else:
        status_visual("⚠️ Digite o ano no campo acima para gerar os links corretamente.", "warning")

# --- LÓGICA DE FLUXO RETROATIVO ---
st.divider()
is_retro = st.checkbox("🔄 Este fluxo é retroativo? (Ex: curso de Janeiro rodando agora)")
data_disparo_manual = None

if is_retro:
    data_disparo_manual = st.text_input("Data da Segunda-feira que vai RODAR (DD/MM):", placeholder="Ex: 02/02")
    if data_disparo_manual:
        status_visual(f"💡 Modo retroativo ativo: disparos em {data_disparo_manual} e identidade do fluxo mantida como safra de {data_semana}.", "info")

# --- 2. BUSCA DE DADOS ---
if st.button("🔍 Buscar Cursos na Planilha", use_container_width=True, disabled=not (fluxo_label and data_semana)):
    with st.spinner("Acessando Google Sheets..."):
        client = conectar_planilha("Informações Webhook")
        if client:
            try:
                aba = client.open("Informações Webhook").worksheet("Cursos 2026")
                dados = aba.get_all_values(value_render_option='FORMATTED_VALUE')
                
                inicio = next((i + 2 for i, l in enumerate(dados) if len(l) > 1 and data_semana in str(l[1])), None)
                
                if inicio:
                    cursos_encontrados = []
                    for i in range(inicio, len(dados)):
                        linha = dados[i]
                        if not linha or not linha[0].strip() or (len(linha) > 1 and "Semana" in str(linha[1])):
                            break
                        cursos_encontrados.append(linha[0].strip())
                    
                    # Lê as cores das linhas e monta o mapeamento de cores -> contas
                    with st.spinner("Lendo cores das contas na planilha..."):
                        mapeamento_contas = buscar_mapeamento_contas(client, "Informações Webhook")

                        cores_lista = buscar_cores_linhas(
                            client,
                            "Informações Webhook",
                            "Cursos 2026",
                            inicio + 1,
                            len(cursos_encontrados),
                        )

                    cores_por_indice = {
                        inicio + j: cor
                        for j, cor in enumerate(cores_lista)
                    }

                    st.session_state['cursos'] = cursos_encontrados
                    st.session_state['dados_planilha'] = dados
                    st.session_state['index_inicio'] = inicio
                    st.session_state['mapeamento_contas'] = mapeamento_contas
                    st.session_state['cores_por_indice'] = cores_por_indice

                    if mapeamento_contas:
                        contas = ", ".join(sorted(set(mapeamento_contas.values())))
                        status_visual(f"✅ {len(cursos_encontrados)} cursos encontrados. Contas detectadas: {contas}.", "success")
                    else:
                        status_visual(f"✅ {len(cursos_encontrados)} cursos encontrados. ⚠️ As cores das contas não foram detectadas.", "warning")
                else:
                    status_visual(f"❌ A data '{data_semana}' não foi encontrada na Coluna B da planilha.", "error")
            except Exception as e:
                status_visual(f"❌ Erro ao abrir a planilha/aba: {e}", "error")

# --- 3. FILTRO E GERAÇÃO ---
if 'cursos' in st.session_state:
    st.divider()
    st.subheader("Configuração da Geração")
    
    curso_filtro = st.multiselect(
        "Selecione cursos específicos (ou deixe vazio para todos):", 
        st.session_state['cursos']
    )

    if id_fluxo == "14":
        status_visual("🔒 O fluxo de Docs ainda está em desenvolvimento e o template não foi carregado.", "warning")
        btn_disabled = True
    else:
        btn_disabled = False

    if st.button("🏗️ Gerar Arquivos e Preparar ZIP", use_container_width=True, disabled=btn_disabled):
        zip_buffer = io.BytesIO()
        if id_fluxo == "99":
            fluxos_alvo = [v for k, v in TEMPLATES.items() if k != "14"]
        else:
            fluxos_alvo = [TEMPLATES[id_fluxo]]
        
        arquivos_criados = 0
        mapeamento_contas = st.session_state.get('mapeamento_contas', {})
        cores_por_indice = st.session_state.get('cores_por_indice', {})
        
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for config in fluxos_alvo:
                contadores_por_conta = {}
                nome_fluxo_ativo = config['nome']

                # Para RETOMADA: conta o total de cursos ANTES do loop para calcular o delay certo
                total_cursos_semana = None
                if nome_fluxo_ativo == "RETOMADA":
                    total_cursos_semana = 0
                    for i in range(st.session_state['index_inicio'], len(st.session_state['dados_planilha'])):
                        linha_aux = st.session_state['dados_planilha'][i]
                        if not linha_aux or not linha_aux[0].strip() or (len(linha_aux) > 1 and "Semana" in str(linha_aux[1])):
                            break
                        total_cursos_semana += 1
                
                for i in range(st.session_state['index_inicio'], len(st.session_state['dados_planilha'])):
                    linha = st.session_state['dados_planilha'][i]
                    if not linha or not linha[0].strip() or (len(linha) > 1 and "Semana" in str(linha[1])):
                        break
                    
                    nome_curso = linha[0].strip()
                    if curso_filtro and nome_curso not in curso_filtro:
                        continue

                    cor_curso = cores_por_indice.get(i, "#FFFFFF")
                    conta_pasta = mapeamento_contas.get(cor_curso, "Sem_Conta")

                    if conta_pasta not in contadores_por_conta:
                        contadores_por_conta[conta_pasta] = 0

                    contador_delay_conta = contadores_por_conta[conta_pasta]
                    dados_template_whatsapp = obter_template_whatsapp(conta_pasta, config["nome"])
                    
                    try:
                        json_data = processar_curso(
                            linha, 
                            data_semana, 
                            config['path'], 
                            contador_delay_conta, 
                            tipo_fluxo=nome_fluxo_ativo,
                            data_disparo=data_disparo_manual,
                            ano_retomada=ano_retomada,
                            total_cursos=total_cursos_semana,
                            dados_template_whatsapp=dados_template_whatsapp,
                            usar_delay_retomada=(nome_fluxo_ativo == "RETOMADA")
                        )
                        
                        nome_limpo = nome_curso.replace(" ", "_").replace("/", "-").replace(":", "")
                        caminho_zip = f"{config['subpasta']}/{conta_pasta}/{nome_limpo}.json"
                        
                        zip_file.writestr(caminho_zip, json.dumps(json_data, indent=2, ensure_ascii=False))
                        arquivos_criados += 1
                        contadores_por_conta[conta_pasta] += 1
                    except Exception as e:
                        status_visual(f"Erro no curso '{nome_curso}': {e}", "error")
        
        if arquivos_criados > 0:
            st.session_state["zip_gerado"] = zip_buffer.getvalue()
            st.session_state["zip_nome"] = f"automacao_cess_{data_semana.replace('/','-')}.zip"
            st.session_state["arquivos_criados"] = arquivos_criados
            status_visual(f"🚀 {arquivos_criados} arquivos processados.", "success")
        else:
            status_visual("Nenhum arquivo gerado.", "warning")

if "zip_gerado" in st.session_state:
    st.divider()
    st.subheader("Download")
    status_visual(f"✅ Pronto! {st.session_state.get('arquivos_criados', 0)} arquivos estão preparados para baixar.", "success")
    st.download_button(
        label="⬇️ Baixar Arquivos (.ZIP)",
        data=st.session_state["zip_gerado"],
        file_name=st.session_state.get("zip_nome", "automacao_cess.zip"),
        mime="application/zip",
        use_container_width=True
    )

st.markdown("""<div class="cess-footer"><strong>CESS Automation System</strong><span>2026</span><div>Versão Web Estável</div></div>""", unsafe_allow_html=True)
st.caption("CESS Automation System 2026 - Versão Web Estável")
