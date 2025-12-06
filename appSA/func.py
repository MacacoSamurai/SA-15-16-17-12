
from flask import Flask, render_template, request, redirect, url_for, session, flash
from main import app, CONFIG_DB
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
import mysql.connector
pi = str ("pagi")
lg = str ("login")

DB_HOST = CONFIG_DB['host']
DB_USER = CONFIG_DB['user']
DB_PASSWORD = CONFIG_DB['password']
DB_NAME = CONFIG_DB['database'] 
DB_PORT = CONFIG_DB['port'] 



"""
-------- Funções Gerais --------
"""

#função para a conexão mais simples com o db
def db_connection():
    return mysql.connector.connect(
        host=DB_HOST, 
        user=DB_USER, 
        password=DB_PASSWORD,
        database=DB_NAME, 
        port=DB_PORT
    )

#verifica se é gerente
def cargos():
    user_id = session.get('user_id') 
    
    if not user_id:
        return False # Não logado

    conexao = None
    cursor = None # Inicializa para garantir que o 'finally' funcione
    try:
        conexao = db_connection()
        cursor = conexao.cursor() # CORRIGIDO: Deve ser chamado como método ()
        
        # Busca o cargo pelo id_func (que é o que está armazenado na session)
        query = "SELECT cargo FROM funcionarios WHERE id_func = %s"
        cursor.execute(query, (user_id,)) # Usa o user_id da sessão
        
        cargo_data = cursor.fetchone() # Retorna uma tupla (ex: ('gerente',))

        # CORRIGIDO: Verifica se o resultado existe E se o primeiro item da tupla é "gerente"
        if cargo_data and cargo_data[0] == "gerente": 
            return True
        else:
            return False

    except mysql.connector.Error as err:
        print(f"Erro ao buscar cargo: {err}")
        return False
    
    finally:
        if 'cursor' in locals() and cursor: 
            cursor.close()
        if conexao and conexao.is_connected():
            conexao.close()

#requerimento de login para a segurança
def login_required(f):  
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: # <--- Mantenha 'user_id'
            flash("Você precisa fazer login para acessar esta página.")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

#Requerimento de gerencia para segurança
def gerente_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 2. Chama a função cargos() que verifica se o usuário é gerente
        if not cargos():
            flash("Acesso negado: Você não tem permissão de Gerente para esta ação.")
            # Redireciona para a página principal (ou outra página de erro)
            return redirect(url_for('pagi')) 
            
        return f(*args, **kwargs)
    return decorated_function




#URL inicial
@app.route("/")


#pagina inicial para a escolha das opções
@app.route(f"/{pi}")
@login_required
def pagi():  

    erro = request.args.get('erro')
    sucesso = request.args.get('sucesso')
    return render_template(f"{pi}.html", erro=erro, sucesso=sucesso)



#pagina de login
@app.route(f"/{lg}", methods=["GET", "POST"])
def login():

    if request.method == 'POST':

        login_user = request.form['usuario']
        senha_user = request.form['senha']        


        conexao = None
        try:
            conexao = db_connection()




            cursor = conexao.cursor(dictionary=True)

            query = "SELECT id_func, senha_user FROM funcionarios WHERE login_user = %s"
            cursor.execute(query, (login_user,))
            funcionario = cursor.fetchone()

            if funcionario:
                senha_hash_armazenada = funcionario['senha_user']
                
                # Verifica se a senha é um hash (começa com 'pbkdf2:sha256')
                if check_password_hash(senha_hash_armazenada, senha_user):
                    session['user_id'] = funcionario['id_func']

                    return redirect(url_for(f'{pi}'))
                else:
                    # Se o hash for inválido
                    return render_template(f"{lg}.html", erro="Usuário ou senha inválidos!")
                    
            else:
                return render_template(f"{lg}.html", erro="Usuário não encontrado!")
            
        except mysql.connector.Error as err:
            print(f"Erro no login: {err}")
            return render_template(f"{lg}.html", erro="Erro interno do servidor.")
        finally:
            if conexao and conexao.is_connected():
                cursor.close()
                conexao.close()

    if session.get('user_id'):
        return redirect('/pagi')

    return render_template(f"{lg}.html", erro="")  



#logout,encerra a sessão de login
@app.route("/logout")
def logout():
    # Limpa toda a sessão
    session.clear() 
    # session.pop('logged_in', None) # Alternativa para limpar apenas um item
    return redirect(url_for(f'{lg}'))



"""
<-------- Area De Clientes -------->
"""

#pagina de salvar cliente
@app.route("/cadastro_cliente", methods=['GET', 'POST'])
@login_required
def cadastro_cliente():
    conexao = None
    if request.method == 'POST':

        nome = request.form['nome_cliente']     
        cpf = request.form['cpf_cliente']        
        celular = request.form['celular_cliente'] 

        placa_carro = request.form['placa_carro1']
        modelo = request.form['modelo_carro']
        fabricante = request.form['fabricante_carro']
        
        dados_carros = (placa_carro, modelo, fabricante)
        dados_clientes = (nome, cpf, celular, placa_carro)

        try:
            conexao = db_connection()
            cursor = conexao.cursor()
            
            sql_verify_cliente = "SELECT id_cliente FROM clientes WHERE cpf = %s OR placa_carro = %s"


            cursor.execute(sql_verify_cliente, (cpf, placa_carro))
            cliente_existente = cursor.fetchone()

            if cliente_existente:
                 return render_template(f"cadastro_cliente.html", erro="Cliente com este CPF ou Placa já cadastrado!")

            # Ação 3: Uso de INSERT IGNORE para não falhar se a placa já existe
            sql_carros = "INSERT IGNORE INTO carros (placa_carro, modelo, fabricante) VALUES (%s, %s, %s)"
            cursor.execute(sql_carros, dados_carros)

            sql_clientes = "INSERT INTO clientes (nome_cliente, cpf, celular, placa_carro) VALUES (%s, %s, %s, %s)" 
            cursor.execute(sql_clientes, dados_clientes)
            
            conexao.commit()
            
            # Redireciona para a página inicial (ou para uma página de sucesso)
            return redirect(f"/listar_clientes")

        except mysql.connector.Error as err:
            print(f"Erro ao salvar cliente: {err}")
            conexao.rollback()
            return render_template(f"{pi}.html", erro=f"Erro no banco de dados: {err.msg}") 
    
        finally:
            if conexao and conexao.is_connected():
                cursor.close()
                conexao.close()
    return render_template("cadastro_cliente.html")                



