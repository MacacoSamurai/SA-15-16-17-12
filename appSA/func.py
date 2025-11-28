
from flask import Flask, render_template, request, redirect, url_for
from main import app, CONFIG_DB
from werkzeug.security import check_password_hash, generate_password_hash
import mysql.connector
pi = str ("pagi")
lg = str ("login")

DB_HOST = CONFIG_DB['host']
DB_USER = CONFIG_DB['user']
DB_PASSWORD = CONFIG_DB['password']
DB_NAME = CONFIG_DB['database'] 
DB_PORT = CONFIG_DB['port'] 



#pagina principal
@app.route("/")
def index():
    # Ação 2: Corrigido o endpoint de redirecionamento para o nome da função
    return redirect(url_for(f"login"))




#pagina inicial para a escolha das opções
@app.route(f"/{pi}")
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
            conexao = mysql.connector.connect(
                host=DB_HOST,   
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                port=DB_PORT
            )
            cursor = conexao.cursor(dictionary=True)

            query = "SELECT senha_user FROM funcionarios WHERE login_user = %s"
            cursor.execute(query, (login_user,))

            funcionario = cursor.fetchone()

            if funcionario:
                senha_hash_armazenada = funcionario['senha_user']
                
                # Verifica se a senha é um hash (começa com 'pbkdf2:sha256')
                if check_password_hash(senha_hash_armazenada, senha_user):
                    # Se o hash for válido
                    return redirect(url_for('pagi'))
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



"""
<-------- Area De Clientes -------->
"""

#pagina de salvar cliente
@app.route("/cadastro_cliente", methods=['GET', 'POST'])
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
            conexao = mysql.connector.connect(
                host=DB_HOST,   
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                port=DB_PORT
            )
            cursor = conexao.cursor()
            
            sql_verify_cliente = "SELECT id_cliente FROM clientes WHERE cpf = %s OR placa_carro = %s"


            cursor.execute(sql_verify_cliente, (cpf, placa_carro))
            cliente_existente = cursor.fetchone()

            if cliente_existente:
                 return render_template(f"{pi}.html", erro="Cliente com este CPF ou Placa já cadastrado!")

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
def editar_cliente(cpf_original):
    conexao = None
    cursor = None

    try:
        conexao = mysql.connector.connect(
            host=DB_HOST,   
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT
        )
        cursor = conexao.cursor()

        if request.method == 'POST':

            nome = request.form['nome_cliente']     
            cpf_novo = request.form['cpf_cliente']        
            celular = request.form['celular_cliente'] 

            placa_carro_nova = request.form['placa_carro']
            modelo = request.form['modelo_carro']
            fabricante = request.form['fabricante_carro']

            cpf_original = request.form['cpf_oroginal']


            sql_placaCPF = "SELECT placa_carro FROM clientes WHERE cpf = (%s)"

            cursor.execute(sql_placaCPF, (cpf_original,))
            placa_original_data = cursor.fetchone()
        
            if placa_original_data is None:
                return render_template(f"{pi}.html", erro=f"Cliente com CPF {cpf_original} não encontrado.")

            placa_original = placa_original_data[0]

        
            sql_update_cliente = "UPDATE clientes set nome = %s, cpf = %s, celular = %s, placa_carro = %s WHERE placa_carro = %s"
            dados_clientes = (nome, cpf_novo, celular, placa_carro_nova, placa_original)
            cursor.execute(sql_update_cliente, dados_clientes,)
        
            # 2. Deletar da tabela `carros`
            sql_update_carro = "UPDATE carros set placa_carro = %s, modelo = %s, fabricante = %s WHERE placa_carro = %s"
            dados_carros = (placa_carro_nova, modelo, fabricante, placa_original)
            cursor.execute(sql_update_carro, dados_carros,)
        
            conexao.commit()

            return redirect(f"{pi}")

        else:
            # --- 🔍 FASE GET: Buscar dados para pré-preencher o formulário ---
            
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
        return render_template("pagina_de_clientes.html", erro=f"Erro no banco de dados: Não foi possível editar o cliente. Detalhe: {err}")
    
    finally:
        if conexao :
            cursor.close()
        if conexao and conexao.is_connected():
            conexao.close()



