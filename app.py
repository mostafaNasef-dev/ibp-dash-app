from dash import Dash, html, dcc, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import psycopg2
import pandas as pd
import numpy as np
import os

# ================= OPTIONAL ML IMPORTS (SAFE) =================
try:
    from statsmodels.tsa.holtwinters import SimpleExpSmoothing
    HAS_SES = True
except:
    HAS_SES = False

try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_absolute_percentage_error
    HAS_RF = True
except:
    HAS_RF = False

try:
    import xgboost as xgb
    HAS_XGB = True
except:
    HAS_XGB = False

# ================= DATABASE =================
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
            params=(product,)
        )

# ================= APP =================
app = Dash(__name__, suppress_callback_exceptions=True,
           external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# ================= SESSION =================
ROLE = os.environ.get("IBP_ROLE", "planner")  # planner / manager

# ================= LAYOUT =================
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="approved", data=False),

    dbc.Row([
        dbc.Col(dbc.Nav([
            dbc.NavLink("📦 Products", href="/products"),
            dbc.NavLink("🤖 Forecast", href="/forecast"),
            dbc.NavLink("🏭 Inventory", href="/inventory"),
            dbc.NavLink("🧪 Scenarios", href="/scenarios"),
            dbc.NavLink("📊 Portfolio", href="/portfolio"),
            dbc.NavLink("🔐 Approval", href="/approval"),
        ], vertical=True, pills=True),
        width=2, style={"background": "#f8f9fa", "height": "100vh"}),

        dbc.Col(html.Div(id="page-content"), width=10)
    ])
])

# ================= FORECAST ENGINE =================
def run_forecast(series):
    results = []

    y = series.values
    X = np.arange(len(y)).reshape(-1, 1)

    if HAS_SES:
        ses = SimpleExpSmoothing(y).fit()
        fc = ses.forecast(1)[0]
        mape = mean_absolute_percentage_error(y, ses.fittedvalues)
        results.append(("SES", fc, mape))

    if HAS_RF:
        rf = RandomForestRegressor()
        rf.fit(X, y)
        pred = rf.predict(X)
        fc = rf.predict([[len(y)]])[0]
        mape = mean_absolute_percentage_error(y, pred)
        results.append(("RandomForest", fc, mape))

    if HAS_XGB:
        model = xgb.XGBRegressor()
        model.fit(X, y)
        pred = model.predict(X)
        fc = model.predict([[len(y)]])[0]
        mape = mean_absolute_percentage_error(y, pred)
        results.append(("XGBoost", fc, mape))

    df = pd.DataFrame(results, columns=["Model", "Forecast", "MAPE"])
    best = df.sort_values("MAPE").iloc[0]
    return df, best

# ================= ROUTING =================
@app.callback(Output("page-content", "children"),
              Input("url", "pathname"),
              State("approved", "data"))
def render_page(path, approved):

    products = load_products()

    # ---------- PRODUCTS ----------
    if path == "/products":
        return html.Div([
            html.H2("📦 Product Master"),
            dash_table.DataTable(
                data=products.to_dict("records"),
                columns=[{"name": c, "id": c} for c in products.columns],
                page_size=10
            )
        ])

    # ---------- FORECAST ----------
    if path == "/forecast":
        p = products.iloc[0]["product_code"]
        hist = load_history(p)

        if hist.empty:
            return html.P("Upload historical sales first")

        series = hist.set_index("month")["qty"]
        metrics, best = run_forecast(series)

        return html.Div([
            html.H2("🤖 Forecast Models"),
            dash_table.DataTable(
                data=metrics.to_dict("records"),
                columns=[{"name": c, "id": c} for c in metrics.columns]
            ),
            html.H4(f"Selected Model: {best['Model']} | Forecast: {best['Forecast']:.1f}")
        ])

    # ---------- INVENTORY ----------
    if path == "/inventory":
        rows = []
        for _, p in products.iterrows():
            hist = load_history(p.product_code)
            if hist.empty:
                continue

            avg = hist.qty.mean()
            std = hist.qty.std()
            safety = std * 1.65
            inv = p.opening_inventory
            prod = min(avg, p.monthly_capacity)
            end_inv = inv + prod - avg
            turns = avg * 12 / max(inv, 1)

            rows.append({
                "Product": p.product_code,
                "Safety Stock": round(safety, 1),
                "Ending Inventory": round(end_inv, 1),
                "Inventory Turns": round(turns, 2),
            })

        return dash_table.DataTable(
            data=rows,
            columns=[{"name": k, "id": k} for k in rows[0]]
        )

    # ---------- SCENARIOS ----------
    if path == "/scenarios":
        rows = []
        for _, p in products.iterrows():
            hist = load_history(p.product_code)
            if hist.empty:
                continue

            base = hist.qty.mean()
            for label, f in [("Base", 1), ("+10%", 1.1), ("-10%", 0.9)]:
                demand = base * f
                service = min(p.monthly_capacity / demand, 1)
                value = p.unit_cost * p.opening_inventory

                rows.append({
                    "Product": p.product_code,
                    "Scenario": label,
                    "Demand": round(demand, 1),
                    "Service Level %": round(service * 100, 1),
                    "Inventory Value": round(value, 1),
                })

        return dash_table.DataTable(
            data=rows,
            columns=[{"name": k, "id": k} for k in rows[0]]
        )

    # ---------- PORTFOLIO ----------
    if path == "/portfolio":
        rows = []
        for _, p in products.iterrows():
            hist = load_history(p.product_code)
            if hist.empty:
                continue

            annual = hist.qty.sum()
            util = annual / (p.monthly_capacity * 12)

            rows.append({
                "Product": p.product_code,
                "Annual Demand": annual,
                "Capacity Util %": round(util * 100, 1),
                "Inventory Value": p.opening_inventory * p.unit_cost
            })

        return dash_table.DataTable(
            data=rows,
            columns=[{"name": k, "id": k} for k in rows[0]]
        )

    # ---------- APPROVAL ----------
    if path == "/approval":
        if ROLE != "manager":
            return html.P("Only managers can approve plans")

        return html.Div([
            html.H2("🔐 Plan Approval"),
            dbc.Button("Approve Plan", id="approve", color="success"),
            dbc.Button("Reject Plan", id="reject", color="danger", className="ms-2"),
            html.Div(id="approval-status")
        ])

    return html.H2("Welcome to IBP")

# ================= APPROVAL CALLBACK =================
@app.callback(
    Output("approved", "data"),
    Output("approval-status", "children"),
    Input("approve", "n_clicks"),
    Input("reject", "n_clicks"),
    prevent_initial_call=True
)
def approve_plan(a, r):
    if a:
        return True, "✅ Plan Approved"
    if r:
        return False, "❌ Plan Rejected"
    return False, ""

# ================= RUN =================
if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050)
