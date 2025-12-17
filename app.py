from dash import Dash, html, dcc, dash_table
import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State
import psycopg2
import pandas as pd
import numpy as np
import os

from statsmodels.tsa.holtwinters import SimpleExpSmoothing
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_percentage_error

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

def load_products():
    with get_conn() as conn:
        return pd.read_sql("SELECT * FROM products ORDER BY product_code", conn)

def load_history(product):
    with get_conn() as conn:
        return pd.read_sql(
            "SELECT * FROM historical_sales WHERE product_code=%s ORDER BY month",
            conn,
            params=(product,),
        )

def insert_history(df):
    with get_conn() as conn:
        df.to_sql("historical_sales", conn, if_exists="append", index=False, method="multi")

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

        dbc.Col(html.Div(id="page-content", style={"padding": "30px"}), width=10),
    ])
])

# =====================================================
# ROUTER
# =====================================================

@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def render_page(pathname):

    products = load_products()

    if pathname in ["/", None]:
        return html.H3("🚀 IBP Dash App")

    # =================================================
    # HISTORICAL SALES
    # =================================================
    if pathname == "/history":
        return html.Div([
            html.H2("📊 Historical Sales Upload"),
            dcc.Upload(
                id="upload-sales",
                children=dbc.Button("Upload CSV / Excel"),
                multiple=False,
            ),
            html.Div(id="upload-status")
        ])

    # =================================================
    # FORECAST
    # =================================================
    if pathname == "/forecast":
        product = products["product_code"].iloc[0]
        hist = load_history(product)

        if hist.empty:
            return html.Div(["No historical data available"])

        y = hist["qty"].values

        ses = SimpleExpSmoothing(y).fit()
        ses_fc = ses.forecast(1)[0]
        ses_mape = mean_absolute_percentage_error(y, ses.fittedvalues)

        X = np.arange(len(y)).reshape(-1, 1)
        rf = RandomForestRegressor()
        rf.fit(X, y)
        rf_fc = rf.predict([[len(y)]])[0]
        rf_mape = mean_absolute_percentage_error(y, rf.predict(X))

        df = pd.DataFrame({
            "Model": ["SES", "RandomForest"],
            "MAPE": [ses_mape, rf_mape],
            "Forecast": [ses_fc, rf_fc],
        })

        return dash_table.DataTable(df.to_dict("records"),
                                    [{"name": c, "id": c} for c in df.columns])

    # =================================================
    # INVENTORY
    # =================================================
    if pathname == "/inventory":
        rows = []
        for _, p in products.iterrows():
            hist = load_history(p.product_code)
            if hist.empty:
                continue

            avg = hist.qty.mean()
            safety = hist.qty.std() * 1.65
            turns = avg * 12 / max(p.opening_inventory, 1)

            rows.append({
                "Product": p.product_code,
                "Safety Stock": round(safety, 1),
                "Inventory Turns": round(turns, 2),
            })

        return dash_table.DataTable(rows, [{"name": k, "id": k} for k in rows[0]])

    # =================================================
    # SCENARIOS
    # =================================================
    if pathname == "/scenarios":
        rows = []
        for _, p in products.iterrows():
            hist = load_history(p.product_code)
            if hist.empty:
                continue

            base = hist.qty.mean()
            for label, mult in [("Base", 1), ("+10%", 1.1), ("-10%", 0.9)]:
                demand = base * mult
                service = min(p.monthly_capacity / demand, 1)

                rows.append({
                    "Product": p.product_code,
                    "Scenario": label,
                    "Service_Level_%": round(service * 100, 1),
                })

        return dash_table.DataTable(rows, [{"name": k, "id": k} for k in rows[0]])

    # =================================================
    # PORTFOLIO
    # =================================================
    if pathname == "/portfolio":
        rows = []
        for _, p in products.iterrows():
            hist = load_history(p.product_code)
            if hist.empty:
                continue

            annual = hist.qty.sum()
            util = annual / (p.monthly_capacity * 12)

            rows.append({
                "Product": p.product_code,
                "Annual_Demand": annual,
                "Capacity_Util_%": round(util * 100, 1),
                "Inventory_Value": p.opening_inventory * p.unit_cost,
            })

        return dash_table.DataTable(rows, [{"name": k, "id": k} for k in rows[0]])

    return html.H3("404")

# =====================================================
# UPLOAD CALLBACK
# =====================================================

@app.callback(
    Output("upload-status", "children"),
    Input("upload-sales", "contents"),
    State("upload-sales", "filename"),
)
def upload_sales(contents, filename):
    if not contents:
        return ""

    content_type, content_string = contents.split(",")
    decoded = pd.read_csv(
        pd.compat.StringIO(pd.compat.base64.b64decode(content_string).decode("utf-8"))
    ) if filename.endswith(".csv") else pd.read_excel(
        pd.compat.BytesIO(pd.compat.base64.b64decode(content_string))
    )

    insert_history(decoded)
    return "Upload successful"

# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(host="0.0.0.0", port=port)
