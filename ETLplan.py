import os

print("Diretório atual:", os.getcwd())
print("Arquivos na pasta:")
print(os.listdir())

from sqlalchemy import create_engine
import pandas as pd

# CONFIGURANDO CONEXÃO - a create engine faz a ponte entre o banco e a planilha
engine = create_engine("postgresql+psycopg2://postgres:123456@localhost:5432/mfix")
arquivo = "mfix.xlsx"

df_fornecedor =     pd.read_excel(arquivo, sheet_name='fornecedor')  #aqui a pandas tá lendo cada página da planilha
df_lotes =          pd.read_excel(arquivo, sheet_name='lotes')
df_transportadora = pd.read_excel(arquivo, sheet_name='transportadora')
df_mov =            pd.read_excel(arquivo, sheet_name='mov_estoque')
df_produto =        pd.read_excel(arquivo, sheet_name='produto')

##### tratar pra limpar os espaços vazios nas colunas
for df in [df_fornecedor, df_produto, df_mov, df_lotes, df_transportadora]:
    df.columns = df.columns.str.strip() # columns é um atributo que ta guardando o nome das colunas, str padroniza datatype e strip elimina espaços

##### nomenclaturas

df_fornecedor = df_fornecedor.rename(columns={
    'NOME': 'nome_forn',
    'CNPJ': 'cnpj_forn',
    'CIDADE': 'cidade_forn',
    'ESTADO': 'uf_forn'
}) ### a sintaxe do columns recebe um dicionario, com sua 'chave' sendo nome originário sheet, e seu valor o nome da database

df_produto = df_produto.rename(columns={
    'DESCRICAO':        'descricao_prod',
    'PRECO DE COMPRA':  'preco_compra',
    'PRECO VENDA':      'preco_venda',
    'LUCRO':            'lucro',
    'QTDE P/CAIXA':     'qtdep_caixa',
    'LOTE':             'lote_prod',
    'DATA_SAIDA':       'data_saida',
    'DATA_ENTRADA':     'data_entrada',
    'PROCEDENCIA':      'procedencia_prod',
    'CATEGORIA':        'categoria_prod'
})


df_transportadora = df_transportadora.rename(columns={
    'NOME': 'nome_transp',
    'CNPJ': 'cnpj_transp'
})


df_lotes = df_lotes.rename(columns={
    'NUMERO DO LOTE': 'numero_lote',
    'DATA DE VALIDADE': 'data_validade'
})

df_mov = df_mov.rename(columns={
    'NUMERO DE REGISTRO':       'id_produto',
    'PRODUTO':                  'produto',
    'NUMERO LOTE':              'numero_lote',
    'TIPO DE REGISTRO':         'tipo_mov',
    'FORNECEDOR':               'fornecedor',
    'TRANSPORTADORA':           'transportadora',
    'DATA':                     'data',
    'QUANTIDADE DO PRODUTO':    'qtde_prod',
    'UNIDADE DE MEDIDA':        'unidade_medida'
})

df_lotes    ['data_validade'] = pd.to_datetime(df_lotes['data_validade'],  errors='coerce')
df_mov      ['data'] =          pd.to_datetime(df_mov    ['data'],         errors='coerce')   #tratamento de data
# pega o atributo data e transforma o tipo de dado, os que não obedecerem a conversão são postos como inválidos

##### tratamento de data 

for coluna in ['data_saida', 'data_entrada']:
    # 1. Tenta converter o que for possível para número (os 45698 da vida)
    valores_numericos = pd.to_numeric(df_produto[coluna], errors='coerce')
    
    # 2. Cria uma máscara para saber onde temos números reais
    mask_num = valores_numericos.notna()
    
    # 3. Onde é número, converte usando a regra do Excel (unit='D')
    df_produto.loc[mask_num, coluna] = pd.to_datetime(
        valores_numericos[mask_num], # <--- O SEGREDO: usamos o valor já convertido em número
        unit='D', 
        origin='1899-12-30', 
        errors='coerce'
    )
    
    # 4. Onde NÃO era número (já era data em texto), tenta converter direto
    df_produto.loc[~mask_num, coluna] = pd.to_datetime(
        df_produto.loc[~mask_num, coluna],
        errors='coerce'
    )

######### case insensitive para os principais atributos

df_fornecedor['nome_forn'] = df_fornecedor['nome_forn'].str.strip().str.upper()
df_produto['descricao_prod'] = df_produto['descricao_prod'].str.strip().str.upper()
df_transportadora['nome_transp'] = df_transportadora['nome_transp'].str.strip().str.upper()
df_lotes['numero_lote'] = df_lotes['numero_lote'].astype(str).str.strip().str.upper()

df_mov['fornecedor'] = df_mov['fornecedor'].str.strip().str.upper()
df_mov['produto'] = df_mov['produto'].str.strip().str.upper()
df_mov['transportadora'] = df_mov['transportadora'].str.strip().str.upper()
df_mov['tipo_mov'] = df_mov['tipo_mov'].str.strip().str.upper()
df_mov['numero_lote'] = df_mov['numero_lote'].astype(str).str.strip().str.upper()


# evitar duplicatas e salvar tabelas base

df_fornecedor = df_fornecedor.drop_duplicates()
df_produto = df_produto.drop_duplicates()
df_transportadora = df_transportadora.drop_duplicates()
df_lotes = df_lotes.drop_duplicates()

#### load tabelas base

