from flask import Flask, render_template, request, jsonify
from sqlalchemy import create_engine, text
import pandas as pd
import plotly.graph_objects as go

app = Flask(__name__)

engine = create_engine(
    "postgresql+psycopg2://postgres:123456@localhost:5432/mfix"
)

def consultar(query, params={}):
    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
    return df.to_dict(orient="records")

#em qualquer outra fnção : dados = consultar(query, params)

#top 5 produtos mais vendidos
def top5produtos(a=5):
    query = """
    SELECT
        p.descricao_prod,
        SUM(m.quantidade_mov) AS total_vendido
    FROM
        movimentacao m
    JOIN
        produto p ON m.id_prod = p.id_prod
    WHERE
        m.tipo_mov = 'Venda'
    GROUP BY
        p.descricao_prod
    ORDER BY
        total_vendido DESC
    LIMIT %s;
    """
    dados = consultar(query, a)
    print(dados)
print(top5produtos())

