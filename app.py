# -*- coding: utf-8 -*-
import csv
import io
import os
import sqlite3
from datetime import date, datetime

from flask import (Flask, abort, flash, redirect, render_template, request,
                   send_file, url_for)

import campos
import excel_reporte

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'datos', 'reportes.db')

DIAS = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
         'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
MESES_CORTOS = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN',
                'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC']

ORDENES = [
    ('fecha_desc', 'Fecha (más recientes primero)'),
    ('fecha_asc', 'Fecha (más antiguos primero)'),
    ('asist_desc', 'Asistencia total (mayor primero)'),
    ('entrada_desc', 'Entrada total (mayor primero)'),
]
ORDENES_SQL = {
    'fecha_desc': 'fecha DESC, id DESC',
    'fecha_asc': 'fecha ASC, id ASC',
    'asist_desc': 'asist_total DESC, fecha DESC',
    'entrada_desc': 'entrada_total DESC, fecha DESC',
}

TODAS_COLUMNAS = (['fecha', 'clima', 'predicador', 'tema']
                  + campos.COLUMNAS_ENTEROS + campos.COLUMNAS_REALES + ['notas'])

COLUMNAS_CSV = ['id', 'fecha', 'predicador', 'tema', 'clima',
                'asist_s1', 'asist_s2', 'asist_s3',
                'ninos_s1', 'ninos_s2', 'ninos_s3',
                'asist_total',
                'vol_total_s1', 'vol_total_s2', 'vol_total_s3',
                'en_linea', 'entrada_total', 'notas', 'creado_en']

app = Flask(__name__)
app.secret_key = 'reportes-av-clave-local'


@app.template_filter('fecha_larga')
def fecha_larga(iso):
    try:
        d = date.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso or ''
    return f'{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]} de {d.year}'


@app.template_filter('fecha_corta')
def fecha_corta(iso):
    try:
        d = date.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso or ''
    return f'{d.day} {MESES_CORTOS[d.month - 1]} {d.year}'


@app.template_filter('dinero')
def dinero(v):
    if v is None:
        return '—'
    return f'$ {v:,.2f}'


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
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
    conn.execute('CREATE TABLE IF NOT EXISTS reportes (\n  '
                 + ',\n  '.join(defs) + '\n)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_reportes_fecha ON reportes (fecha)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_reportes_predicador ON reportes (predicador)')
    conn.commit()
    conn.close()


def valores_de(fila):
    valores = {}
    for c in TODAS_COLUMNAS:
        v = fila[c] if fila is not None else None
        valores[c] = '' if v is None else v
    if fila is None:
        valores['fecha'] = date.today().isoformat()
    return valores


def leer_formulario():
    f = request.form
    datos = {}
    fecha = (f.get('fecha') or '').strip()
    if not fecha:
        raise ValueError('La fecha es obligatoria.')
    try:
        date.fromisoformat(fecha)
    except ValueError:
        raise ValueError('La fecha no es válida.')
    datos['fecha'] = fecha
    datos['clima'] = (f.get('clima') or '').strip() or None
    datos['predicador'] = (f.get('predicador') or '').strip()
    if not datos['predicador']:
        raise ValueError('El predicador es obligatorio.')
    datos['tema'] = (f.get('tema') or '').strip() or None
    for c in campos.COLUMNAS_ENTEROS:
        bruto = (f.get(c) or '').strip()
        if bruto == '':
            datos[c] = None
        else:
            try:
                datos[c] = int(bruto)
            except ValueError:
                raise ValueError(
                    f'Valor inválido en "{campos.ETIQUETAS.get(c, c)}": {bruto}')
    for c in campos.COLUMNAS_REALES:
        bruto = (f.get(c) or '').strip().replace(',', '.')
        if bruto == '':
            datos[c] = None
        else:
            try:
                datos[c] = float(bruto)
            except ValueError:
                raise ValueError(
                    f'Valor inválido en "{campos.ETIQUETAS.get(c, c)}": {bruto}')
    datos['notas'] = (f.get('notas') or '').strip() or None
    datos.update(campos.calcular_totales(datos))
    return datos


def guardar(datos, rid=None):
    columnas = TODAS_COLUMNAS + campos.COLUMNAS_CALC
    conn = get_db()
    try:
        if rid is None:
            marcadores = ', '.join('?' * len(columnas))
            sql = f"INSERT INTO reportes ({', '.join(columnas)}) VALUES ({marcadores})"
            cur = conn.execute(sql, [datos.get(c) for c in columnas])
            rid = cur.lastrowid
        else:
            datos = dict(datos)
            datos['actualizado_en'] = datetime.now().isoformat(timespec='seconds')
            columnas = columnas + ['actualizado_en']
            asignaciones = ', '.join(f'{c} = ?' for c in columnas)
            conn.execute(f'UPDATE reportes SET {asignaciones} WHERE id = ?',
                         [datos.get(c) for c in columnas] + [rid])
        conn.commit()
    finally:
        conn.close()
    return rid


