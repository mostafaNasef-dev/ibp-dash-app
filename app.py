from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
import psycopg2
import pandas as pd
import os

def get_conn():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        database=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        port=6543,
        sslmode="require",
    )

def load_products():
    with get_conn() as conn:
        return pd.read_sql(
            "SELECT * FROM products ORDER BY product_code",
            conn
        )

def upsert_product(code, name, opening, capacity, cost):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO products
            (product_code, product_name, opening_inventory, monthly_capacity, unit_cost)
            VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT (product_code)
            DO UPDATE SET
                product_name = EXCLUDED.product_name,
                opening_inventory = EXCLUDED.opening_inventory,
                monthly_capacity = EXCLUDED.monthly_capacity,
                unit_cost = EXCLUDED.unit_cost
            """,
            (code, name, opening, capacity, cost)
        )
        conn.commit()

def delete_product(code):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM products WHERE product_code = %s",
            (code,)
        )
        conn.commit()

# ---------------- App ----------------
app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
)

# ---------------- Layout ----------------
app.layout = html.Div([
    dcc.Location(id="url"),

    dbc.Row([
        # -------- Sidebar --------
        dbc.Col(
            dbc.Nav(
                [
                    dbc.NavLink("📦 Product Master", href="/products", active="exact"),
                    dbc.NavLink("📊 Historical Sales", href="/history", active="exact"),
                    dbc.NavLink("🤖 Forecast & Models", href="/forecast", active="exact"),
                    dbc.NavLink("🏭 Inventory & KPIs", href="/inventory", active="exact"),
                    dbc.NavLink("🧪 Scenario Comparison", href="/scenarios", active="exact"),
                    dbc.NavLink("📦 Portfolio View", href="/portfolio", active="exact"),
                ],
                vertical=True,
                pills=True,
            ),
            width=2,
            style={
                "backgroundColor": "#f8f9fa",
                "minHeight": "100vh",
                "padding": "20px",
            },
        ),

        # -------- Page Content --------
        dbc.Col(
            html.Div(id="page-content", style={"padding": "30px"}),
            width=10,
        ),
    ])
])

# ---------------- Pages ----------------
def page_layout(title, text):
    return html.Div([
        html.H2(title),
        html.P(text),
    ])

# ---------------- Routing ----------------
@app.callback(
    dcc.Output("page-content", "children"),
    dcc.Input("url", "pathname"),
)
def render_page(pathname):
    if pathname == "/products":
        return page_layout("📦 Product Master", "Manage products here")
    if pathname == "/history":
        return page_layout("📊 Historical Sales", "Upload 12 months of history")
    if pathname == "/forecast":
        return page_layout("🤖 Forecast & Models", "Run forecasting models")
    if pathname == "/inventory":
        return page_layout("🏭 Inventory & KPIs", "Inventory planning and KPIs")
    if pathname == "/scenarios":
        return page_layout("🧪 Scenario Comparison", "Compare demand scenarios")
    if pathname == "/portfolio":
        return page_layout("📦 Portfolio View", "Multi-product portfolio KPIs")

    return page_layout(
        "🚀 IBP Dash App",
        "Use the navigation menu to start planning."
    )

# ---------------- Run ----------------
if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050)
