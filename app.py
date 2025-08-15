import csv
import os
from datetime import date, datetime
from flask import Flask, render_template, request, redirect, url_for, flash

# --- CONFIGURAÇÃO DA APLICAÇÃO FLASK ---
app = Flask(__name__)
app.secret_key = 'uma_chave_secreta_muito_segura_para_consultas'

# --- CONFIGURAÇÕES GLOBAIS DO BANCO DE DADOS ---
NOME_ARQUIVO = 'banco_de_dados_sessoes.csv'
CABECALHO = [
    'ID Único', 'Data da Sessão', 'ID da Sessão', 'Dirigente', 'Mestre Assistente',
    'Responsável Preenchimento', 'Qtd. Pessoas', 'ID do Vegetal',
    'Litros Iniciais', 'Litros Finais', 'Litros Consumidos',
    'Consumo por Pessoa (ml)'
]

# --- LÓGICA DO BANCO DE DADOS ---
# (As funções de leitura e escrita permanecem as mesmas da versão anterior)

def inicializar_banco_de_dados():
    if not os.path.exists(NOME_ARQUIVO):
        with open(NOME_ARQUIVO, mode='w', newline='', encoding='utf-8') as f:
            escritor = csv.writer(f)
            escritor.writerow(CABECALHO)

def ler_sessoes():
    sessoes = []
    try:
        with open(NOME_ARQUIVO, mode='r', newline='', encoding='utf-8') as f:
            leitor = csv.DictReader(f)
            for i, linha in enumerate(leitor):
                linha['ID Único'] = i
                sessoes.append(linha)
    except (FileNotFoundError, StopIteration):
        return []
    return sessoes

def escrever_todas_sessoes(sessoes):
    with open(NOME_ARQUIVO, mode='w', newline='', encoding='utf-8') as f:
        escritor = csv.DictWriter(f, fieldnames=CABECALHO)
        escritor.writeheader()
        for sessao in sessoes:
            dados_para_escrever = {k: v for k, v in sessao.items() if k != 'ID Único'}
            escritor.writerow(dados_para_escrever)

def adicionar_sessao(nova_sessao):
    with open(NOME_ARQUIVO, mode='a', newline='', encoding='utf-8') as f:
        escritor = csv.DictWriter(f, fieldnames=CABECALHO)
        if os.path.getsize(NOME_ARQUIVO) == 0:
            escritor.writeheader()
        escritor.writerow({k: v for k, v in nova_sessao.items() if k != 'ID Único'})

# --- ROTAS DA APLICAÇÃO WEB ---

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

@app.route('/')
def index():
    sessoes = ler_sessoes()
    return render_template('index.html', sessoes=list(reversed(sessoes)))

@app.route('/adicionar', methods=['GET', 'POST'])
def adicionar():
    # (Esta rota permanece igual à versão anterior)
    if request.method == 'POST':
        try:
            form_data = request.form.to_dict()
            qtd_pessoas = int(form_data.get('qtd_pessoas'))
            litros_iniciais = float(form_data.get('litros_iniciais'))
            litros_finais = float(form_data.get('litros_finais'))
            
            litros_consumidos = round(litros_iniciais - litros_finais, 2)
            consumo_por_pessoa_ml = round((litros_consumidos * 1000) / qtd_pessoas, 2) if qtd_pessoas > 0 else 0

            nova_sessao = {
                'Data da Sessão': date.today().strftime('%d/%m/%Y'),
                'ID da Sessão': form_data.get('id_sessao'),
                'Dirigente': form_data.get('dirigente'),
                'Mestre Assistente': form_data.get('mestre_assistente'),
                'Responsável Preenchimento': form_data.get('responsavel_preenchimento'),
                'Qtd. Pessoas': qtd_pessoas,
                'ID do Vegetal': form_data.get('id_vegetal'),
                'Litros Iniciais': litros_iniciais,
                'Litros Finais': litros_finais,
                'Litros Consumidos': litros_consumidos,
                'Consumo por Pessoa (ml)': consumo_por_pessoa_ml
            }
            
            adicionar_sessao(nova_sessao)
            flash('Sessão adicionada com sucesso!', 'success')
            return redirect(url_for('index'))
        except (ValueError, TypeError):
            flash('Erro: Os campos de quantidade e litros devem ser números válidos.', 'error')
            return render_template('adicionar.html', form_data=request.form)
    return render_template('adicionar.html', form_data={})