#pagina de editar clientes
@app.route("/editar_cliente/<cpf_original>", methods=['GET', 'POST'])
@login_required
def editar_cliente(cpf_original):
    conexao = None
    cursor = None

    try:
        conexao = db_connection()
        cursor = conexao.cursor()

        if request.method == 'POST':

            nome = request.form['nome_cliente']     
            cpf_novo = request.form['cpf_cliente']        
            celular = request.form['celular_cliente'] 

            placa_carro_nova = request.form['placa_carro']
            modelo = request.form['modelo_carro']
            fabricante = request.form['fabricante_carro']

            cpf_original = request.form['cpf_original']


            sql_placaCPF = "SELECT placa_carro FROM clientes WHERE cpf = (%s)"  
            cursor.execute(sql_placaCPF, (cpf_original,))
            placa_original_data = cursor.fetchone()
        
            if placa_original_data is None:
                return render_template("editar_cliente.html", erro=f"Cliente com CPF {cpf_original} não encontrado.", cliente={'cpf_original_url': cpf_original})

            placa_original = placa_original_data[0]

        
            sql_update_cliente = "UPDATE clientes SET nome_cliente = %s, cpf = %s, celular = %s, placa_carro = %s WHERE cpf = %s"
            dados_clientes = (nome, cpf_novo, celular, placa_carro_nova, cpf_original)
            cursor.execute(sql_update_cliente, dados_clientes,)
        
            # 2. Deletar da tabela `carros`
            sql_update_carro = "UPDATE carros set placa_carro = %s, modelo = %s, fabricante = %s WHERE placa_carro = %s"
            dados_carros = (placa_carro_nova, modelo, fabricante, placa_original)
            cursor.execute(sql_update_carro, dados_carros,)
        
            conexao.commit()

            return redirect(f"/listar_clientes")

        else:
            # --- FASE GET: Buscar dados para pré-preencher o formulário ---
            
            # Query que junta cliente e carro (necessário para pegar o modelo/fabricante)
            sql_select = """
            SELECT c.nome_cliente, c.cpf, c.celular, ca.placa_carro, ca.modelo, ca.fabricante, ca.placa_carro as placa_original
            FROM clientes c
            JOIN carros ca ON c.placa_carro = ca.placa_carro
            WHERE c.cpf = %s
            """
            cursor.execute(sql_select, (cpf_original,))
            cliente_data = cursor.fetchone()

            if cliente_data is None:
                # Não encontrou o cliente com o CPF da URL.
                return render_template("listar_clientes.html", erro=f"Cliente com CPF {cpf_original} não encontrado para edição.")

            cliente = {
                'nome': cliente_data[0],
                'cpf': cliente_data[1],
                'celular': cliente_data[2],
                'placa_carro': cliente_data[3],
                'modelo': cliente_data[4],
                'fabricante': cliente_data[5],
                # Passa o CPF original da URL para o formulário (útil como campo hidden)
                'cpf_original_url': cpf_original
            }

            return render_template("editar_cliente.html", cliente=cliente)
        
    except mysql.connector.Error as err:
        print(f"Erro ao deletar cliente: {err}")
        if conexao:
            conexao.rollback()
        # Use um template adequado para a mensagem de erro
        return render_template("editar_cliente.html", erro=f"Erro no banco de dados: Não foi possível editar o cliente. Detalhe: {err}")
    
    finally:
        if cursor is not None:
            cursor.close()
        if conexao and conexao.is_connected():
            conexao.close()



#pagina de listar clientes
@app.route("/listar_clientes")
@login_required
def listar_clientes():
    conn = None
    clientes = []
    try:
        # Estabelece conexão com o DB
        conn = db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if cargos():
        # 1. Query para selecionar 5 itens do estoque
            query1 = """
            SELECT c.nome_cliente, c.cpf, c.celular, ca.placa_carro, ca.modelo, ca.fabricante 
            FROM clientes c
            JOIN carros ca ON c.placa_carro = ca.placa_carro
            """
            cursor.execute(query1)

            clientes = cursor.fetchall()

        else:
        # 2. Query para selecionar todos os itens do estoque
            query2 = """
            SELECT c.nome_cliente, c.cpf, c.celular, ca.placa_carro, ca.modelo, ca.fabricante 
            FROM clientes c
            JOIN carros ca ON c.placa_carro = ca.placa_carro
            LIMIT 5
            """
            cursor.execute(query2)

            clientes = cursor.fetchall()



    except mysql.connector.Error as err:
        print(f"Erro ao listar clientes: {err}")
        return render_template(f"{pi}.html", erro="Erro ao listar clientes.")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

    # Redirecionar para uma nova página de visualização dos clientes 
    return render_template("listar_clientes.html", clientes=clientes)



