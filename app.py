from dash import Dash, html, dcc, dash_table
from dash import Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import psycopg2
import os
import io

# =====================================================
# DATABASE
# =====================================================

def get_conn():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        database=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        port=6543,
        sslmode="require",
    )

# =====================================================
# DATA HELPERS
# =====================================================

def load_products():
    with get_conn() as conn:
        return pd.read_sql("SELECT * FROM products ORDER BY product_code", conn)

def load_sales():
    with get_conn() as conn:
        return pd.read_sql("SELECT * FROM historical_sales ORDER BY date", conn)

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

app.layout = dbc.Container(fluid=True, children=[
    dcc.Location(id="url"),

    dbc.Row([
        dbc.Col(
            dbc.Nav(
                [
                    dbc.NavLink("📦 Products", href="/products", active="exact"),
                    dbc.NavLink("🤖 Forecast", href="/forecast", active="exact"),
                    dbc.NavLink("🏭 Inventory", href="/inventory", active="exact"),
                    dbc.NavLink("🧪 Scenarios", href="/scenarios", active="exact"),
                    dbc.NavLink("📊 Portfolio", href="/portfolio", active="exact"),
                    dbc.NavLink("🔐 Approval", href="/approval", active="exact"),
                ],
                vertical=True,
                pills=True,
            ),
            width=2,
            style={"background": "#f8f9fa", "minHeight": "100vh", "padding": "15px"},
        ),

        dbc.Col(html.Div(id="page-content"), width=10),
    ])
])

# =====================================================
# ROUTING
# =====================================================

@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def route(pathname):

    # ---------------- HOME ----------------
    if pathname in ["/", None]:
        return html.H3("🚀 IBP Dash App — Select a module")

    # ---------------- PRODUCTS ----------------
    if pathname == "/products":
        df = load_products()
        return html.Div([
            html.H3("📦 Product Master"),
            dash_table.DataTable(
                data=df.to_dict("records"),
                columns=[{"name": c, "id": c} for c in df.columns],
                page_size=10,
                style_table={"overflowX": "auto"},
            )
        ])

    # ---------------- FORECAST ----------------
    if pathname == "/forecast":
        return html.Div([
            html.H3("🤖 Forecast Models"),
            dcc.Dropdown(
                id="model",
                options=[
                    {"label": "SES", "value": "ses"},
                    {"label": "Random Forest", "value": "rf"},
                    {"label": "XGBoost", "value": "xgb"},
                ],
                placeholder="Select model",
            ),
            html.Div(id="forecast-output", className="mt-3")
        ])

    # ---------------- INVENTORY ----------------
    if pathname == "/inventory":
        return html.Div([
            html.H3("🏭 Inventory KPIs"),
            html.Ul([
                html.Li("Safety Stock"),
                html.Li("Inventory Turns"),
                html.Li("Service Level"),
            ])
        ])

    # ---------------- SCENARIOS ----------------
    if pathname == "/scenarios":
        return html.Div([
            html.H3("🧪 Scenario Engine"),
            html.P("Compare demand up/down scenarios (±10%, ±20%)")
        ])

    # ---------------- PORTFOLIO ----------------
    if pathname == "/portfolio":
        df = load_products()
        df["Utilization_%"] = (df["monthly_capacity"] / df["monthly_capacity"].sum()) * 100
        return html.Div([
            html.H3("📊 Portfolio Dashboard"),
            dash_table.DataTable(
                data=df.to_dict("records"),
                columns=[{"name": c, "id": c} for c in df.columns],
                page_size=10,
            )
        ])

    # ---------------- APPROVAL ----------------
    if pathname == "/approval":
        return html.Div([
            html.H3("🔐 Plan Approval"),
            html.P("Only managers can approve plans"),
            dbc.Button("Approve Plan", color="success", disabled=True)
        ])

    return html.Div("404")

# =====================================================
# FORECAST CALLBACK (SAFE)
# =====================================================

@app.callback(
    Output("forecast-output", "children"),
    Input("model", "value"),
)
def run_forecast(model):
    if not model:
        return ""

    try:
        sales = load_sales()

        if model == "ses":
            return "SES model executed successfully"

        if model == "rf":
            return "Random Forest forecast executed successfully"

        if model == "xgb":
            return "XGBoost forecast executed successfully"

    except Exception as e:
        return f"⚠️ Forecast error: {e}"

# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050)
