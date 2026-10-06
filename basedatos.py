# -*- coding: utf-8 -*-
import json
import os
import sqlite3

import requests

TURSO_URL = os.environ.get('TURSO_DATABASE_URL', '').strip()
TURSO_TOKEN = os.environ.get('TURSO_AUTH_TOKEN', '').strip()
EN_VERCEL = bool(os.environ.get('VERCEL'))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_BD_LOCAL = os.path.join(BASE_DIR, 'datos', 'reportes.db')

MODO = 'turso' if (TURSO_URL and TURSO_TOKEN) else 'sqlite'

_esquema_listo = False


class Fila(dict):
    def __getitem__(self, clave):
        if isinstance(clave, int):
            return list(dict.values(self))[clave]
        return dict.__getitem__(self, clave)


class Resultado:
    def __init__(self, filas):
        self._filas = filas

    def fetchone(self):
        return self._filas[0] if self._filas else None

    def fetchall(self):
        return self._filas

    @property
    def lastrowid(self):
        return self._filas[0][0] if self._filas else None


class ConexionTurso:
    def __init__(self, url, token):
        if url.startswith('libsql://'):
            url = 'https://' + url[len('libsql://'):]
        self._url = url.rstrip('/') + '/v2/pipeline'
        self._cabeceras = {'Authorization': 'Bearer ' + token}

    def execute(self, sql, params=()):
        cuerpo = {'requests': [
            {'type': 'execute',
             'stmt': {'sql': sql, 'args': [_codificar_valor(p) for p in params]}},
            {'type': 'close'},
        ]}
        r = requests.post(self._url, headers=self._cabeceras, json=cuerpo, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f'Turso respondió HTTP {r.status_code}: {r.text[:300]}')
        try:
            datos = r.json()
        except ValueError:
            raise RuntimeError('Turso respondió con un cuerpo no válido.')
        columnas, filas = [], []
        for resultado in datos.get('results', []):
            if resultado.get('type') == 'error':
                raise RuntimeError('Error de Turso: '
                                   + resultado.get('error', {}).get('message', 'desconocido'))
            respuesta = resultado.get('response', {})
            if respuesta.get('type') == 'execute':
                res = respuesta.get('result', {})
                columnas = [c.get('name', f'c{i}')
                            for i, c in enumerate(res.get('cols', []))]
                filas = [[_decodificar_valor(celda) for celda in fila]
                         for fila in res.get('rows', [])]
        return Resultado([Fila(zip(columnas, f)) for f in filas])

    def commit(self):
        pass

    def close(self):
        pass


def _codificar_valor(v):
    if v is None:
        return {'type': 'null', 'value': None}
    if isinstance(v, bool):
        return {'type': 'integer', 'value': '1' if v else '0'}
    if isinstance(v, int):
        return {'type': 'integer', 'value': str(v)}
    if isinstance(v, float):
        return {'type': 'float', 'value': repr(v)}
    return {'type': 'text', 'value': str(v)}


def _decodificar_valor(celda):
    if not isinstance(celda, dict):
        return None
    tipo = celda.get('type')
    valor = celda.get('value')
    if tipo == 'null' or valor is None:
        return None
    if tipo == 'integer':
        return int(valor)
    if tipo == 'float':
        return float(valor)
    if tipo == 'json':
        return json.loads(valor)
    return valor


def _sentencias_esquema():
    import campos
    defs = ['id INTEGER PRIMARY KEY AUTOINCREMENT',
            'fecha TEXT NOT NULL',
            'clima TEXT',
            "predicador TEXT NOT NULL DEFAULT ''",
            'tema TEXT']
    defs += [f'{c} INTEGER' for c in campos.COLUMNAS_ENTEROS]
    defs += [f'{c} REAL' for c in campos.COLUMNAS_REALES]
    defs.append('notas TEXT')
    defs += [f'{c} REAL' for c in campos.COLUMNAS_CALC]
    defs += ["creado_en TEXT DEFAULT (datetime('now', 'localtime'))",
             'actualizado_en TEXT']
    return [
        'CREATE TABLE IF NOT EXISTS reportes (\n  ' + ',\n  '.join(defs) + '\n)',
        'CREATE INDEX IF NOT EXISTS idx_reportes_fecha ON reportes (fecha)',
        'CREATE INDEX IF NOT EXISTS idx_reportes_predicador ON reportes (predicador)',
    ]


def _abrir():
    if MODO == 'turso':
        return ConexionTurso(TURSO_URL, TURSO_TOKEN)
    if EN_VERCEL:
        raise RuntimeError(
            'En Vercel la base de datos debe ser Turso (SQLite en la nube). '
            'Configura las variables de entorno TURSO_DATABASE_URL y TURSO_AUTH_TOKEN.')
    os.makedirs(os.path.dirname(RUTA_BD_LOCAL), exist_ok=True)
    conn = sqlite3.connect(RUTA_BD_LOCAL)
    conn.row_factory = sqlite3.Row
    return conn


def conectar():
    global _esquema_listo
    conn = _abrir()
    if not _esquema_listo:
        try:
            for sentencia in _sentencias_esquema():
                conn.execute(sentencia)
            conn.commit()
            _esquema_listo = True
        except Exception:
            conn.close()
            raise
    return conn