#pagina de deletar clientes
@app.route("/delete_cliente", methods=['POST'])
@login_required
def delete_cliente():
    conexao = None
    
    cpf_deletar = request.form['cpf_deletar']    

    if not cpf_deletar:
        return render_template(f"{pi}.html", erro="CPF para deleção não fornecido.")

    try:
        conexao = db_connection()
        cursor = conexao.cursor()


        sql_placaCPF = "SELECT placa_carro FROM clientes WHERE cpf = (%s)"
        cursor.execute(sql_placaCPF, (cpf_deletar,))
        resultado = cursor.fetchone()
        
        if resultado is None:
            return render_template(f"{pi}.html", erro=f"Cliente com CPF {cpf_deletar} não encontrado.")

        placa = resultado[0]


        sql_delete_registros = "DELETE FROM registro_servico WHERE placa = %s"
        cursor.execute(sql_delete_registros, (placa,))

        
        sql_delete_cliente = "DELETE FROM clientes WHERE placa_carro = %s"
        cursor.execute(sql_delete_cliente, (placa,))
        

        sql_delete_carro = "DELETE FROM carros WHERE placa_carro = %s"
        cursor.execute(sql_delete_carro, (placa,))
        
        conexao.commit()
        
        # Verifica se alguma linha foi afetada para confirmar a exclusão
        if cursor.rowcount > 0:
            return redirect(f"/listar_clientes") # Redireciona para a página inicial
        else:
            return render_template(f"{pi}.html", erro="Carro/Cliente não encontrado ou deleção falhou.")

    except mysql.connector.Error as err:
        print(f"Erro ao deletar cliente: {err}")
        conexao.rollback()
        return render_template(f"{pi}.html", erro=f"Erro no banco de dados: Não foi possível deletar o cliente, verifique se há registros de serviço associados.") 
    
    finally:
        if conexao and conexao.is_connected():
            cursor.close()
            conexao.close()



"""
<-------- Area De Funcionários -------->
"""

#pagina para cadastrar funcionários
@app.route("/cadastro_func", methods=['GET', 'POST'])
@login_required 
@gerente_required #só funciona se for gerente
def cadastro_func():
    if cargos == True:
        return
    conexao = None
    if request.method == 'POST':
        nome = request.form['nome_func']     
        login_user = request.form['login_user']        
        senha_user = request.form['senha_user'] 
        cargo = request.form['cargo']
        cpf = request.form['cpf']

        senha_hash = generate_password_hash(senha_user)
        
        dados_funcionario = (nome, login_user, senha_hash, cargo, cpf)

        try:
            conexao = db_connection()
            cursor = conexao.cursor()
            
            sql_verify = "SELECT id_func FROM funcionarios WHERE login_user = %s OR cpf = %s"
            cursor.execute(sql_verify, (login_user, cpf))
            funcionario_existente = cursor.fetchone()

            if funcionario_existente:
                 return render_template("cadastro_func.html", erro="Funcionário com este Login ou CPF já cadastrado!")

            sql_insert = "INSERT INTO funcionarios (nome_func, login_user, senha_user, cargo, cpf) VALUES (%s, %s, %s, %s, %s)" 
            cursor.execute(sql_insert, dados_funcionario)
            
            conexao.commit()
            
            return redirect(f"/listar_func")

        except mysql.connector.Error as err:
            print(f"Erro ao salvar funcionário: {err}")
            conexao.rollback()
            return render_template("cadastro_func.html", erro=f"Erro no banco de dados: {err.msg}") 
    
        finally:
            if conexao and conexao.is_connected():
                cursor.close()
                conexao.close()

    return render_template("cadastro_func.html")



#pagina para listar funcionários
@app.route("/listar_func")
@login_required
@gerente_required
def listar_func():
    conn = None
    funcionarios = []
    try:
        conn = db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT id_func, nome_func, login_user, cargo, cpf FROM funcionarios"
        cursor.execute(query)
        
        funcionarios = cursor.fetchall()
        
    except mysql.connector.Error as err:
        print(f"Erro ao listar funcionários: {err}")
        return render_template(f"{pi}.html", erro="Erro ao carregar a lista de funcionários.")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

    return render_template("listar_func.html", funcionarios=funcionarios)



#pagina para editar funcionários
@app.route("/editar_func/<int:id_func_original>", methods=['GET', 'POST'])
@login_required
@gerente_required
def editar_func(id_func_original):
    conexao = None
    
    try:
        conexao = db_connection()
        cursor = conexao.cursor()

        if request.method == 'POST':
            nome = request.form['nome_func']     
            login_user = request.form['login_user']        
            senha_user = request.form['senha_user'] 
            cargo = request.form['cargo']
            cpf = request.form['cpf']
            id_func = request.form['id_func_editar']
            
            if not senha_user:
                 sql_update = "UPDATE funcionarios SET nome_func = %s, login_user = %s, cargo = %s, cpf = %s WHERE id_func = %s"
                 dados_func = (nome, login_user, cargo, cpf, id_func)
            else:
                 senha_hash = generate_password_hash(senha_user)
                 sql_update = "UPDATE funcionarios SET nome_func = %s, login_user = %s, senha_user = %s, cargo = %s, cpf = %s WHERE id_func = %s"
                 dados_func = (nome, login_user, senha_hash, cargo, cpf, id_func)

            cursor.execute(sql_update, dados_func)
            conexao.commit()

            return redirect(url_for('listar_func')) 
            
        else:
            # --- FASE GET: Buscar dados para pré-preencher o formulário ---
            sql_select = "SELECT id_func, nome_func, login_user, cargo, cpf FROM funcionarios WHERE id_func = %s"
            cursor.execute(sql_select, (id_func_original,))
            funcionario_data = cursor.fetchone()
        
            if funcionario_data is None:
                return render_template(f"listar_func.html", erro=f"Funcionário com ID {id_func_original} não encontrado.")

            funcionario = {
                'id_func': funcionario_data[0],
                'nome_func': funcionario_data[1],
                'login_user': funcionario_data[2],
                'cargo': funcionario_data[3],
                'cpf': funcionario_data[4]
            }
            
            return render_template("editar_func.html", funcionario=funcionario) 

    except mysql.connector.Error as err:
        print(f"Erro ao editar funcionário: {err}")
        if conexao:
            conexao.rollback()
        return render_template(f"{pi}.html", erro=f"Erro no banco de dados: Não foi possível editar o funcionário.") 
    
    finally:
        if conexao and conexao.is_connected():
            cursor.close()
            conexao.close()



