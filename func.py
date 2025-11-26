
from flask import Flask, render_template, request, redirect, url_for
from main import app, CONFIG_DB
from werkzeug.security import check_password_hash
import mysql.connector


DB_HOST = CONFIG_DB['host']
DB_USER = CONFIG_DB['user']
DB_PASSWORD = CONFIG_DB['password']
DB_NAME = CONFIG_DB['database'] 
DB_PORT = CONFIG_DB['port'] 




@app.route("/")
def index():
    # Ação 2: Corrigido o endpoint de redirecionamento para o nome da função
    return redirect(url_for("login"))





#pagina inicial para a escolha das opções
@app.route("/pagina_inicial")
def pagina_inicial():
    return render_template("listarclientes.html")  






@app.route("/login", methods=["GET", "POST"])
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

            usuario = cursor.fetchone()

            if usuario:
                senha_hash = usuario['senha_user']
                
                # Verifica se a senha é um hash (começa com 'pbkdf2:sha256')
                if senha_hash.startswith('pbkdf2:sha256'):
                    if check_password_hash(senha_hash, senha_user):
                        return redirect(url_for("pagina_inicial"))
                # Se não for hash, verifica a senha diretamente (MUITO INSEGURO, mas necessário para o seu dado '1324')
                elif senha_hash == senha_user:
                     return redirect(url_for("pagina_inicial"))

            return render_template("login.html", erro="Usuário ou senha incorretos!")

        except mysql.connector.Error as err:
            print(f"Erro no login: {err}")
            return render_template("login.html", erro="Erro interno do servidor.")
        finally:
            if conexao and conexao.is_connected():
                cursor.close()
                conexao.close()

    return render_template("login.html", erro="")  









#pagina de salvar cliente
@app.route("/savecliente", methods=['GET', 'POST'])
def create_client():
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
                 return render_template("paginainicial.html", erro="Cliente com este CPF ou Placa já cadastrado!")

            # Ação 3: Uso de INSERT IGNORE para não falhar se a placa já existe
            sql_carros = "INSERT IGNORE INTO carros (placa_carro, modelo, fabricante) VALUES (%s, %s, %s)"
            cursor.execute(sql_carros, dados_carros)

            sql_clientes = "INSERT INTO clientes (nome_cliente, cpf, celular, placa_carro) VALUES (%s, %s, %s, %s)" 
            cursor.execute(sql_clientes, dados_clientes)
            
            conexao.commit()
            
            # Redireciona para a página inicial (ou para uma página de sucesso)
            return redirect(url_for("pagina_inicial"))

        except mysql.connector.Error as err:
            print(f"Erro ao salvar cliente: {err}")
            conexao.rollback()
            return render_template("paginainicial.html", erro=f"Erro no banco de dados: {err.msg}") 
    
        finally:
            if conexao and conexao.is_connected():
                cursor.close()
                conexao.close()
    return render_template("paginainicial.html")                


#listar clientes
@app.route("/listarclientes")
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
        query = "SELECT nome_cliente, cpf, celular, placa_carro FROM clientes"
        cursor.execute(query)
        
        # 3. Armazenar os resultados
        clientes = cursor.fetchall()
        
    except mysql.connector.Error as err:
        print(f"Erro ao listar clientes: {err}")
        return render_template("paginainicial.html", erro="Erro ao carregar o clientes.")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

    # 4. Redirecionar para uma nova página de visualização do estoque (que precisa ser criada)
    return render_template("listarclientes.html", clientes=clientes)


#deletar clientes
@app.route("/deletecliente", methods=['POST'])
def delete_client():
    conexao = None
    

    cpf_deletar = request.form['cpf_deletar']    

    if not cpf_deletar:
        return render_template("paginainicial.html", erro="CPF para deleção não fornecido.")

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
            return render_template("login.html", erro=f"Cliente com CPF {cpf_deletar} não encontrado.")

        placa = resultado[0]

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
            return redirect(url_for("pagina_inicial")) # Redireciona para a página inicial
        else:
            return render_template("login.html", erro="Carro/Cliente não encontrado ou deleção falhou.")

    except mysql.connector.Error as err:
        print(f"Erro ao deletar cliente: {err}")
        conexao.rollback()
        return render_template("login.html", erro=f"Erro no banco de dados: Não foi possível deletar o cliente, verifique se há registros de serviço associados.") 
    
    finally:
        if conexao and conexao.is_connected():
            cursor.close()
            conexao.close()



#pagina para listar estoque
@app.route("/listarestoque")
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
        return render_template("paginainicial.html", erro="Erro ao carregar o estoque.")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

    # 4. Redirecionar para uma nova página de visualização do estoque (que precisa ser criada)
    return render_template("listarestoque.html", pecas=pecas)