df_fornecedor       .to_sql('fornecedor',       engine, if_exists='append', index=False)
df_produto          .to_sql('produto',          engine, if_exists='append', index=False)
df_transportadora   .to_sql('transportadora',   engine, if_exists='append', index=False)
df_lotes            .to_sql('lotes',            engine, if_exists='append', index=False)


# puxando os IDs das tabelas base
df_forn_db =    pd.read_sql("SELECT id, nome_forn FROM fornecedor", engine)
df_prod_db =    pd.read_sql("SELECT id, descricao_prod, preco_venda FROM produto",engine)
df_transp_db =  pd.read_sql("SELECT id, nome_transp FROM transportadora", engine)
df_lotes_db =   pd.read_sql("SELECT id, numero_lote FROM lotes", engine )

 # padronização de movimentação_estoque para tornar case insensitive

##### MERGES (JOIN no SQL)

df_mov = df_mov.merge(
    df_forn_db.rename(columns={'id': 'fornecedor_id'}),
    left_on='fornecedor',
    right_on='nome_forn',
    how='left'                  )

df_mov = df_mov.merge(
    df_prod_db.rename(columns={'id': 'produto_id'}),
    left_on='produto',
    right_on='descricao_prod',
    how='left'                  )

df_mov = df_mov.merge(
    df_transp_db.rename(columns={'id': 'transportadora_id'}),
    left_on='transportadora',
    right_on='nome_transp',
    how='left'                  )
# garantir que não existam nomes de transportadoras duplicados no cadastro que veio do banco
df_transp_db = df_transp_db.drop_duplicates(subset=['nome_transp'])

df_mov = df_mov.merge(
    df_lotes_db.rename(columns={'id': 'lote_id'}),
    on='numero_lote',
    how='left'
)

# tratamento para verificação de id nulo

print("Registros com problema de fornecedor:")
print(df_mov[
                (df_mov["fornecedor_id"].isna()) &  
                (df_mov["tipo_mov"] == "ENTRADA")  ] )  # verifica erro de null onde não pode ser null


print("Registros com problema de produto:") # o mesmo de cima
print(df_mov[df_mov['produto_id'].isna()])

print("Registros com problema de transportadora:")
print( df_mov[
                    (df_mov["tipo_mov"] == "AJUSTE") &
                    (df_mov["transportadora_id"].notna())  ] )    # igual pra transp

erro_lote = df_mov[df_mov['lote_id'].isna()] # evitar erro de lote, que não pode ser nulo em nenhum registro

if erro_lote.shape[0] > 0:
    raise ValueError("Erro de lote")

###### tratamento para a table tipo_mov
df_tipo = pd.DataFrame({
    'id': [1, 2, 3],
    'tipo_mov': ['ENTRADA', 'SAÍDA', 'AJUSTE']
})

df_mov['tipo_mov'] = df_mov['tipo_mov'].str.strip().str.upper()

df_mov = df_mov.merge(
    df_tipo.rename(columns={'id': 'tipo_mov_id'}),
    on='tipo_mov',
    how='left'
)

############# tabela central final
df_mov_final = df_mov[[
    'produto_id',
    'fornecedor_id',
    'transportadora_id',
    'lote_id',
    'tipo_mov_id',
    'data',
    'qtde_prod',
    'preco_venda',
    'unidade_medida'
                        ]]

# load
df_mov_final        .to_sql('mov_estoque',      engine, if_exists='append', index=False)

#################################### Consultar a execução do etl
print("\n" + "="*50)
print("     RELATÓRIO DE CONFERÊNCIA DO BANCO DE DADOS")
print("="*50)

# Quantidade de registros por tabela
tabelas = ['fornecedor', 'produto', 'transportadora', 'lotes', 'mov_estoque']
print("\n[ESTATÍSTICAS DE CARGA]")
for tabela in tabelas:
    qtd = pd.read_sql(f"SELECT COUNT(*) FROM {tabela}", engine).iloc[0, 0]
    print(f"-> Tabela {tabela:15} | Registros: {qtd}")

# Movimentação 
query_demonstracao = """
    SELECT 
        m.data AS data_mov,
        p.descricao_prod AS produto,
        f.nome_forn AS fornecedor,
        l.numero_lote AS lote,
        tm.descricao_mov,
        m.qtde_prod,
        m.unidade_medida
    FROM mov_estoque m
    LEFT JOIN produto p ON m.produto_id = p.id
    LEFT JOIN fornecedor f ON m.fornecedor_id = f.id
    LEFT JOIN lotes l ON m.lote_id = l.id
    LEFT JOIN tipo_mov tm ON m.tipo_mov_id = tm.id
    ORDER BY m.data DESC
    LIMIT 10;
"""

print("\n[DEMONSTRAÇÃO DE DADOS INTEGRADOS - ÚLTIMOS 10 REGISTROS]")
df_final = pd.read_sql(query_demonstracao, engine)

if df_final.empty:
    print("AVISO: A tabela de movimentação está vazia no banco.")
else:
    print(df_final.to_string(index=False))

# Validação de Saúde das Datas
print("\n[VERIFICAÇÃO DE TIPOS DE DATA]")
df_datas = pd.read_sql("SELECT data_saida, data_entrada FROM produto LIMIT 1", engine)
print(f"Tipo no Banco (Saída): {type(df_datas['data_saida'][0])}")

print("\n" + "="*50)
print("             ETL FINALIZADO COM SUCESSO")
print("="*50)