@app.route('/editar/<int:id_unico>', methods=['GET', 'POST'])
def editar(id_unico):
    # (Esta rota permanece igual à versão anterior)
    sessoes = ler_sessoes()
    sessao_para_editar = next((s for s in sessoes if s['ID Único'] == id_unico), None)

    if sessao_para_editar is None:
        flash('Erro: Sessão não encontrada.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            form_data = request.form.to_dict()
            qtd_pessoas = int(form_data.get('qtd_pessoas'))
            litros_iniciais = float(form_data.get('litros_iniciais'))
            litros_finais = float(form_data.get('litros_finais'))

            litros_consumidos = round(litros_iniciais - litros_finais, 2)
            consumo_por_pessoa_ml = round((litros_consumidos * 1000) / qtd_pessoas, 2) if qtd_pessoas > 0 else 0

            sessao_para_editar.update({
                'Data da Sessão': form_data.get('data_sessao'),
                'ID da Sessão': form_data.get('id_sessao'),
                'Dirigente': form_data.get('dirigente'),
                'Mestre Assistente': form_data.get('mestre_assistente'),
                'Responsável Preenchimento': form_data.get('responsavel_preenchimento'),
                'Qtd. Pessoas': qtd_pessoas,
                'ID do Vegetal': form_data.get('id_vegetal'),
                'Litros Iniciais': litros_iniciais,
                'Litros Finais': litros_finais,
                'Litros Consumidos': litros_consumidos,
                'Consumo por Pessoa (ml)': consumo_por_pessoa_ml
            })
            
            escrever_todas_sessoes(sessoes)
            flash('Sessão atualizada com sucesso!', 'success')
            return redirect(url_for('index'))
        except (ValueError, TypeError):
            flash('Erro: Os campos de quantidade e litros devem ser números válidos.', 'error')
            return render_template('editar.html', sessao=form_data, id_unico=id_unico)

    return render_template('editar.html', sessao=sessao_para_editar, id_unico=id_unico)

# --- NOVA ROTA PARA CONSULTAS ---
@app.route('/consultas', methods=['GET', 'POST'])
def consultas():
    if request.method == 'POST':
        dirigente_consulta = request.form.get('dirigente').strip().lower()
        data_inicio_str = request.form.get('data_inicio')
        data_fim_str = request.form.get('data_fim')
        
        sessoes = ler_sessoes()
        resultado_filtrado = []

        try:
            # Converte as datas do formulário para objetos datetime
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d') if data_inicio_str else None
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d') if data_fim_str else None

            for sessao in sessoes:
                # Converte a data da sessão (dd/mm/yyyy) para objeto datetime
                data_sessao = datetime.strptime(sessao['Data da Sessão'], '%d/%m/%Y')
                
                # Verifica as condições do filtro
                match_dirigente = dirigente_consulta in sessao['Dirigente'].strip().lower()
                match_data_inicio = not data_inicio or data_sessao >= data_inicio
                match_data_fim = not data_fim or data_sessao <= data_fim

                if match_dirigente and match_data_inicio and match_data_fim:
                    resultado_filtrado.append(sessao)
            
            # Retorna para a página de consultas com os resultados
            return render_template('consultas.html', 
                                   resultado=resultado_filtrado, 
                                   total=len(resultado_filtrado),
                                   parametros=request.form)

        except ValueError:
            flash('Formato de data inválido. Use o seletor de datas.', 'error')
            return render_template('consultas.html', parametros=request.form)

    # Se for um pedido GET, apenas mostra a página de consultas
    return render_template('consultas.html')


# --- PONTO DE ENTRADA DO PROGRAMA ---
if __name__ == '__main__':
    inicializar_banco_de_dados()
    app.run()
