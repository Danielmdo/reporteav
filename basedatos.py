# -*- coding: utf-8 -*-
import json
import os
import sqlite3

import requests

TURSO_URL = os.environ.get('TURSO_DATABASE_URL', '').strip()
TURSO_TOKEN = os.environ.get('TURSO_AUTH_TOKEN', '').strip()
EN_VERCEL = bool(os.environ.get('VERCEL'))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_BD_LOCAL = os.environ.get('RUTA_BD') or os.path.join(BASE_DIR, 'datos', 'reportes.db')

MODO = 'turso' if (TURSO_URL and TURSO_TOKEN) else 'sqlite'

_esquema_listo = False


class Fila(dict):
    def __getitem__(self, clave):
        if isinstance(clave, int):
            return list(dict.values(self))[clave]
        return dict.__getitem__(self, clave)


class Resultado:
    def __init__(self, columnas, filas):
        self.columnas = columnas
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
        return Resultado(columnas, [Fila(zip(columnas, f)) for f in filas])

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


def _columnas_esperadas():
    import campos
    cols = [('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
            ('fecha', 'TEXT NOT NULL'),
            ('clima', 'TEXT'),
            ('predicador', "TEXT NOT NULL DEFAULT ''"),
            ('tema', 'TEXT')]
    cols += [(c, 'INTEGER') for c in campos.COLUMNAS_ENTEROS]
    cols += [(c, 'REAL') for c in campos.COLUMNAS_REALES]
    cols.append(('notas', 'TEXT'))
    cols += [(c, 'REAL') for c in campos.COLUMNAS_CALC]
    cols.append(('creado_en', "TEXT DEFAULT (datetime('now', 'localtime'))"))
    cols.append(('actualizado_en', 'TEXT'))
    return cols


def _nombres_columnas(conn):
    res = conn.execute('SELECT * FROM reportes LIMIT 0')
    if hasattr(res, 'description'):
        return {d[0] for d in res.description}
    return set(res.columnas)


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
    if _esquema_listo:
        return conn
    try:
        defs = ',\n  '.join(f'{n} {t}' for n, t in _columnas_esperadas())
        conn.execute(f'CREATE TABLE IF NOT EXISTS reportes (\n  {defs}\n)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_reportes_fecha ON reportes (fecha)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_reportes_predicador ON reportes (predicador)')
        existentes = _nombres_columnas(conn)
        for nombre, tipo in _columnas_esperadas():
            if nombre not in existentes:
                conn.execute(f'ALTER TABLE reportes ADD COLUMN {nombre} {tipo.split()[0]}')
        conn.commit()
        _esquema_listo = True
    except Exception:
        conn.close()
        raise
    return conn
