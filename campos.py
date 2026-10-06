# -*- coding: utf-8 -*-

SERVICIOS = [('s1', '10:00 a.m.'), ('s2', '12:00 p.m.'), ('s3', '6:00 p.m.')]
COLS_EXCEL = {'s1': 'D', 's2': 'E', 's3': 'F'}

GRUPO_AUDITORIO = [('auditorio', 'Auditorio')]

GRUPO_VOLUNTARIOS = [
    ('primeras_impresiones', 'Primeras impresiones'),
    ('anfitriones', 'Anfitriones'),
    ('estacionamiento', 'Estacionamiento'),
    ('jardin', 'Jardín'),
    ('crece', 'CRECE'),
    ('eventos', 'Eventos'),
    ('alabanza', 'Alabanza'),
    ('produccion', 'Producción'),
    ('kids', 'Kids'),
    ('transporte', 'Transporte'),
    ('contadores', 'Contadores'),
    ('sirviendo_en_amor', 'Sirviendo en amor'),
    ('neon_primaria', 'NEON (5.° y 6.° primaria)'),
    ('jovenes', 'Jóvenes'),
]

GRUPO_CONEXION = [
    ('inv_esp', 'Invitados especiales (primera vez)'),
    ('aceptaron', 'Personas que aceptaron a Cristo'),
    ('bautizos', 'Bautizos'),
    ('recepcion_inv', 'Recepción de invitados (mensual)'),
    ('rutas', 'Rutas de camiones'),
    ('crece_mod1', 'Registro CRECE módulo 1'),
    ('crece_mod2', 'Registro CRECE módulo 2'),
]

GRUPO_KIDS = [
    ('kids_maternal1', '0 a 1.5 años / Maternal 1'),
    ('kids_maternal2', '1.5 a 2 años / Maternal 2'),
    ('kids_kinder1', '3 años / Kinder 1'),
    ('kids_kinder23', '4 y 5 años / Kinder 2 y 3'),
    ('kids_g1', '6 años / 1.° grado'),
    ('kids_g2', '7 años / 2.° grado'),
    ('kids_g3', '8 años / 3.° grado'),
    ('kids_g4', '9 años / 4.° grado'),
]

GRUPO_KIDS_S3 = [
    ('kids_maternal', 'Maternal (0 a 2 años)'),
    ('kids_kinder', 'Kinder (3 a 5 años)'),
    ('kids_grados', 'Primaria (6 a 9 años)'),
]

GRUPO_NEON_JOVENES = [('neon_jovenes', 'NEON (5.° y 6.° primaria)')]

SABADO_COLS = [('de', 'Col. D:E'), ('f', 'Col. F')]

GRUPO_SABADO = [
    ('sab_secundarias', 'Grupos de secundarias (1.° a 3.° grado)'),
    ('sab_preparatorias', 'Grupos de preparatorias (1.° a 3.° grado)'),
]

CAMPOS_VECTOR = [('vector_de', 'VECTOR — col. D:E'), ('vector_f', 'VECTOR — col. F')]

CAMPOS_GRUPOS = [
    ('grupos_fin_semana', 'Grupos de vida fin de semana'),
    ('grupos_entre_semana', 'Grupos de vida entre semana'),
    ('grupo_jovenes', 'Grupo de jóvenes'),
]

CAMPOS_REDES = [
    ('fb_rep15', 'Facebook — Rep. 15 seg. con sonido (ROCK)'),
    ('fb_rep1min', 'Facebook — Rep. al menos 1 minuto'),
    ('yt_views', 'YouTube — Views al terminar el servicio (ROCK)'),
]

CAMPOS_FINANCIEROS = [
    ('online_dlls', 'On line en DLLS'),
    ('efectivo_dlls', 'Efectivo en DLLS — col. D:E'),
    ('efectivo_f_dlls', 'Efectivo en DLLS — col. F'),
]

SECCIONES_TABLA = [
    ('Auditorio', GRUPO_AUDITORIO),
    ('Voluntarios', GRUPO_VOLUNTARIOS),
    ('Datos de conexión', GRUPO_CONEXION),
    ('Jóvenes', GRUPO_NEON_JOVENES),
]


def _cols_servicio(lista, servicios=('s1', 's2', 's3')):
    return [f'{c}_{s}' for c, _ in lista for s in servicios]


COLUMNAS_ENTEROS = (
    _cols_servicio(GRUPO_AUDITORIO)
    + _cols_servicio(GRUPO_VOLUNTARIOS)
    + _cols_servicio(GRUPO_CONEXION)
    + _cols_servicio(GRUPO_KIDS, ('s1', 's2'))
    + [f'{c}_s3' for c, _ in GRUPO_KIDS_S3]
    + _cols_servicio(GRUPO_NEON_JOVENES)
    + [f'{c}_{suf}' for c, _ in GRUPO_SABADO for suf, _ in SABADO_COLS]
    + [c for c, _ in CAMPOS_VECTOR]
    + [c for c, _ in CAMPOS_GRUPOS]
    + [c for c, _ in CAMPOS_REDES]
)

COLUMNAS_REALES = [c for c, _ in CAMPOS_FINANCIEROS]

COLUMNAS_CALC = [
    'asist_s1', 'asist_s2', 'asist_s3',
    'ninos_s1', 'ninos_s2', 'ninos_s3',
    'asist_total',
    'vol_total_s1', 'vol_total_s2', 'vol_total_s3',
    'en_linea', 'entrada_total',
]