#pagina para deletar funcionários
@app.route("/delete_funcionario", methods=['POST'])
@login_required
@gerente_required
def delete_func():
    conexao = None
    id_deletar = request.form.get('id_deletar')    

    if not id_deletar:
        return render_template(f"{pi}.html", erro="ID do funcionário para deleção não fornecido.")

    try:
        conexao = db_connection()
        cursor = conexao.cursor()

        sql_delete = "DELETE FROM funcionarios WHERE id_func = %s"
        cursor.execute(sql_delete, (id_deletar,))
        
        conexao.commit()
        
        if cursor.rowcount > 0:
            return redirect(f"/listar_func") 
        else:
            return render_template(f"{pi}.html", erro="Funcionário não encontrado ou deleção falhou.")

    except mysql.connector.Error as err:
        print(f"Erro ao deletar funcionário: {err}")
        conexao.rollback()
        return render_template(f"{pi}.html", erro=f"Erro no banco de dados: Não foi possível deletar o funcionário, verifique se há registros de serviço associados.") 
    
    finally:
        if conexao and conexao.is_connected():
            cursor.close()
            conexao.close()



"""
<-------- Area De Estoque -------->
"""

#pagina para cadastrar peças
@app.route("/cadastro_peca", methods=['GET', 'POST'])
@login_required
def cadastro_peca():
    conexao = None
    if request.method == 'POST':
        nome_peca = request.form['nome_peca']     
        lote = request.form['lote']        
        validade = request.form['validade'] 
        fornecedor = request.form['fornecedor']
        quant_peca = request.form['quant_peca']
        min_peca = request.form['min']
        max_peca = request.form['max']
        
        dados_peca = (nome_peca, lote, validade, fornecedor, quant_peca, min_peca, max_peca)

        try:
            conexao = db_connection()
            cursor = conexao.cursor()
            
            sql_insert = "INSERT INTO estoque (nome_peca, lote, validade, fornecedor, quant_peca, min, max) VALUES (%s, %s, %s, %s, %s, %s, %s)" 
            cursor.execute(sql_insert, dados_peca)
            
            conexao.commit()
            
            return redirect(f"/listar_estoque")

        except mysql.connector.Error as err:
            print(f"Erro ao salvar peça: {err}")
            conexao.rollback()
            return render_template("cadastro_peca.html", erro=f"Erro no banco de dados: {err.msg}") 
    
        finally:
            if conexao and conexao.is_connected():
                cursor.close()
                conexao.close()
    return render_template("cadastro_peca.html")



#pagina para listar estoque
@app.route("/listar_estoque")
@login_required
def listar_estoque():
    conn = None
    pecas = []
    try:
        # 1. Estabelecer conexão com o DB
        conn = db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 2. Query para selecionar todos os itens do estoque
        query = "SELECT id_peca, nome_peca, lote, validade, fornecedor, quant_peca FROM estoque"
        cursor.execute(query)
        
        # 3. Armazenar os resultados
        pecas = cursor.fetchall()
        
    except mysql.connector.Error as err:
        print(f"Erro ao listar estoque: {err}")
        return render_template(f"{pi}.html", erro="Erro ao carregar o estoque.")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

    # 4. Redirecionar para uma nova página de visualização do estoque (que precisa ser criada)
    return render_template(f"listar_estoque.html", pecas=pecas)



#pagina para editar peças
# func.py (Trecho corrigido da rota editar_peca)