def construir_filtros(args):
    condiciones, params = [], []
    q = (args.get('q') or '').strip()
    if q:
        like = f'%{q}%'
        condiciones.append('(predicador LIKE ? OR tema LIKE ? OR notas LIKE ?)')
        params += [like, like, like]
    desde = (args.get('desde') or '').strip()
    if desde:
        condiciones.append('fecha >= ?')
        params.append(desde)
    hasta = (args.get('hasta') or '').strip()
    if hasta:
        condiciones.append('fecha <= ?')
        params.append(hasta)
    orden = args.get('orden') or 'fecha_desc'
    if orden not in ORDENES_SQL:
        orden = 'fecha_desc'
    donde = ('WHERE ' + ' AND '.join(condiciones)) if condiciones else ''
    return donde, params, ORDENES_SQL[orden]


def obtener_reporte(rid):
    conn = get_db()
    fila = conn.execute('SELECT * FROM reportes WHERE id = ?', (rid,)).fetchone()
    conn.close()
    if fila is None:
        abort(404)
    return fila


@app.context_processor
def globales():
    return {
        'servicios': campos.SERVICIOS,
        'ordenes': ORDENES,
        'secciones': campos.SECCIONES_TABLA,
        'kids': campos.GRUPO_KIDS,
        'kids_s3': campos.GRUPO_KIDS_S3,
        'sabado': campos.GRUPO_SABADO,
        'vector': campos.CAMPOS_VECTOR,
        'grupos_vida': campos.CAMPOS_GRUPOS,
        'redes': campos.CAMPOS_REDES,
        'financieros': campos.CAMPOS_FINANCIEROS,
    }


@app.route('/')
def index():
    donde, params, orden_sql = construir_filtros(request.args)
    conn = get_db()
    reportes = conn.execute(
        f'SELECT * FROM reportes {donde} ORDER BY {orden_sql}', params).fetchall()
    agg = conn.execute(
        f'SELECT COUNT(*) AS n, COALESCE(SUM(asist_total), 0) AS a, '
        f'COALESCE(SUM(en_linea), 0) AS e, COALESCE(SUM(entrada_total), 0) AS t '
        f'FROM reportes {donde}', params).fetchone()
    conn.close()
    return render_template('index.html', reportes=reportes, agg=agg)


@app.route('/nuevo', methods=['GET', 'POST'])
def nuevo():
    if request.method == 'POST':
        try:
            datos = leer_formulario()
        except ValueError as exc:
            flash(str(exc), 'error')
            return render_template('formulario.html', valores=request.form, rid=None), 400
        rid = guardar(datos)
        flash('Reporte guardado correctamente.', 'exito')
        return redirect(url_for('detalle', rid=rid))
    return render_template('formulario.html', valores=valores_de(None), rid=None)


@app.route('/editar/<int:rid>', methods=['GET', 'POST'])
def editar(rid):
    if request.method == 'POST':
        try:
            datos = leer_formulario()
        except ValueError as exc:
            flash(str(exc), 'error')
            return render_template('formulario.html', valores=request.form, rid=rid), 400
        guardar(datos, rid)
        flash('Reporte actualizado correctamente.', 'exito')
        return redirect(url_for('detalle', rid=rid))
    fila = obtener_reporte(rid)
    return render_template('formulario.html', valores=valores_de(fila), rid=rid)


@app.route('/reporte/<int:rid>')
def detalle(rid):
    fila = obtener_reporte(rid)
    return render_template('detalle.html', r=fila, valores=valores_de(fila))


@app.route('/reporte/<int:rid>/eliminar', methods=['POST'])
def eliminar(rid):
    conn = get_db()
    conn.execute('DELETE FROM reportes WHERE id = ?', (rid,))
    conn.commit()
    conn.close()
    flash('Reporte eliminado.', 'exito')
    return redirect(url_for('index'))


@app.route('/reporte/<int:rid>/excel')
def descargar_excel(rid):
    fila = obtener_reporte(rid)
    buf, nombre = excel_reporte.generar(dict(fila))
    return send_file(
        buf,
        as_attachment=True,
        download_name=nombre,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@app.route('/exportar.csv')
def exportar_csv():
    donde, params, orden_sql = construir_filtros(request.args)
    conn = get_db()
    filas = conn.execute(
        f'SELECT * FROM reportes {donde} ORDER BY {orden_sql}', params).fetchall()
    conn.close()
    salida = io.StringIO()
    w = csv.writer(salida)
    w.writerow(COLUMNAS_CSV)
    for f in filas:
        w.writerow([f[c] for c in COLUMNAS_CSV])
    data = salida.getvalue().encode('utf-8-sig')
    return send_file(io.BytesIO(data), as_attachment=True,
                     download_name='reportes.csv', mimetype='text/csv')


init_db()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
