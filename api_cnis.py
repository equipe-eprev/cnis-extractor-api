#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API REST para Extração de Texto de CNIS
Integração com Google AI Studio
VERSÃO CORRIGIDA - Formato otimizado para parser TypeScript
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import tempfile
import os
import re
from pathlib import Path

app = Flask(__name__)
CORS(app)  # Permite requisições do frontend

def normalizar_espacos(texto):
    """Remove espaços excessivos e normaliza o layout"""
    # Remove múltiplos espaços, mantendo apenas um
    texto = re.sub(r' {2,}', ' ', texto)
    # Remove espaços no início e fim de cada linha
    linhas = [linha.strip() for linha in texto.split('\n')]
    # Remove linhas vazias duplicadas
    linhas_limpas = []
    linha_vazia_anterior = False
    for linha in linhas:
        if linha:
            linhas_limpas.append(linha)
            linha_vazia_anterior = False
        elif not linha_vazia_anterior:
            linhas_limpas.append('')
            linha_vazia_anterior = True
    return '\n'.join(linhas_limpas)

def consolidar_linhas_quebradas(texto):
    """
    Consolida linhas que foram quebradas incorretamente.
    Exemplo: junta "EMPREGADO" com "DOMÉSTICO" na linha seguinte.
    """
    linhas = texto.split('\n')
    linhas_consolidadas = []
    i = 0
    
    while i < len(linhas):
        linha_atual = linhas[i].strip()
        
        # Se a linha atual não está vazia
        if linha_atual:
            # Verifica se a próxima linha é uma continuação
            if i + 1 < len(linhas):
                proxima_linha = linhas[i + 1].strip()
                
                # Padrões de continuação:
                # 1. Linha atual termina com palavra incompleta (ex: "EMPREGADO")
                # 2. Próxima linha começa com complemento (ex: "DOMÉSTICO")
                # 3. Linha atual não termina com pontuação ou número
                
                # Lista de termos que indicam continuação
                termos_continuacao = ['DOMÉSTICO', 'DOMESTICO', 'INDIVIDUAL', 'FACULTATIVO']
                
                # Se a próxima linha é um termo de continuação e a atual não tem data/número no final
                if (proxima_linha in termos_continuacao and 
                    not re.search(r'\d{2}/\d{2}/\d{4}$', linha_atual) and
                    not re.search(r'\d+,\d{2}$', linha_atual)):
                    linha_atual = linha_atual + ' ' + proxima_linha
                    i += 1  # Pula a próxima linha pois já foi consolidada
            
            linhas_consolidadas.append(linha_atual)
        else:
            linhas_consolidadas.append('')
        
        i += 1
    
    return '\n'.join(linhas_consolidadas)

def limpar_cabecalhos_rodapes(texto):
    """Remove cabeçalhos e rodapés repetitivos de cada página"""
    linhas = texto.split('\n')
    linhas_limpas = []
    
    # Padrões para identificar cabeçalhos/rodapés
    padroes_ignorar = [
        r'^Página \d+ de \d+$',
        r'^INSS\s*$',
        r'^CNIS - Cadastro Nacional',
        r'^Extrato Previdenciário\s*$',
        r'^\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}$'
    ]
    
    for linha in linhas:
        # Verifica se a linha corresponde a algum padrão de cabeçalho/rodapé
        eh_cabecalho_rodape = False
        for padrao in padroes_ignorar:
            if re.match(padrao, linha.strip()):
                eh_cabecalho_rodape = True
                break
        
        # Só adiciona se não for cabeçalho/rodapé ou se for uma linha importante
        if not eh_cabecalho_rodape:
            linhas_limpas.append(linha)
    
    return '\n'.join(linhas_limpas)

def extrair_texto_cnis(pdf_bytes):
    """
    Extrai texto de um PDF CNIS e formata para o parser TypeScript.
    
    Args:
        pdf_bytes: Bytes do arquivo PDF
        
    Returns:
        Texto extraído formatado e otimizado
    """
    texto_completo = []
    
    # Cria arquivo temporário
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(pdf_bytes)
        tmp_path = tmp_file.name
    
    try:
        with pdfplumber.open(tmp_path) as pdf:
            for pagina in pdf.pages:
                # AJUSTE CRÍTICO: usa layout=False para texto mais limpo
                # e ajusta tolerâncias para melhor extração
                texto_pagina = pagina.extract_text(
                    layout=False,  # Mudança principal!
                    x_tolerance=3,
                    y_tolerance=3
                )
                if texto_pagina:
                    texto_completo.append(texto_pagina)
    finally:
        # Remove arquivo temporário
        Path(tmp_path).unlink(missing_ok=True)
    
    # Junta todas as páginas
    texto_bruto = '\n'.join(texto_completo)
    
    # PIPELINE DE LIMPEZA E FORMATAÇÃO:
    # 1. Remove cabeçalhos e rodapés
    texto_limpo = limpar_cabecalhos_rodapes(texto_bruto)
    
    # 2. Normaliza espaços
    texto_limpo = normalizar_espacos(texto_limpo)
    
    # 3. Consolida linhas quebradas
    texto_limpo = consolidar_linhas_quebradas(texto_limpo)
    
    # 4. Normalização final de espaços
    texto_limpo = normalizar_espacos(texto_limpo)
    
    return texto_limpo


@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar se a API está funcionando"""
    return jsonify({
        'status': 'ok',
        'message': 'API de Extração de CNIS está funcionando!',
        'version': '2.0-optimized'
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
            'arquivo': file.filename,
            'versao': '2.0-optimized'
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
            },
            'versao': '2.0-optimized'
        })
    
    except Exception as e:
        return jsonify({
            'error': 'Erro ao processar arquivo',
            'message': str(e)
        }), 500


if __name__ == '__main__':
    # Modo desenvolvimento
    app.run(host='0.0.0.0', port=5000, debug=True)