ETIQUETAS = {}
for _lista in (GRUPO_AUDITORIO, GRUPO_VOLUNTARIOS, GRUPO_CONEXION,
               GRUPO_KIDS, GRUPO_KIDS_S3, GRUPO_NEON_JOVENES):
    for _c, _e in _lista:
        for _s, _h in SERVICIOS:
            ETIQUETAS.setdefault(f'{_c}_{_s}', f'{_e} ({_h})')
for _c, _e in GRUPO_SABADO:
    for _suf, _col in SABADO_COLS:
        ETIQUETAS[f'{_c}_{_suf}'] = f'{_e} — {_col}'
for _lista in (CAMPOS_VECTOR, CAMPOS_GRUPOS, CAMPOS_REDES, CAMPOS_FINANCIEROS):
    for _c, _e in _lista:
        ETIQUETAS[_c] = _e


def _mapa_servicio(lista, fila):
    mapa = {}
    for i, (c, _) in enumerate(lista):
        for s, _h in SERVICIOS:
            mapa[f'{c}_{s}'] = f'{COLS_EXCEL[s]}{fila + i}'
    return mapa


EXCEL_MAP = {}
EXCEL_MAP.update(_mapa_servicio(GRUPO_AUDITORIO, 9))
EXCEL_MAP.update(_mapa_servicio(GRUPO_VOLUNTARIOS, 11))
EXCEL_MAP.update(_mapa_servicio(GRUPO_CONEXION, 27))
EXCEL_MAP.update(_mapa_servicio(GRUPO_NEON_JOVENES, 45))
for i, (c, _) in enumerate(GRUPO_KIDS):
    EXCEL_MAP[f'{c}_s1'] = f'D{35 + i}'
    EXCEL_MAP[f'{c}_s2'] = f'E{35 + i}'
EXCEL_MAP['kids_maternal_s3'] = 'F35'
EXCEL_MAP['kids_kinder_s3'] = 'F37'
EXCEL_MAP['kids_grados_s3'] = 'F39'
EXCEL_MAP['sab_secundarias_de'] = 'D47'
EXCEL_MAP['sab_secundarias_f'] = 'F47'
EXCEL_MAP['sab_preparatorias_de'] = 'D48'
EXCEL_MAP['sab_preparatorias_f'] = 'F48'
EXCEL_MAP['vector_de'] = 'D51'
EXCEL_MAP['vector_f'] = 'F51'
EXCEL_MAP['grupos_fin_semana'] = 'D53'
EXCEL_MAP['grupos_entre_semana'] = 'D54'
EXCEL_MAP['grupo_jovenes'] = 'D55'
EXCEL_MAP['fb_rep15'] = 'J5'
EXCEL_MAP['fb_rep1min'] = 'J6'
EXCEL_MAP['yt_views'] = 'J7'
EXCEL_MAP['online_dlls'] = 'D57'
EXCEL_MAP['efectivo_dlls'] = 'D58'
EXCEL_MAP['efectivo_f_dlls'] = 'F58'


def _n(v, c):
    x = v.get(c)
    return x if x is not None else 0


def calcular_totales(v):
    t = {}
    for s in ('s1', 's2', 's3'):
        t[f'asist_{s}'] = (_n(v, f'primeras_impresiones_{s}')
                           - _n(v, f'anfitriones_{s}')
                           - _n(v, f'estacionamiento_{s}')
                           - _n(v, f'jardin_{s}')
                           + _n(v, f'crece_{s}')
                           + _n(v, f'kids_{s}')
                           + _n(v, f'neon_primaria_{s}')
                           + _n(v, f'jovenes_{s}')
                           + _n(v, f'auditorio_{s}'))
        t[f'vol_total_{s}'] = (_n(v, f'primeras_impresiones_{s}')
                               + _n(v, f'crece_{s}')
                               + _n(v, f'eventos_{s}')
                               + _n(v, f'alabanza_{s}')
                               + _n(v, f'produccion_{s}')
                               + _n(v, f'kids_{s}')
                               + _n(v, f'transporte_{s}')
                               + _n(v, f'contadores_{s}')
                               + _n(v, f'sirviendo_en_amor_{s}')
                               + _n(v, f'neon_primaria_{s}')
                               + _n(v, f'jovenes_{s}'))
    for s in ('s1', 's2'):
        t[f'ninos_{s}'] = (sum(_n(v, f'{c}_{s}') for c, _ in GRUPO_KIDS)
                           + _n(v, f'neon_jovenes_{s}'))
    t['ninos_s3'] = (_n(v, 'kids_maternal_s3') + _n(v, 'kids_kinder_s3')
                     + _n(v, 'kids_grados_s3') + _n(v, 'neon_jovenes_s3'))
    t['asist_total'] = (t['asist_s1'] + t['asist_s2'] + t['asist_s3']
                        + t['ninos_s1'] + t['ninos_s2'] + t['ninos_s3'])
    t['en_linea'] = _n(v, 'fb_rep15') + _n(v, 'yt_views')
    t['entrada_total'] = (_n(v, 'online_dlls') + _n(v, 'efectivo_dlls')
                          + _n(v, 'efectivo_f_dlls'))
    return t
