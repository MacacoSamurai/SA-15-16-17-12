
from flask import Flask, render_template, request, redirect, url_for
from main import app, CONFIG_DB
from werkzeug.security import check_password_hash
import mysql.connector


DB_HOST = CONFIG_DB['host']
DB_USER = CONFIG_DB['user']
DB_PASSWORD = CONFIG_DB['password']
DB_NAME = CONFIG_DB['database'] 




@app.route("/")
def index():
    # Ação 2: Corrigido o endpoint de redirecionamento para o nome da função
    return redirect(url_for("login"))


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
                database=DB_NAME
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

#pagina inicial para a escolha das opções
@app.route("/pagina_inicial")
def pagina_inicial():
    return render_template("paginainicial.html")    


#pagina de salvar usuário
@app.route("/savecliente", methods=['GET', 'POST'])
def create_client():
    if request.method == 'POST':

        nome = request.form['nome_cliente']     
        cpf = request.form['cpf_cliente']        
        celular = request.form['celular_cliente'] 

        placa_carro = request.form['placa_carro']
        modelo = request.form['modelo_carro']
        fabricante = request.form['fabricante_carro']
        
        conexao = None
    try:
            conexao = mysql.connector.connect(
                host=DB_HOST,   
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME
            )
            cursor = conexao.cursor()

            # Ação 3: Uso de INSERT IGNORE para não falhar se a placa já existe
            sql_carros = "INSERT IGNORE INTO carros (placa_carro, modelo, fabricante) VALUES (%s, %s, %s)"
            dados_carros = (placa_carro, modelo, fabricante)
            cursor.execute(sql_carros, dados_carros)

            sql_clientes = "INSERT INTO clientes (nome_cliente, cpf, celular, placa_carro) VALUES (%s, %s, %s, %s)" 
            dados_clientes = (nome, cpf, celular, placa_carro)
            cursor.execute(sql_clientes, dados_clientes)
            
            conexao.commit()
            
            # Redireciona para a página inicial (ou para uma página de sucesso)
            return redirect(url_for("pagina_inicial"))

    except mysql.connector.Error as err:
            print(f"Erro ao salvar cliente: {err}")
            # Em caso de erro, você pode redirecionar ou renderizar a página com uma mensagem
            return render_template("paginainicial.html", erro="Erro ao salvar dados do cliente.")
    finally:
            if conexao and conexao.is_connected():
                cursor.close()
                conexao.close()
                
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