@app.route("/editar_peca/<int:id_peca_original>", methods=['GET', 'POST'])
@login_required
def editar_peca(id_peca_original):
    conexao = None
    
    try:
        conexao = db_connection()
        cursor = conexao.cursor()

        if request.method == 'POST':
            
            # Pega a confirmação (se não vier, assume 'false')
            confirmacao = request.form.get('confirmacao', 'false')

            try:
                nome_peca = request.form['nome_peca']     
                lote = request.form['lote']        
                validade = request.form['validade'] 
                fornecedor = request.form['fornecedor']
                quant_peca = int(request.form['quant_peca'])
                min_peca = int(request.form['min'])
                max_peca = int(request.form['max'])
                id_peca = int(request.form['id_peca_editar'])

            except ValueError:
                return render_template(f"{pi}.html", erro="Erro: Valores numéricos inválidos.") 

            # LÓGICA DE VALIDAÇÃO DO ESTOQUE
            # Se estiver fora dos limites E a confirmação ainda for falsa
            if (quant_peca < min_peca or quant_peca > max_peca) and confirmacao == 'false':
                
                # Monta um dicionário com os dados atuais para não perder o que o usuário digitou
                peca_dados = request.form.to_dict()
                
                # CORREÇÃO IMPORTANTE: 
                # O template usa {{ peca.id_peca }} na tag <form action...>.
                # O form envia 'id_peca_editar'. Precisamos mapear um no outro.
                peca_dados['id_peca'] = id_peca 
                
                return render_template("editar_peca.html", 
                                       aviso_estoque=True, # Flag para o HTML
                                       peca=peca_dados,
                                       erro="ATENÇÃO: A quantidade está fora dos limites MÍN/MÁX. Clique em SALVAR novamente para confirmar.")

            # Se chegou aqui, ou está dentro dos limites ou o usuário confirmou (confirmacao='true')
            sql_update = "UPDATE estoque SET nome_peca = %s, lote = %s, validade = %s, fornecedor = %s, quant_peca = %s, min = %s, max = %s WHERE id_peca = %s"
            dados_peca = (nome_peca, lote, validade, fornecedor, quant_peca, min_peca, max_peca, id_peca)

            cursor.execute(sql_update, dados_peca)
            conexao.commit()

            return redirect("/listar_estoque") 

        else:
            # --- FASE GET (Manteve igual) ---
            sql_select = "SELECT id_peca, nome_peca, lote, validade, fornecedor, quant_peca, min, max FROM estoque WHERE id_peca = %s"
            cursor.execute(sql_select, (id_peca_original,))
            peca_data = cursor.fetchone()
        
            if peca_data is None:
                return render_template(f"{pi}.html", erro=f"Peça com ID {id_peca_original} não encontrada.")

            peca = {
                'id_peca': peca_data[0],
                'nome_peca': peca_data[1],
                'lote': peca_data[2],
                'validade': peca_data[3],
                'fornecedor': peca_data[4],
                'quant_peca': peca_data[5],
                'min': peca_data[6],
                'max': peca_data[7]
            }
            
            return render_template("editar_peca.html", peca=peca) 

    except mysql.connector.Error as err:
        print(f"Erro ao editar peça: {err}")
        if conexao:
            conexao.rollback()
        return render_template(f"{pi}.html", erro=f"Erro no banco de dados.") 
    
    finally:
        if conexao and conexao.is_connected():
            cursor.close()
            conexao.close()



#pagina para deletar peças
@app.route("/delete_peca", methods=['POST'])
@login_required
def delete_peca():
    conexao = None
    id_deletar = request.form.get('id_deletar')    

    if not id_deletar:
        return render_template(f"{pi}.html", erro="ID da peça para deleção não fornecido.")

    try:
        conexao = db_connection()
        cursor = conexao.cursor()

        sql_delete = "DELETE FROM estoque WHERE id_peca = %s"
        cursor.execute(sql_delete, (id_deletar,))
        
        conexao.commit()
        
        if cursor.rowcount > 0:
            return redirect(f"/listar_estoque") 
        else:
            return render_template(f"{pi}.html", erro="Peça não encontrada ou deleção falhou.")

    except mysql.connector.Error as err:
        print(f"Erro ao deletar peça: {err}")
        conexao.rollback()
        return render_template(f"{pi}.html", erro=f"Erro no banco de dados: Não foi possível deletar a peça, verifique se há registros associados.") 
    
    finally:
        if conexao and conexao.is_connected():
            cursor.close()
            conexao.close()



"""
--------Registro de serviços--------
"""


# Certifique-se de que a função 'cargos' é usada aqui para verificar a permissão
from datetime import datetime # Adicione isso no topo do func.py se não houver

