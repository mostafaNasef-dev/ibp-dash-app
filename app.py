from dash import Dash, html, dcc
import dash_bootstrap_components as dbc

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
