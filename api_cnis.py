#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API REST para Extração de Texto de CNIS
Integração com Google AI Studio
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import tempfile
import os
from pathlib import Path

app = Flask(__name__)
CORS(app)  # Permite requisições do frontend

def extrair_texto_cnis(pdf_bytes):
    """
    Extrai texto de um PDF CNIS mantendo o formato.
    
    Args:
        pdf_bytes: Bytes do arquivo PDF
        
    Returns:
        Texto extraído formatado
    """
    texto_completo = []
    
    # Cria arquivo temporário
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(pdf_bytes)
        tmp_path = tmp_file.name
    
    try:
        with pdfplumber.open(tmp_path) as pdf:
            for pagina in pdf.pages:
                texto_pagina = pagina.extract_text(
                    layout=True,
                    x_tolerance=2,
                    y_tolerance=2
                )
                if texto_pagina:
                    texto_completo.append(texto_pagina)
    finally:
        # Remove arquivo temporário
        Path(tmp_path).unlink(missing_ok=True)
    
    return '\n'.join(texto_completo)


@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar se a API está funcionando"""
    return jsonify({
        'status': 'ok',
        'message': 'API de Extração de CNIS está funcionando!'
    })


@app.route('/extract', methods=['POST'])
def extract_cnis():
    """
    Endpoint principal para extração de texto de CNIS.
    
    Espera um arquivo PDF no corpo da requisição.
    Retorna o texto extraído em JSON.
    """
    try:
        # Verifica se o arquivo foi enviado
        if 'file' not in request.files:
            return jsonify({
                'error': 'Nenhum arquivo foi enviado',
                'message': 'Envie um arquivo PDF com a chave "file"'
            }), 400
        
        file = request.files['file']
        
        # Verifica se o arquivo tem nome
        if file.filename == '':
            return jsonify({
                'error': 'Nome do arquivo vazio',
                'message': 'O arquivo enviado não tem nome'
            }), 400
        
        # Verifica se é PDF
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({
                'error': 'Formato inválido',
                'message': 'Apenas arquivos PDF são aceitos'
            }), 400
        
        # Lê o arquivo
        pdf_bytes = file.read()
        
        # Extrai o texto
        texto_extraido = extrair_texto_cnis(pdf_bytes)
        
        # Calcula estatísticas
        linhas = texto_extraido.split('\n')
        num_linhas = len(linhas)
        num_chars = len(texto_extraido)
        num_palavras = len(texto_extraido.split())
        
        # Retorna resultado
        return jsonify({
            'success': True,
            'texto': texto_extraido,
            'estatisticas': {
                'linhas': num_linhas,
                'caracteres': num_chars,
                'palavras': num_palavras
            },
            'arquivo': file.filename
        })
    
    except Exception as e:
        return jsonify({
            'error': 'Erro ao processar arquivo',
            'message': str(e)
        }), 500


@app.route('/extract-json', methods=['POST'])
def extract_cnis_json():
    """
    Endpoint alternativo que recebe PDF em base64.
    Útil para integração com Google AI Studio.
    """
    try:
        data = request.get_json()
        
        if not data or 'pdf_base64' not in data:
            return jsonify({
                'error': 'PDF não encontrado',
                'message': 'Envie o PDF em base64 com a chave "pdf_base64"'
            }), 400
        
        import base64
        
        # Decodifica base64
        pdf_bytes = base64.b64decode(data['pdf_base64'])
        
        # Extrai o texto
        texto_extraido = extrair_texto_cnis(pdf_bytes)
        
        # Calcula estatísticas
        linhas = texto_extraido.split('\n')
        num_linhas = len(linhas)
        num_chars = len(texto_extraido)
        num_palavras = len(texto_extraido.split())
        
        # Retorna resultado
        return jsonify({
            'success': True,
            'texto': texto_extraido,
            'estatisticas': {
                'linhas': num_linhas,
                'caracteres': num_chars,
                'palavras': num_palavras
            }
        })
    
    except Exception as e:
        return jsonify({
            'error': 'Erro ao processar arquivo',
            'message': str(e)
        }), 500


if __name__ == '__main__':
    # Modo desenvolvimento
    app.run(host='0.0.0.0', port=5000, debug=True)
