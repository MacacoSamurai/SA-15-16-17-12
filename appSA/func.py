
from flask import Flask, render_template, request
from main import app

@app.route("/", methods=['GET', 'POST'])
def htmlSA():
    if request.method == 'POST':
        nome = request.form['nome_usuario']
        email = request.form['email_usuario']
        senha = request.form['senha_usuario'] 
        return f"<h1>dados recebidos com sucesso!</h1><p>Ola, {nome} com o e_mail: {email} <br>Senha: {senha}!</p>"
        

    return render_template("htmlSa.html")

@app.route('/usuarios/<username>')
def show_user_profile(username):
    # a variável 'username' da URL é passada aqui
    return f'Perfil do usuário: {username}' 
