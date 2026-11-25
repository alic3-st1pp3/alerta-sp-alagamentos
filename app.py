import datetime
import io
import json
import re
import urllib.parse
import feedparser
from google import genai
from google.genai import types
import pandas as pd
from PIL import Image
import pydeck as pdk
import requests
import streamlit as st

# Configuração da página
st.set_page_config(
    page_title="Alerta SP — Mobilidade Segura em Dias de Chuva",
    page_icon="🌧️",
    layout="wide",
)

# Estilo visual acessível e de alto contraste
st.markdown(
    """
    <style>
        .stApp {
            background-color: #F8FAFC;
            color: #0F172A;
            font-size: 16px;
        }
        /* Garante rótulos escuros e legíveis em formulários, inputs e selects */
        label, .stTextInput label, .stSelectbox label, .stTextArea label,
        .stFileUploader label, .stSlider label, .stCheckbox label {
            color: #0F172A !important;
            font-weight: 600 !important;
            font-size: 15px !important;
        }
        .stMarkdown p, .stCaption, [data-testid="stCaptionContainer"] {
            color: #1E293B !important;
        }
        [data-testid="stFileUploaderDropzone"] {
            background-color: #FFFFFF !important;
            border: 1.5px dashed #94A3B8 !important;
            color: #0F172A !important;
        }
        [data-testid="stFileUploaderDropzone"] span,
        [data-testid="stFileUploaderDropzone"] small,
        [data-testid="stFileUploaderDropzone"] div {
            color: #1E293B !important;
        }
        .header-box {
            background-color: #1E3A8A;
            color: #FFFFFF;
            padding: 24px 28px;
            border-radius: 14px;
            margin-bottom: 20px;
        }
        .header-box h1 {
            color: #FFFFFF;
            font-size: 30px;
            margin: 0 0 8px 0;
        }
        .header-box p {
            color: #E2E8F0;
            font-size: 17px;
            margin: 0;
        }
        .card-resumo {
            background-color: #FFFFFF;
            border-radius: 12px;
            padding: 18px 20px;
            border: 1px solid #CBD5E1;
            box-shadow: 0 2px 6px rgba(15, 23, 42, 0.05);
        }
        .card-titulo {
            font-size: 15px;
            font-weight: 700;
            color: #334155;
            margin-bottom: 6px;
        }
        .card-valor {
            font-size: 24px;
            font-weight: 800;
            margin: 0;
        }
        .card-sub {
            font-size: 14px;
            color: #334155;
            margin-top: 6px;
        }
        .privacidade-box {
            background-color: #EFF6FF;
            border-left: 4px solid #1E3A8A;
            padding: 12px 16px;
            border-radius: 8px;
            color: #0F172A;
            font-size: 15px;
            margin-bottom: 16px;
        }
        .escopo-box {
            background-color: #FFFBEB;
            border-left: 4px solid #D97706;
            padding: 12px 16px;
            border-radius: 8px;
            color: #0F172A;
            font-size: 15px;
            margin-bottom: 14px;
        }
        .legenda-box {
            background-color: #FFFFFF;
            border: 1px solid #CBD5E1;
            border-radius: 10px;
            padding: 12px 16px;
            margin-bottom: 12px;
            font-size: 15px;
            color: #0F172A;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# 96 distritos oficiais do município de São Paulo com coordenadas aproximadas
DISTRITOS_SP = {
    "Água Rasa": (-23.5683, -46.5719),
    "Alto de Pinheiros": (-23.5494, -46.7097),
    "Anhanguera": (-23.4381, -46.7836),
    "Aricanduva": (-23.5700, -46.5064),
    "Artur Alvim": (-23.5403, -46.4858),
    "Barra Funda": (-23.5256, -46.6656),
    "Bela Vista": (-23.5614, -46.6464),
    "Belém": (-23.5425, -46.5906),
    "Bom Retiro": (-23.5289, -46.6353),
    "Brás": (-23.5450, -46.6158),
    "Brasilândia": (-23.4614, -46.6939),
    "Butantã": (-23.5719, -46.7081),
    "Cachoeirinha": (-23.4750, -46.6636),
    "Cambuci": (-23.5617, -46.6164),
    "Campo Belo": (-23.6233, -46.6697),
    "Campo Grande": (-23.6797, -46.6933),
    "Campo Limpo": (-23.6489, -46.7594),
    "Capão Redondo": (-23.6686, -46.7806),
    "Carrão": (-23.5469, -46.5397),
    "Casa Verde": (-23.5117, -46.6572),
    "Cidade Ademar": (-23.6758, -46.6553),
    "Cidade Dutra": (-23.7294, -46.6978),
    "Cidade Líder": (-23.5644, -46.4931),
    "Cidade Tiradentes": (-23.5917, -46.4042),
    "Consolação": (-23.5558, -46.6611),
    "Cursino": (-23.6283, -46.6197),
    "Ermelino Matarazzo": (-23.4956, -46.4817),
    "Freguesia do Ó": (-23.5008, -46.7008),
    "Grajaú": (-23.7764, -46.6889),
    "Guaianases": (-23.5439, -46.4125),
    "Iguatemi": (-23.5964, -46.4253),
    "Ipiranga": (-23.5914, -46.6064),
    "Itaim Bibi": (-23.5856, -46.6819),
    "Itaim Paulista": (-23.5017, -46.3983),
    "Itaquera": (-23.5414, -46.4733),
    "Jabaquara": (-23.6464, -46.6408),
    "Jaçanã": (-23.4678, -46.5789),
    "Jaguará": (-23.5122, -46.7486),
    "Jaguaré": (-23.5364, -46.7536),
    "Jaraguá": (-23.4556, -46.7358),
    "Jardim Ângela": (-23.6947, -46.7717),
    "Jardim Helena": (-23.4892, -46.4167),
    "Jardim Paulista": (-23.5689, -46.6689),
    "Jardim São Luís": (-23.6708, -46.7372),
    "José Bonifácio": (-23.5553, -46.4378),
    "Lapa": (-23.5275, -46.7036),
    "Liberdade": (-23.5583, -46.6353),
    "Limão": (-23.5072, -46.6789),
    "Mandaqui": (-23.4839, -46.6339),
    "Marsilac": (-23.9242, -46.6969),
    "Moema": (-23.5994, -46.6656),
    "Mooca": (-23.5558, -46.5978),
    "Morumbi": (-23.6000, -46.7200),
    "Parelheiros": (-23.8297, -46.7308),
    "Pari": (-23.5328, -46.6156),
    "Parque do Carmo": (-23.5667, -46.4625),
    "Pedreira": (-23.6939, -46.6431),
    "Penha": (-23.5289, -46.5419),
    "Perdizes": (-23.5361, -46.6736),
    "Perus": (-23.4067, -46.7539),
    "Pinheiros": (-23.5673, -46.7019),
    "Ponte Rasa": (-23.5161, -46.4947),
    "Raposo Tavares": (-23.5808, -46.7783),
    "República": (-23.5436, -46.6428),
    "Rio Pequeno": (-23.5681, -46.7556),
    "Sacomã": (-23.6019, -46.5961),
    "Santa Cecília": (-23.5356, -46.6517),
    "Santana": (-23.5025, -46.6247),
    "Santo Amaro": (-23.6549, -46.7102),
    "São Domingos": (-23.4956, -46.7433),
    "São Lucas": (-23.5881, -46.5397),
    "São Mateus": (-23.6075, -46.4756),
    "São Miguel": (-23.4958, -46.4419),
    "São Rafael": (-23.6272, -46.4539),
    "Sapopemba": (-23.6075, -46.5064),
    "Saúde": (-23.6147, -46.6383),
    "Sé": (-23.5505, -46.6339),
    "Tatuapé": (-23.5403, -46.5764),
    "Tremembé": (-23.4578, -46.6197),
    "Tucuruvi": (-23.4792, -46.6031),
    "Vila Andrade": (-23.6253, -46.7311),
    "Vila Curuçá": (-23.5131, -46.4161),
    "Vila Formosa": (-23.5656, -46.5442),
    "Vila Guilherme": (-23.5178, -46.6042),
    "Vila Jacuí": (-23.5019, -46.4556),
    "Vila Leopoldina": (-23.5308, -46.7317),
    "Vila Maria": (-23.5144, -46.5881),
    "Vila Mariana": (-23.5892, -46.6347),
    "Vila Matilde": (-23.5342, -46.5194),
    "Vila Medeiros": (-23.4889, -46.5889),
    "Vila Prudente": (-23.5819, -46.5800),
    "Vila Sônia": (-23.5978, -46.7367),
}

MUNICIPIOS_GRANDE_SP = [
    "sao paulo",
    "guarulhos",
    "osasco",
    "santo andre",
    "sao bernardo",
    "sao caetano",
    "diadema",
    "maua",
    "ribeirao pires",
    "rio grande da serra",
    "barueri",
    "carapicuiba",
    "cotia",
    "embu das artes",
    "itapecerica da serra",
    "jandira",
    "santana de parnaiba",
    "taboao da serra",
    "aruja",
    "ferraz de vasconcelos",
    "itaquaquecetuba",
    "mogi das cruzes",
    "poa",
    "suzano",
    "caieiras",
    "cajamar",
    "franco da rocha",
    "francisco morato",
    "mairipora",
]

TERMOS_INTERIOR_EXCLUIR = [
    "campinas",
    "santos",
    "baixada santista",
    "sorocaba",
    "ribeirao preto",
    "sao jose dos campos",
    "vale do paraiba",
    "bauru",
    "franca",
    "marilia",
    "presidente prudente",
    "sao jose do rio preto",
    "piracicaba",
    "jundiai",
    "araraquara",
    "botucatu",
    "itu",
    "americana",
    "limeira",
    "ubatuba",
    "caraguatatuba",
    "sao sebastiao",
    "ilhabela",
]

NIVEIS_AGUA = [
    "Risco leve / Poças",
    "Água na calçada",
    "Intransitável - Água alta",
]


def normalizar_texto(texto: str) -> str:
    mapa_acentos = str.maketrans(
        "áàãâäéèêëíìîïóòõôöúùûüçÁÀÃÂÄÉÈÊËÍÌÎÏÓÒÕÔÖÚÙÛÜÇ",
        "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC",
    )
    return texto.translate(mapa_acentos).lower()


def validar_imagem_com_ia(foto_bytes: bytes):
    """Valida se a imagem é segura e relacionada a rua/alagamento usando o Gemini."""
    api_key = st.secrets.get("GEMINI_API_KEY", None)
    if not api_key:
        return False, "Chave GEMINI_API_KEY não configurada nos Secrets do Streamlit."

    try:
        client = genai.Client(api_key=api_key)
        imagem = Image.open(io.BytesIO(foto_bytes))

        prompt = (
            "Analise esta imagem enviada para um sistema público de alerta de alagamentos em São Paulo. "
            "Responda APENAS em JSON válido com duas chaves booleanas e uma string curta em português:\n"
            '{"segura": true/false, "relacionada_alagamento_ou_via": true/false, "motivo": "explicação curta"}\n'
            "Regras:\n"
            "- segura deve ser false se houver nudez, pornografia, conteúdo sexual, violência explícita ou ofensivo.\n"
            "- relacionada_alagamento_ou_via deve ser true APENAS se a foto mostrar rua, avenida, estação, calçada, chuva, poça, enchente ou trânsito afetado por água.\n"
            "- Se for selfie, meme, tela, animal ou foto interna sem relação com via/chuva/alagamento, relacionada_alagamento_ou_via deve ser false."
        )

        resposta = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[imagem, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )

        resultado = json.loads(resposta.text)
        segura = bool(resultado.get("segura", False))
        relacionada = bool(resultado.get("relacionada_alagamento_ou_via", False))
        motivo = resultado.get("motivo", "Imagem fora dos critérios do sistema.")

        if not segura:
            return False, "Imagem bloqueada pelo filtro de segurança (conteúdo impróprio detectado)."
        if not relacionada:
            return False, f"Imagem recusada: {motivo}. Envie apenas fotos reais da rua ou do alagamento."

        return True, "Imagem validada com sucesso."
    except Exception as e:
        return False, f"Não foi possível validar a imagem agora ({e}). Tente novamente."


@st.cache_data(ttl=1800)
def buscar_chuva_real_sp():
    """Busca previsão real de precipitação (mm) e temperatura para São Paulo via Open-Meteo."""
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=-23.5505&longitude=-46.6339"
        "&daily=precipitation_sum,temperature_2m_max,temperature_2m_min"
        "&timezone=America%2FSao_Paulo"
    )
    try:
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        data = resp.json().get("daily", {})
        chuva_hoje = float(data.get("precipitation_sum", [0.0])[0] or 0.0)
        temp_max = data.get("temperature_2m_max", [None])[0]
        temp_min = data.get("temperature_2m_min", [None])[0]
        return round(chuva_hoje, 1), temp_min, temp_max, True
    except Exception:
        return 12.0, None, None, False


@st.cache_data(ttl=900)
def buscar_noticias_sp_e_grande_sp():
    """
    Busca notícias recentes sobre alagamento e chuva focadas em São Paulo e Grande SP,
    excluindo manchetes voltadas a cidades do interior paulista.
    """
    query = urllib.parse.quote(
        '(alagamento OR enchente OR "chuva forte") ("São Paulo" OR "Grande SP" OR Guarulhos OR Osasco OR ABC)'
    )
    url = f"https://news.google.com/rss/search?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    noticias = []

    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:15]:
            titulo = entry.get("title", "Notícia sem título")
            link = entry.get("link", "")
            fonte = entry.get("source", {}).get("title", "Imprensa local")
            texto_norm = normalizar_texto(f"{titulo} {fonte}")

            if any(re.search(rf"\b{re.escape(termo)}\b", texto_norm) for termo in TERMOS_INTERIOR_EXCLUIR):
                continue

            tem_grande_sp = any(
                re.search(rf"\b{re.escape(mun)}\b", texto_norm) for mun in MUNICIPIOS_GRANDE_SP
            )
            if not tem_grande_sp and "sp" not in texto_norm.split():
                continue

            distrito_detectado = None
            for distrito in DISTRITOS_SP:
                distrito_norm = normalizar_texto(distrito)
                if re.search(rf"\b{re.escape(distrito_norm)}\b", texto_norm):
                    distrito_detectado = distrito
                    break

            if not distrito_detectado:
                distrito_detectado = "Sé"

            noticias.append(
                {
                    "titulo": titulo,
                    "link": link,
                    "fonte": fonte,
                    "distrito_detectado": distrito_detectado,
                }
            )
    except Exception:
        pass

    return noticias[:6]


# Inicializa ocorrências de usuários no estado da sessão
if "ocorrencias_usuarios" not in st.session_state:
    hora_atual = datetime.datetime.now().strftime("%H:%M")
    st.session_state.ocorrencias_usuarios = [
        {
            "id": 1,
            "usuario": "@carlos_zl",
            "distrito": "Itaquera",
            "lat": -23.5414,
            "lon": -46.4733,
            "nivel": "Intransitável - Água alta",
            "horario": hora_atual,
            "descricao": "Água acumulando perto da estação; ônibus com passagem lenta.",
            "foto": None,
            "secou_votos": 0,
        },
        {
            "id": 2,
            "usuario": "@ana_lapa",
            "distrito": "Lapa",
            "lat": -23.5275,
            "lon": -46.7036,
            "nivel": "Água na calçada",
            "horario": hora_atual,
            "descricao": "Calçada tomada pela água e trânsito parado nos arredores.",
            "foto": None,
            "secou_votos": 0,
        },
    ]

if "mensagem_sucesso" not in st.session_state:
    st.session_state.mensagem_sucesso