#pagina de listar clientes
@app.route("/listar_clientes")
def listar_clientes():
    conn = None
    clientes = []
    try:
        # 1. Estabelecer conexão com o DB
        conn = mysql.connector.connect(
            host=DB_HOST,   
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = conn.cursor(dictionary=True)
        
        # 2. Query para selecionar todos os itens do estoque
        query = """
        SELECT c.nome_cliente, c.cpf, c.celular, ca.placa_carro, ca.modelo, ca.fabricante 
        FROM clientes c
        JOIN carros ca ON c.placa_carro = ca.placa_carro
        """
        cursor.execute(query)

        clientes = cursor.fetchall()

    except mysql.connector.Error as err:
        print(f"Erro ao listar estoque: {err}")
        return render_template(f"{pi}.html", erro="Erro ao carregar o estoque.")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

    # 4. Redirecionar para uma nova página de visualização do estoque (que precisa ser criada)
    return render_template("listarclientes.html", clientes=clientes)



#pagina de deletar clientes
@app.route("/delete_cliente", methods=['POST'])
def delete_cliente():
    conexao = None
    

    cpf_deletar = request.form['cpf_deletar']    

    if not cpf_deletar:
        return render_template(f"{pi}.html", erro="CPF para deleção não fornecido.")

    try:
        conexao = mysql.connector.connect(
            host=DB_HOST,   
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT
        )
        cursor = conexao.cursor()

        sql_placaCPF = "SELECT placa_carro FROM clientes WHERE cpf = (%s)"

        cursor.execute(sql_placaCPF, (cpf_deletar,))
        resultado = cursor.fetchone()
        
        if resultado is None:
            return render_template(f"{pi}.html", erro=f"Cliente com CPF {cpf_deletar} não encontrado.")

        placa = resultado[0]

        sql_delete_registros = "DELETE FROM registro_servico WHERE placa = %s"
        cursor.execute(sql_delete_registros, (placa,))

        # 1. Deletar da tabela `clientes` (referência ao carro)
        # Se houver registros em `registro_servico` para este cliente/carro, 
        # a deleção falhará a menos que você as exclua primeiro ou configure ON DELETE CASCADE.
        sql_delete_cliente = "DELETE FROM clientes WHERE placa_carro = %s"
        cursor.execute(sql_delete_cliente, (placa,))
        
        # 2. Deletar da tabela `carros`
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
        return render_template(f"{pi}", erro=f"Erro no banco de dados: Não foi possível deletar o cliente, verifique se há registros de serviço associados.") 
    
    finally:
        if conexao and conexao.is_connected():
            cursor.close()
            conexao.close()



"""
<-------- Area De Funcionários -------->
"""

#pagina para cadastrar funcionários
@app.route("/cadastro_funcionario", methods=['GET', 'POST'])
def create_funcionario():
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
            conexao = mysql.connector.connect(
                host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
                database=DB_NAME, port=DB_PORT
            )
            cursor = conexao.cursor()
            
            sql_verify = "SELECT id_func FROM funcionarios WHERE login_user = %s OR cpf = %s"
            cursor.execute(sql_verify, (login_user, cpf))
            funcionario_existente = cursor.fetchone()

            if funcionario_existente:
                 return render_template("cadastro_funcionario.html", erro="Funcionário com este Login ou CPF já cadastrado!")

            sql_insert = "INSERT INTO funcionarios (nome_func, login_user, senha_user, cargo, cpf) VALUES (%s, %s, %s, %s, %s)" 
            cursor.execute(sql_insert, dados_funcionario)
            
            conexao.commit()
            
            return redirect(f"/{pi}")

        except mysql.connector.Error as err:
            print(f"Erro ao salvar funcionário: {err}")
            conexao.rollback()
            return render_template("cadastro_funcionario.html", erro=f"Erro no banco de dados: {err.msg}") 
    
        finally:
            if conexao and conexao.is_connected():
                cursor.close()
                conexao.close()
    return render_template("cadastro_funcionario.html")



#pagina para listar funcionários
@app.route("/listarfuncionarios")
def listar_funcionarios():
    conn = None
    funcionarios = []
    try:
        conn = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
            database=DB_NAME, port=DB_PORT
        )
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

    return render_template("listarfuncionarios.html", funcionarios=funcionarios)