@app.route("/cadastro_registro_servico", methods=['GET', 'POST'])
@login_required
def cadastro_registro_servico():
    conexao = None
    cursor = None
    pecas_disponiveis = []

    # --- 1. Buscar peças disponíveis para preencher o <select> no HTML (GET e erro no POST) ---
    try:
        conexao = db_connection()
        cursor = conexao.cursor(dictionary=True)
        # Busca apenas peças com estoque positivo
        cursor.execute("SELECT id_peca, nome_peca, lote, quant_peca FROM estoque WHERE quant_peca > 0")
        pecas_disponiveis = cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Erro ao buscar peças: {err}")
    finally:
        if cursor: cursor.close()
        if conexao and conexao.is_connected(): conexao.close()

    # --- 2. Processar o Formulário (POST) ---
    if request.method == 'POST':
        try:
            conexao = db_connection()
            conexao.start_transaction() # Inicia transação para garantir integridade
            cursor = conexao.cursor(dictionary=True)

            # Coletar dados simples
            cpf_cliente = request.form.get('cpf_cliente')
            diagnostico = request.form.get('diagnostico')
            prazo = request.form.get('prazo')
            realizacao = request.form.get('realizacao')
            
            # Coletar e tratar valores monetários (trocando vírgula por ponto se necessário)
            valor_pecas = float(request.form.get('valor_pecas', 0))
            valor_servico = float(request.form.get('valor_servico', 0))
            valor_total = valor_pecas + valor_servico # Recalcula no back-end por segurança

            # Coletar listas de peças (arrays do HTML)
            pecas_ids = request.form.getlist('peca_id[]')
            quantidades = request.form.getlist('quantidade[]')
            
            # Pega o ID do funcionário logado na sessão
            func_id = session.get('user_id')

            # --- Validação 1: Verificar se o Cliente existe ---
            cursor.execute("SELECT id_cliente, placa_carro FROM clientes WHERE cpf = %s", (cpf_cliente,))
            cliente_data = cursor.fetchone()
            
            if not cliente_data:
                # Se não achar cliente, faz rollback (cancela) e avisa
                conexao.rollback()
                return render_template("cadastro_registro_servico.html", 
                                     erro="Cliente não encontrado com este CPF. Cadastre o cliente primeiro.", 
                                     pecas_disponiveis=pecas_disponiveis)
            
            id_cliente = cliente_data['id_cliente']
            placa_carro = cliente_data['placa_carro']

            # --- Validação 2: Verificar Estoque (Antes de salvar qualquer coisa) ---
            # Cria uma lista de tuplas (id_peca, quantidade) para processar
            itens_para_salvar = []
            for i in range(len(pecas_ids)):
                p_id = int(pecas_ids[i])
                p_qtd = int(quantidades[i])
                
                # Verifica quantidade atual no banco
                cursor.execute("SELECT quant_peca, nome_peca FROM estoque WHERE id_peca = %s", (p_id,))
                peca_estoque = cursor.fetchone()
                
                if not peca_estoque or peca_estoque['quant_peca'] < p_qtd:
                    conexao.rollback()
                    nome = peca_estoque['nome_peca'] if peca_estoque else "Desconhecida"
                    return render_template("cadastro_registro_servico.html", 
                                         erro=f"Estoque insuficiente para a peça '{nome}'. Disponível: {peca_estoque['quant_peca']}", 
                                         pecas_disponiveis=pecas_disponiveis)
                
                itens_para_salvar.append((p_id, p_qtd))

            # --- Passo 3: Inserir o Registro do Serviço ---
            sql_registro = """
                INSERT INTO registro_servico 
                (diagnostico, func_id, prazo, realizacao, cliente, placa, valor_peca, valor_servico, valor_total) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            valores_registro = (diagnostico, func_id, prazo, realizacao, id_cliente, placa_carro, valor_pecas, valor_servico, valor_total)
            cursor.execute(sql_registro, valores_registro)
            
            # Recupera o ID do serviço que acabou de ser criado
            id_registro_novo = cursor.lastrowid

            # --- Passo 4: Inserir na Tabela de Associação (servico_pecas) e Baixar Estoque ---
            sql_insert_item = "INSERT INTO servico_pecas (id_registro, id_peca_estoque, quantidade_usada) VALUES (%s, %s, %s)"
            sql_update_estoque = "UPDATE estoque SET quant_peca = quant_peca - %s WHERE id_peca = %s"

            for p_id, p_qtd in itens_para_salvar:
                # 1. Cria o vinculo na tabela servico_pecas
                cursor.execute(sql_insert_item, (id_registro_novo, p_id, p_qtd))
                
                # 2. Subtrai do estoque
                cursor.execute(sql_update_estoque, (p_qtd, p_id))

            # Se tudo deu certo, confirma as alterações no banco
            conexao.commit()
            return redirect(url_for('listar_registro_servico'))

        except mysql.connector.Error as err:
            if conexao: conexao.rollback() # Desfaz tudo se der erro
            print(f"Erro no cadastro de serviço: {err}")
            return render_template("cadastro_registro_servico.html", 
                                 erro=f"Erro ao salvar serviço: {err}", 
                                 pecas_disponiveis=pecas_disponiveis)
        finally:
            if cursor: cursor.close()
            if conexao and conexao.is_connected(): conexao.close()

    # --- Renderização Inicial (GET) ---
    return render_template("cadastro_registro_servico.html", pecas_disponiveis=pecas_disponiveis)


@app.route("/listar_registro_servico")
@login_required
def listar_registro_servico():
    conn = None
    registros = []
    try:
        # 1. Estabelecer conexão com o DB
        conn = db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 2. Query corrigida:
        # - Usa GROUP_CONCAT para pegar todas as peças e quantidades e transformar em texto
        # - Usa LEFT JOIN para não sumir com o serviço se não tiver peças
        query = """
        SELECT 
            rs.id_reg, 
            rs.diagnostico, 
            rs.prazo, 
            rs.placa, 
            c.nome_cliente, 
            -- Cria uma string ex: "Oleo (2), Filtro (1)"
            GROUP_CONCAT(CONCAT(e.nome_peca, ' (', sp.quantidade_usada, ')') SEPARATOR ', ') as lista_pecas
        FROM registro_servico rs
        JOIN clientes c ON rs.cliente = c.id_cliente
        LEFT JOIN servico_pecas sp ON rs.id_reg = sp.id_registro
        LEFT JOIN estoque e ON sp.id_peca_estoque = e.id_peca
        GROUP BY rs.id_reg, rs.diagnostico, rs.prazo, rs.placa, c.nome_cliente
        ORDER BY rs.id_reg DESC
        """
        cursor.execute(query)
        
        # 3. Armazenar os resultados
        registros = cursor.fetchall()
        
    except mysql.connector.Error as err:
        print(f"Erro ao listar os registros: {err}")
        return render_template("listar_registro_servico.html", erro="Erro ao carregar os registros.")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

    return render_template("listar_registro_servico.html", registros=registros)

#pagina para editar os registros
@app.route("/editar_registro_servico/<int:id_reg_original>", methods=['GET', 'POST'])
@login_required
def editar_registro_servico(id_reg_original):
    # A EDIÇÃO DE REGISTROS É COMPLEXA POIS EXIGE REVERSÃO DE ESTOQUE
    # Esta versão usa a lógica de ajuste por DELTA (diferença) para atualizar o estoque.

    conexao = None
    cursor = None
    
    try:
        conexao = db_connection()
        # ESSENCIAL: Usar dictionary=True para o POST funcionar, pois ele acessa campos por nome.
        cursor = conexao.cursor(dictionary=True)

        if request.method == 'POST':
            # --- LÓGICA POST (AJUSTE DE ESTOQUE POR DELTA) ---
            
            # CAMPOS PRINCIPAIS (Editáveis)
            diagnostico = request.form['diagnostico']
            func_id     = session.get('user_id') 
            prazo       = request.form['prazo'] 
            realizacao  = request.form['realizacao']
            cpf_cliente = request.form['cpf_cliente']
            id_reg      = request.form['id_reg_editar'] 
            
            # 1. Coletar dados do formulário (Novos)
            pecas_ids_novas = request.form.getlist('peca_id[]')
            # Garante que só peças com quantidade > 0 sejam consideradas
            quantidades_novas = [int(q) for q in request.form.getlist('quantidade[]') if q.isdigit() and int(q) > 0]
            
            # Mapeia as novas peças: {id_peca: quantidade}
            novas_pecas_map = dict(zip(pecas_ids_novas, quantidades_novas))
            
            # 2. Buscar Cliente/Carro e Peças Atuais no DB
            sql_cliente_carro = "SELECT id_cliente, placa_carro FROM clientes WHERE cpf = %s"
            cursor.execute(sql_cliente_carro, (cpf_cliente,))
            cliente_data = cursor.fetchone()
            
            if not cliente_data:
                # Retorna erro e repassa o id original para a URL de edição
                flash("Cliente com este CPF não encontrado!", "erro")
                return redirect(url_for('editar_registro_servico', id_reg_original=id_reg_original))

            cliente_id = cliente_data['id_cliente']
            placa_carro = cliente_data['placa_carro']
            
            sql_pecas_originais = "SELECT id_peca_estoque, quantidade_usada FROM servico_pecas WHERE id_registro = %s"
            cursor.execute(sql_pecas_originais, (id_reg,))
            pecas_originais_db = cursor.fetchall()
            
            # Mapeia as peças atuais: {id_peca (str): quantidade (int)}
            pecas_atuais_map = {str(p['id_peca_estoque']): p['quantidade_usada'] for p in pecas_originais_db}
            
            # Conjunto de todos os IDs de peças envolvidas (antigas e novas)
            todos_pecas_ids = set(pecas_atuais_map.keys()) | set(novas_pecas_map.keys())
            
            # 3. CALCULAR DELTA E ATUALIZAR ESTOQUE/SERVICO_PECAS
            
            # %s pode ser positivo (devolver peça) ou negativo (retirar peça)
            sql_update_estoque = "UPDATE estoque SET quant_peca = quant_peca + %s WHERE id_peca = %s" 
            
            for peca_id in todos_pecas_ids:
                # O get() garante que se a peça não existir no mapa, o valor é 0
                quant_atual = pecas_atuais_map.get(peca_id, 0)
                quant_nova = novas_pecas_map.get(peca_id, 0)
                
                # delta_estoque é a quantidade que precisa ser *adicionada* ao estoque.
                # Exemplo: Atual=5, Nova=3 -> delta=2 (Devolver 2 peças)
                # Exemplo: Atual=5, Nova=7 -> delta=-2 (Retirar 2 peças)
                delta_estoque = quant_atual - quant_nova 
                
                if delta_estoque != 0:
                    # Aplica o ajuste no estoque.
                    cursor.execute(sql_update_estoque, (delta_estoque, peca_id))
                    
                if quant_nova > 0:
                    # Peça ainda está em uso (ou foi adicionada), então atualiza/insere
                    if peca_id in pecas_atuais_map:
                        # Atualizar quantidade da peça na tabela de relacionamento
                        sql_update_rel = "UPDATE servico_pecas SET quantidade_usada = %s WHERE id_registro = %s AND id_peca_estoque = %s"
                        # É preciso usar o id_peca como inteiro aqui, se for a convenção do DB
                        cursor.execute(sql_update_rel, (quant_nova, id_reg, int(peca_id))) 
                    else:
                        # Inserir nova peça na tabela de relacionamento
                        sql_insert_rel = "INSERT INTO servico_pecas (id_registro, id_peca_estoque, quantidade_usada) VALUES (%s, %s, %s)"
                        cursor.execute(sql_insert_rel, (id_reg, int(peca_id), quant_nova))
                
                elif quant_nova == 0 and peca_id in pecas_atuais_map:
                    # A peça foi removida, deletar a relação
                    sql_delete_rel = "DELETE FROM servico_pecas WHERE id_registro = %s AND id_peca_estoque = %s"
                    cursor.execute(sql_delete_rel, (id_reg, int(peca_id)))
            
            # 4. Atualizar registro principal (sem valores monetários)
            sql_update = """
            UPDATE registro_servico SET 
            diagnostico = %s, func_id = %s, prazo = %s, 
            realizacao = %s, cliente = %s, placa = %s 
            WHERE id_reg = %s
            """
            dados_reg = (diagnostico, func_id, prazo, realizacao, cliente_id, placa_carro, id_reg)
            # cursor.execute exige que todos os dados sejam passados na ordem correta
            cursor.execute(sql_update, dados_reg) 
            
            conexao.commit()
            flash("Registro de serviço e estoque atualizados com sucesso!", "sucesso")
            return redirect(url_for('listar_registro_servico'))

        else:
            # --- FASE GET (BUSCAR DADOS) ---
            # O cursor deve ser mantido como dictionary=True para o GET funcionar corretamente.
            
            # 1. Buscar Dados do Registro Principal (incluindo valores para readonly)
            sql_select = """
            SELECT 
                rs.id_reg, rs.diagnostico, rs.prazo, rs.realizacao, rs.func_id, rs.placa,
                c.cpf AS cpf_cliente, rs.valor_servico, rs.valor_pecas, rs.valor_total
            FROM registro_servico rs
            JOIN clientes c ON rs.cliente = c.id_cliente
            WHERE rs.id_reg = %s
            """
            cursor.execute(sql_select, (id_reg_original,))
            reg_data = cursor.fetchone() # Retorna dicionário (dictionary=True)
            
            if reg_data is None:
                flash(f"Registro com ID {id_reg_original} não encontrado.", "erro")
                # Assumindo que 'pagi' é a rota inicial segura
                return redirect(url_for('pagi'))
            
            # Formatação de datas para input type="datetime-local"
            prazo_formatado = reg_data['prazo'].strftime('%Y-%m-%dT%H:%M') if reg_data['prazo'] else ''
            realizacao_formatada = reg_data['realizacao'].strftime('%Y-%m-%dT%H:%M') if reg_data['realizacao'] else ''

            registro = {
                'id_reg': reg_data['id_reg'],
                'diagnostico': reg_data['diagnostico'],
                'prazo': prazo_formatado,
                'realizacao': realizacao_formatada,
                'cpf_cliente': reg_data['cpf_cliente'],
                'placa': reg_data['placa'],
                # Valores monetários (para serem exibidos como readonly no template)
                'valor_servico': reg_data['valor_servico'],
                'valor_pecas': reg_data['valor_pecas'],
                'valor_total': reg_data['valor_total']
            }
            
            # 2. Buscar Peças Usadas (Para repopular a tabela dinâmica de edição)
            sql_pecas_usadas = """
            SELECT sp.id_peca_estoque, sp.quantidade_usada, e.nome_peca, e.quant_peca AS estoque_atual
            FROM servico_pecas sp
            JOIN estoque e ON sp.id_peca_estoque = e.id_peca
            WHERE sp.id_registro = %s
            """
            cursor.execute(sql_pecas_usadas, (id_reg_original,))
            # Usando 'pecas_usadas_completas' para ser mais claro no template
            registro['pecas_usadas_completas'] = cursor.fetchall() 
            
            # 3. Buscar todas as peças disponíveis para o dropdown de adição
            sql_pecas_disponiveis = "SELECT id_peca, nome_peca, quant_peca FROM estoque ORDER BY nome_peca"
            cursor.execute(sql_pecas_disponiveis)
            pecas_disponiveis = cursor.fetchall()
            
            return render_template("editar_registro_servico.html", 
                                registro=registro, 
                                pecas_disponiveis=pecas_disponiveis) 

    except mysql.connector.Error as err:
        print(f"Erro ao editar registro: {err}")
        if conexao:
            conexao.rollback()
        # Retorna para a página de listagem em caso de erro no DB
        flash(f"Erro no banco de dados: Não foi possível editar o registro. Detalhe: {err.msg}", "erro")
        return redirect(url_for('listar_registro_servico'))
    
    finally:
        if cursor: cursor.close()
        if conexao and conexao.is_connected():
            conexao.close()


#pagina para deletar os registros (e reverter o estoque)
@app.route("/delete_registro_servico", methods=['POST'])
@login_required
def delete_registro_servico():
    conexao = None
    id_deletar = request.form.get('id_deletar')    

    if not id_deletar:
        return redirect(url_for('listar_registro_servico', erro="ID do registro para deleção não fornecido."))

    try:
        conexao = db_connection()
        cursor = conexao.cursor()

        # 1. Recuperar peças e quantidades para reverter o estoque
        sql_pecas_usadas = "SELECT id_peca_estoque, quantidade_usada FROM servico_pecas WHERE id_registro = %s"
        cursor.execute(sql_pecas_usadas, (id_deletar,))
        pecas_para_reverter = cursor.fetchall()
        
        # 2. Reverter o estoque (adicionar as peças de volta)
        for id_peca, quantidade in pecas_para_reverter:
            sql_reverter_estoque = "UPDATE estoque SET quant_peca = quant_peca + %s WHERE id_peca = %s"
            cursor.execute(sql_reverter_estoque, (quantidade, id_peca))
        
        # 3. Deletar os registros de uso da peça (opcional, devido a ON DELETE CASCADE)
        sql_delete_pecas = "DELETE FROM servico_pecas WHERE id_registro = %s"
        cursor.execute(sql_delete_pecas, (id_deletar,))

        # 4. Deletar o registro de serviço principal
        sql_delete_reg = "DELETE FROM registro_servico WHERE id_reg = %s"
        cursor.execute(sql_delete_reg, (id_deletar,))
        
        conexao.commit()
        
        if cursor.rowcount > 0:
            return redirect(f"/listar_registro_servico") 
        else:
            conexao.rollback()
            return redirect(url_for('listar_registro_servico', erro="Registro não encontrado ou deleção falhou."))


    except mysql.connector.Error as err:
        print(f"Erro ao deletar registro: {err}")
        conexao.rollback()
        return redirect(url_for('listar_registro_servico', erro=f"Erro no banco de dados: Não foi possível deletar o registro. Detalhe: {err.msg}"))
    
    finally:
        if conexao and conexao.is_connected():
            cursor.close()
            conexao.close()