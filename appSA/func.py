
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
def index():
    # Ação 2: Corrigido o endpoint de redirecionamento para o nome da função
    return redirect(url_for(f"login"))



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

        placa_carro = request.form['placa_carro']
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
            return redirect(f"/{pi}")

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

        
            sql_update_cliente = "UPDATE clientes set nome = %s, cpf = %s, celular = %s, placa_carro = %s WHERE cpf_original = %s"
            dados_clientes = (nome, cpf_novo, celular, placa_carro_nova, cpf_original)
            cursor.execute(sql_update_cliente, dados_clientes,)
        
            # 2. Deletar da tabela `carros`
            sql_update_carro = "UPDATE carros set placa_carro = %s, modelo = %s, fabricante = %s WHERE placa_carro = %s"
            dados_carros = (placa_carro_nova, modelo, fabricante, placa_original)
            cursor.execute(sql_update_carro, dados_carros,)
        
            conexao.commit()

            return redirect(f"{pi}")

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
                return render_template("pagina_de_clientes.html", erro=f"Cliente com CPF {cpf_original} não encontrado para edição.")

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
            return redirect(f"/{pi}") # Redireciona para a página inicial
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
            
            return redirect(f"/{pi}")

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

            if cursor.rowcount > 0:
                return redirect(url_for('listar_func')) 
            else:
                return render_template(f"{pi}.html", erro="Funcionário não encontrado ou nenhum dado alterado.")

        else:
            # --- FASE GET: Buscar dados para pré-preencher o formulário ---
            sql_select = "SELECT id_func, nome_func, login_user, cargo, cpf FROM funcionarios WHERE id_func = %s"
            cursor.execute(sql_select, (id_func_original,))
            funcionario_data = cursor.fetchone()
        
            if funcionario_data is None:
                return render_template(f"{pi}.html", erro=f"Funcionário com ID {id_func_original} não encontrado.")

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
        
        dados_peca = (nome_peca, lote, validade, fornecedor, quant_peca)

        try:
            conexao = db_connection()
            cursor = conexao.cursor()
            
            sql_insert = "INSERT INTO estoque (nome_peca, lote, validade, fornecedor, quant_peca) VALUES (%s, %s, %s, %s, %s)" 
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
@app.route("/editar_peca/<int:id_peca_original>", methods=['GET', 'POST'])
@login_required
def editar_peca(id_peca_original):
    conexao = None
    
    try:
        conexao = db_connection()
        cursor = conexao.cursor()

        if request.method == 'POST':
            nome_peca = request.form['nome_peca']     
            lote = request.form['lote']        
            validade = request.form['validade'] 
            fornecedor = request.form['fornecedor']
            quant_peca = request.form['quant_peca']
            id_peca = request.form['id_peca_editar'] 

            sql_update = "UPDATE estoque SET nome_peca = %s, lote = %s, validade = %s, fornecedor = %s, quant_peca = %s WHERE id_peca = %s"
            dados_peca = (nome_peca, lote, validade, fornecedor, quant_peca, id_peca)

            cursor.execute(sql_update, dados_peca)
            conexao.commit()

            return redirect(f"/listar_estoque") 

        else:
            # --- FASE GET: Buscar dados para pré-preencher o formulário ---
            sql_select = "SELECT id_peca, nome_peca, lote, validade, fornecedor, quant_peca FROM estoque WHERE id_peca = %s"
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
                'quant_peca': peca_data[5]
            }
            
            return render_template("editar_peca.html", peca=peca) 

    except mysql.connector.Error as err:
        print(f"Erro ao editar peça: {err}")
        if conexao:
            conexao.rollback()
        return render_template(f"{pi}.html", erro=f"Erro no banco de dados: Não foi possível editar a peça.") 
    
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

@app.route("/registro_servico", methods=['GET', 'POST'])
@login_required
def registro_servico():
    conexao = None
    if request.method == 'POST':
        
        diagnostico = request.form['diagnostico']
        pecas_subs  = request.form['pecas_subs']
        func_id     = session.get('user_id') 
        prazo       = request.form['prazo'] # Recebido como string (e.g., 'YYYY-MM-DD HH:MM:SS')
        realizacao  = request.form['realizacao'] 

        
        cpf_cliente = request.form['cpf_cliente']
        
        
        valor_pecas = float(request.form.get('valor_pecas', 0.0))
        valor_servico = float(request.form.get('valor_servico', 0.0))
        
        valor_total = valor_pecas + valor_servico

        try:
            conexao = db_connection()
            cursor = conexao.cursor()

            
            sql_cliente_carro = "SELECT id_cliente, placa_carro FROM clientes WHERE cpf = %s"
            cursor.execute(sql_cliente_carro, (cpf_cliente,))
            cliente_data = cursor.fetchone()

            if not cliente_data:
                 return render_template("registro_servico.html", erro="Cliente com este CPF não encontrado!")

            cliente_id = cliente_data[0]
            placa_carro = cliente_data[1]


            sql_insert = """
            INSERT INTO registro_servico 
            (diagnostico, pecas_subs, func_id, prazo, realizacao, cliente, placa) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """ 
            dados_servico = (diagnostico, pecas_subs, func_id, prazo, realizacao, cliente_id, placa_carro)
            cursor.execute(sql_insert, dados_servico)
            
            conexao.commit()
            
            return redirect(url_for('pagi', sucesso=f"Serviço registrado com sucesso! Valor Total (Mão de Obra + Peças): R$ {valor_total:.2f}"))

        except mysql.connector.Error as err:
            print(f"Erro ao registrar serviço: {err}")
            conexao.rollback()
            return render_template("registro_servico.html", erro=f"Erro no banco de dados: {err.msg}") 
    
        finally:
            if conexao and conexao.is_connected():
                cursor.close()
                conexao.close()

    # FASE GET: Exibir o formulário
    return render_template("registro_servico.html")
    