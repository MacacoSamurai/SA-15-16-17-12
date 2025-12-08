create database mecanica;
use mecanica;

create table funcionarios (
    id_func int auto_increment primary key,
    nome_func varchar(20),
    login_user varchar(30) UNIQUE NOT NULL, 
    senha_user varchar(255) NOT NULL,
    cargo     varchar(20),
    cpf       varchar(11)
);

create table carros (
    placa_carro varchar(7) primary key,
    modelo      varchar(20),
    fabricante  varchar(30)
);

create table clientes (
    id_cliente int auto_increment primary key,
    nome_cliente varchar(20),
    cpf          varchar(11),
    celular      varchar(11),
    placa_carro  varchar(7),
    foreign key (placa_carro) references carros(placa_carro)
);

-- Tabela registro_servico atualizada (sem pecas_subs)
create table registro_servico (
    id_reg int auto_increment primary key,
    diagnostico varchar(280),
    -- pecas_subs foi removida, será gerenciada pela tabela servico_pecas
    func_id     int,
    prazo       timestamp,
    realizacao  datetime,
    cliente     int,
    placa       varchar(7),
    valor_peca  float,
    valor_servico  float,
    valor_total  float,

    foreign key (placa)    references carros(placa_carro),
    foreign key (cliente)  references clientes(id_cliente),
    foreign key (func_id) references funcionarios(id_func)
);

create table estoque (
    id_peca    int auto_increment primary key,
    nome_peca  varchar(30),
    lote       int,
    validade   date,
    fornecedor varchar(30),
    quant_peca int,
    min        int,
    max        int
);

-- NOVA TABELA: Relacionamento Muitos-para-Muitos entre Serviço e Peça
create table servico_pecas (
    id_servico_peca int auto_increment primary key,
    id_registro     int,
    id_peca_estoque int,
    quantidade_usada int not null,
    foreign key (id_registro) references registro_servico(id_reg) ON DELETE CASCADE,
    foreign key (id_peca_estoque) references estoque(id_peca) ON DELETE RESTRICT 
    -- ON DELETE CASCADE garante que, se um serviço for apagado, o registro de uso da peça também será.
);


insert into funcionarios (nome_func, login_user, senha_user, cargo, cpf) values
('Adm Geral','ADM','scrypt:32768:8:1$2ZmUdRtaBFQkrETz$5ba0195cc74885ab48aced985bf3f76b3f2bb83d9c580453aa2c3fe847b1addb17d9b63c171da4f9854a1be955b6b611e64b4758ac70735e2eeb39e5e17c03dd','gerente','12345678910');

select * from funcionarios