"""
Personal Finance Tracker - Main Application
Built with Dash Plotly
"""

import dash
import dash_bootstrap_components as dbc
from dash import Dash, html

app = Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css",
    ],
    suppress_callback_exceptions=True,
    title="Finance Tracker",
    update_title="Loading...",
    use_pages=True,
)

server = app.server

app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H1(
                            "💰 Personal Finance Tracker", className="text-primary mb-0"
                        ),
                        html.P(
                            "Track expenses, manage budgets, and monitor savings",
                            className="text-muted mb-0",
                        ),
                    ],
                    width=12,
                )
            ],
            className="mb-4 mt-3",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Nav(
                            [
                                dbc.NavLink(
                                    [
                                        html.I(className="bi bi-house-door me-2"),
                                        "Dashboard",
                                    ],
                                    href="/",
                                    active="exact",
                                ),
                                dbc.NavLink(
                                    [html.I(className="bi bi-wallet2 me-2"), "Budgets"],
                                    href="/budgets",
                                    active="exact",
                                ),
                                dbc.NavLink(
                                    [
                                        html.I(className="bi bi-piggy-bank me-2"),
                                        "Savings",
                                    ],
                                    href="/savings",
                                    active="exact",
                                ),
                                dbc.NavLink(
                                    [
                                        html.I(className="bi bi-bar-chart me-2"),
                                        "Analytics",
                                    ],
                                    href="/analytics",
                                    active="exact",
                                ),
                                dbc.NavLink(
                                    [
                                        html.I(className="bi bi-receipt me-2"),
                                        "Transactions",
                                    ],
                                    href="/transactions",
                                    active="exact",
                                ),
                                dbc.NavLink(
                                    [html.I(className="bi bi-upload me-2"), "Import"],
                                    href="/import",
                                    active="exact",
                                ),
                            ],
                            pills=True,
                            className="mb-4",
                        )
                    ]
                )
            ]
        ),
        dbc.Row([dbc.Col([dash.page_container], width=12)]),
    ],
    fluid=True,
    className="py-3",
)


if __name__ == "__main__":
    app.run_server(debug=True, port=8080)
