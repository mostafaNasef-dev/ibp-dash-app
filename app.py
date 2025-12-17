from dash import Dash, html, dcc, dash_table
import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State
import psycopg2
import pandas as pd
import os

# =====================================================
# DATABASE HELPERS
# =====================================================

def get_conn():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        database=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        port=5432,
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

# =====================================================
# APP
# =====================================================

app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
)

# =====================================================
# LAYOUT
# =====================================================

app.layout = html.Div([
    dcc.Location(id="url"),

    dbc.Row([
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

        dbc.Col(
            html.Div(id="page-content", style={"padding": "30px"}),
            width=10,
        ),
    ])
])

# =====================================================
# ROUTING
# =====================================================

from dash import Input, Output

@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
)
def render_page(pathname):

    # ---------- HOME ----------
    if pathname in ["/", None]:
        return html.Div([
            html.H2("🚀 IBP Dash App"),
            html.P("Select a page from the left menu to start."),
        ])

    # ---------- PRODUCT MASTER ----------
    if pathname == "/products":
        df = load_products()

        return html.Div([
            html.H2("📦 Product Master"),

            dbc.Row([
                dbc.Col([
                    dbc.Input(id="p-code", placeholder="Product Code"),
                    dbc.Input(id="p-name", placeholder="Product Name", className="mt-2"),
                    dbc.Input(id="p-open", type="number", placeholder="Opening Inventory", className="mt-2"),
                    dbc.Input(id="p-cap", type="number", placeholder="Monthly Capacity", className="mt-2"),
                    dbc.Input(id="p-cost", type="number", placeholder="Unit Cost", className="mt-2"),

                    dbc.Button("💾 Save Product", id="save-product", color="primary", className="mt-3"),
                    dbc.Button("🗑 Delete Product", id="delete-product", color="danger", className="mt-2"),
                ], width=4),

                dbc.Col([
                    dash_table.DataTable(
                        id="product-table",
                        data=df.to_dict("records"),
                        columns=[{"name": c, "id": c} for c in df.columns],
                        row_selectable="single",
                        style_table={"overflowX": "auto"},
                        page_size=10,
                    )
                ], width=8),
            ])
        ])

    # ---------- HISTORICAL SALES ----------
    if pathname == "/history":
        return html.Div([
            html.H2("📊 Historical Sales"),
            html.P("Historical sales upload & validation — coming next"),
        ])

    # ---------- FORECAST ----------
    if pathname == "/forecast":
        return html.Div([
            html.H2("🤖 Forecast & Models"),
            html.P("Forecast models, metrics, and selection — coming next"),
        ])

    # ---------- INVENTORY ----------
    if pathname == "/inventory":
        return html.Div([
            html.H2("🏭 Inventory & KPIs"),
            html.P("Inventory simulation, turns, safety stock — coming next"),
        ])

    # ---------- SCENARIOS ----------
    if pathname == "/scenarios":
        return html.Div([
            html.H2("🧪 Scenario Comparison"),
            html.P("Demand & capacity scenarios — coming next"),
        ])

    # ---------- PORTFOLIO ----------
    if pathname == "/portfolio":
        return html.Div([
            html.H2("📦 Portfolio View"),
            html.P("Multi-product KPIs — coming next"),
        ])

    # ---------- FALLBACK ----------
    return html.Div([
        html.H2("404"),
        html.P(f"Unknown page: {pathname}")
    ])


# =====================================================
# CALLBACKS
# =====================================================

@app.callback(
    Output("product-table", "data"),
    Input("save-product", "n_clicks"),
    Input("delete-product", "n_clicks"),
    State("p-code", "value"),
    State("p-name", "value"),
    State("p-open", "value"),
    State("p-cap", "value"),
    State("p-cost", "value"),
    prevent_initial_call=True
)
def manage_products(save_clicks, delete_clicks, code, name, opening, capacity, cost):
    ctx = dash.callback_context

    if not ctx.triggered or not code:
        return load_products().to_dict("records")

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger == "save-product":
        upsert_product(code, name, opening or 0, capacity or 0, cost or 0)

    elif trigger == "delete-product":
        delete_product(code)

    return load_products().to_dict("records")

# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050)
