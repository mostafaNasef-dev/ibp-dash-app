from dash import Dash, html

app = Dash(__name__)

app.layout = html.Div(
    style={"padding": "40px", "fontFamily": "Arial"},
    children=[
        html.H1("🚀 IBP Dash App"),
        html.P("Deployment successful. Streamlit → Dash migration started."),
    ],
)

if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050)