#pagina para editar funcionários
@app.route("/editar_funcionario/<int:id_func_original>", methods=['GET', 'POST'])
def update_funcionario(id_func_original):
    conexao = None
    
    try:
        conexao = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
            database=DB_NAME, port=DB_PORT
        )
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
                 sql_update = "UPDATE funcionarios SET nome_func = %s, login_user = %s, senha_user = %s, cargo = %s, cpf = %s WHERE id_func = %s"
                 dados_func = (nome, login_user, senha_user, cargo, cpf, id_func)

            cursor.execute(sql_update, dados_func)
            conexao.commit()

            if cursor.rowcount > 0:
                return redirect(f"/listarfuncionarios") 
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
            
            return render_template("editar_funcionario.html", funcionario=funcionario) 

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
def delete_funcionario():
    conexao = None
    id_deletar = request.form.get('id_deletar')    

    if not id_deletar:
        return render_template(f"{pi}.html", erro="ID do funcionário para deleção não fornecido.")

    try:
        conexao = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
            database=DB_NAME, port=DB_PORT
        )
        cursor = conexao.cursor()

        sql_delete = "DELETE FROM funcionarios WHERE id_func = %s"
        cursor.execute(sql_delete, (id_deletar,))
        
        conexao.commit()
        
        if cursor.rowcount > 0:
            return redirect(f"/listarfuncionarios") 
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
def create_peca():
    conexao = None
    if request.method == 'POST':
        nome_peca = request.form['nome_peca']     
        lote = request.form['lote']        
        validade = request.form['validade'] 
        fornecedor = request.form['fornecedor']
        quant_peca = request.form['quant_peca']
        
        dados_peca = (nome_peca, lote, validade, fornecedor, quant_peca)

        try:
            conexao = mysql.connector.connect(
                host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
                database=DB_NAME, port=DB_PORT
            )
            cursor = conexao.cursor()
            
            sql_insert = "INSERT INTO estoque (nome_peca, lote, validade, fornecedor, quant_peca) VALUES (%s, %s, %s, %s, %s)" 
            cursor.execute(sql_insert, dados_peca)
            
            conexao.commit()
            
            return redirect(f"/listarestoque")

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
def listar_estoque():
    conn = None
    pecas = []
    try:
        # 1. Estabelecer conexão com o DB
        conn = mysql.connector.connect(
            host=DB_HOST,   
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = conn.cursor(dictionary=True)
        
        # 2. Query para selecionar todos os itens do estoque
        query = "SELECT nome_peca, lote, validade, fornecedor, quant_peca FROM estoque"
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
    return render_template(f"listarestoque.html", pecas=pecas)



#pagina para editar peças
@app.route("/editar_peca/<int:id_peca_original>", methods=['GET', 'POST'])
def update_peca(id_peca_original):
    conexao = None
    
    try:
        conexao = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
            database=DB_NAME, port=DB_PORT
        )
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

            if cursor.rowcount > 0:
                return redirect(f"/listarestoque") 
            else:
                return render_template(f"{pi}.html", erro="Peça não encontrada ou nenhum dado alterado.")

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
def delete_peca():
    conexao = None
    id_deletar = request.form.get('id_deletar')    

    if not id_deletar:
        return render_template(f"{pi}.html", erro="ID da peça para deleção não fornecido.")

    try:
        conexao = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
            database=DB_NAME, port=DB_PORT
        )
        cursor = conexao.cursor()

        sql_delete = "DELETE FROM estoque WHERE id_peca = %s"
        cursor.execute(sql_delete, (id_deletar,))
        
        conexao.commit()
        
        if cursor.rowcount > 0:
            return redirect(f"/listarestoque") 
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

