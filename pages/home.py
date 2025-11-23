"""
Dashboard Home Page (SQLite)
Overview of finances for current month
"""

import calendar
from datetime import datetime

import dash
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html

from database.db import db

dash.register_page(__name__, path="/", title="Dashboard")


def get_month_summary(year: int, month: int):
    """Get summary statistics for a specific month"""
    first_day = f"{year}-{month:02d}-01"
    last_day = f"{year}-{month:02d}-{calendar.monthrange(year, month)[1]}"

    your_spending = db.fetch_all(
        """
        SELECT COALESCE(SUM(amount_usd), 0)
        FROM transactions
        WHERE date BETWEEN ? AND ?
          AND is_quorum = 0
    """,
        (first_day, last_day),
    )[0][0]

    quorum_spending = db.fetch_all(
        """
        SELECT COALESCE(SUM(amount_usd), 0)
        FROM transactions
        WHERE date BETWEEN ? AND ?
          AND is_quorum = 1
    """,
        (first_day, last_day),
    )[0][0]

    your_eur = db.fetch_all(
        """
        SELECT COALESCE(SUM(amount_eur), 0)
        FROM transactions
        WHERE date BETWEEN ? AND ?
          AND is_quorum = 0
    """,
        (first_day, last_day),
    )[0][0]

    category_breakdown = db.fetch_df(
        """
        SELECT 
            category,
            ROUND(SUM(amount_eur), 2) as total_eur,
            COUNT(*) as transaction_count
        FROM transactions
        WHERE date BETWEEN ? AND ?
          AND is_quorum = 0
        GROUP BY category
        ORDER BY total_eur DESC
    """,
        (first_day, last_day),
    )

    return {
        "your_spending_usd": float(your_spending),
        "your_spending_eur": float(your_eur),
        "quorum_spending_usd": float(quorum_spending),
        "total_spending_usd": float(your_spending + quorum_spending),
        "category_breakdown": category_breakdown,
    }


def layout():
    today = datetime.now()
    return dbc.Container(
        [
            dcc.Store(
                id="current-month", data={"year": today.year, "month": today.month}
            ),
            html.Div(id="dashboard-content"),
        ],
        fluid=True,
    )


def render_dashboard(year, month):
    month_name = calendar.month_name[month]

    summary = get_month_summary(year, month)

    recent_df = db.fetch_df("""
        SELECT 
            date,
            description,
            amount_usd,
            amount_eur,
            category,
            subcategory,
            is_quorum
        FROM transactions
        ORDER BY date DESC
        LIMIT 10
    """)

    try:
        uncategorized_count = db.fetch_all("""
            SELECT COUNT(*)
            FROM transactions
            WHERE subcategory = 'Uncategorized'
        """)[0][0]
    except:
        uncategorized_count = 0

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2(f"{month_name} {year}", className="mb-0"),
                            html.P("Overview of your finances", className="text-muted"),
                        ],
                        width=8,
                    ),
                    dbc.Col(
                        [
                            dbc.Button(
                                "Previous Month",
                                id="prev-month",
                                outline=True,
                                color="secondary",
                                size="sm",
                                className="me-2",
                            ),
                            dbc.Button(
                                "Next Month",
                                id="next-month",
                                outline=True,
                                color="secondary",
                                size="sm",
                            ),
                        ],
                        width=4,
                        className="text-end",
                    ),
                ],
                className="mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.H6(
                                        "Your Spending", className="text-muted mb-2"
                                    ),
                                    html.H3(
                                        f"€{summary['your_spending_eur']:,.2f}",
                                        className="mb-0",
                                    ),
                                    html.Small(
                                        f"${summary['your_spending_usd']:,.2f} USD",
                                        className="text-muted",
                                    ),
                                ]
                            )
                        ),
                        width=3,
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.H6(
                                        "Quorum (Reimbursable)",
                                        className="text-muted mb-2",
                                    ),
                                    html.H3(
                                        f"${summary['quorum_spending_usd']:,.2f}",
                                        className="mb-0 text-success",
                                    ),
                                    html.Small(
                                        "USD transactions", className="text-muted"
                                    ),
                                ]
                            )
                        ),
                        width=3,
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.H6(
                                        "Total Credit Card", className="text-muted mb-2"
                                    ),
                                    html.H3(
                                        f"${summary['total_spending_usd']:,.2f}",
                                        className="mb-0",
                                    ),
                                    html.Small(
                                        "Total USD charged", className="text-muted"
                                    ),
                                ]
                            )
                        ),
                        width=3,
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.H6("Need Review", className="text-muted mb-2"),
                                    html.H3(
                                        str(uncategorized_count),
                                        className="mb-0 text-warning"
                                        if uncategorized_count
                                        else "mb-0",
                                    ),
                                    html.Small(
                                        "Uncategorized transactions",
                                        className="text-muted",
                                    ),
                                ]
                            ),
                            color="warning" if uncategorized_count > 0 else None,
                            outline=True,
                        ),
                        width=3,
                    ),
                ],
                className="mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Spending by Category (EUR)"),
                                dbc.CardBody(
                                    dcc.Graph(
                                        id="category-bar-chart",
                                        figure=create_category_bar_chart(
                                            summary["category_breakdown"]
                                        ),
                                        config={"displayModeBar": False},
                                    )
                                ),
                            ]
                        ),
                        width=6,
                    ),
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Recent Transactions"),
                                dbc.CardBody(
                                    create_recent_transactions_list(recent_df),
                                    style={"maxHeight": "400px", "overflowY": "auto"},
                                ),
                            ]
                        ),
                        width=6,
                    ),
                ],
                className="mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.H5("Quick Actions", className="mb-3"),
                                    dbc.ButtonGroup(
                                        [
                                            dbc.Button(
                                                [
                                                    html.I(
                                                        className="bi bi-upload me-2"
                                                    ),
                                                    "Import Transactions",
                                                ],
                                                href="/import",
                                                color="primary",
                                                outline=True,
                                            ),
                                            dbc.Button(
                                                [
                                                    html.I(
                                                        className="bi bi-receipt me-2"
                                                    ),
                                                    "View All Transactions",
                                                ],
                                                href="/transactions",
                                                color="secondary",
                                                outline=True,
                                            ),
                                            dbc.Button(
                                                [
                                                    html.I(
                                                        className="bi bi-wallet2 me-2"
                                                    ),
                                                    "Manage Budgets",
                                                ],
                                                href="/budgets",
                                                color="secondary",
                                                outline=True,
                                            ),
                                        ],
                                        className="w-100",
                                    ),
                                ]
                            )
                        )
                    )
                ]
            ),
        ]
    )


def create_category_bar_chart(df):
    if df is None or df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No transactions this month",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray"),
        )
        fig.update_layout(height=350)
        return fig

    CATEGORY_COLORS = {
        "Rent": "#1f77b4",  # blue (Plotly 1)
        "Groceries & Living": "#d62728",  # red (Plotly 2)
        "Phone Bill": "#17becf",  # cyan-like blue (Plotly 10, lighter than dark blue)
        "Transportation": "#bcbd22",  # lime / yellow-green (Plotly 8, replaces previous cyan)
        "Travel": "#ff7f0e",  # orange (Plotly 3)
        "Shopping": "#ffbc79",  # yellow/orange (Plotly 4, softer than previous)
        "Restaurants": "#3EB489",  # green (Plotly 5, mint-like)
        "Subscriptions": "#9467bd",  # purple (Plotly 6, light viola tone)
        "Quorum": "#5dade2",  # light blue (keep similar)
        "Unexpected": "#7f7f7f",  # gray (Plotly neutral)
        "Taxes": "#2e2e2e",  # dark gray (kept)
    }

    max_value = df["total_eur"].max()

    fig = px.bar(
        df,
        y="category",
        x="total_eur",
        text="total_eur",
        color="category",
        color_discrete_map=CATEGORY_COLORS,
        orientation="h",
    )

    fig.update_traces(texttemplate="€%{text:.2f}", textposition="outside")

    fig.update_layout(
        height=350,
        margin=dict(t=20, b=20, l=20, r=20),
        xaxis_title="Total EUR",
        yaxis_title=None,
        showlegend=False,
        xaxis_range=[0, max_value * 1.1],
    )

    return fig


def create_recent_transactions_list(df):
    """Create list of recent transactions"""
    if df.empty:
        return html.P("No transactions yet", className="text-muted")

    items = []
    for _, row in df.iterrows():
        badge_color = "success" if row["is_quorum"] else "primary"
        badge_text = "Quorum" if row["is_quorum"] else row["category"]

        amount_display = (
            f"€{row['amount_eur']:.2f}"
            if not row["is_quorum"]
            else f"${row['amount_usd']:.2f}"
        )

        items.append(
            dbc.ListGroupItem(
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Strong(row["description"][:40]),
                                html.Br(),
                                html.Small(row["date"], className="text-muted"),
                            ],
                            width=7,
                        ),
                        dbc.Col(
                            dbc.Badge(badge_text, color=badge_color),
                            width=3,
                        ),
                        dbc.Col(
                            html.Strong(amount_display),
                            width=2,
                            className="text-end",
                        ),
                    ]
                )
            )
        )

    return dbc.ListGroup(items, flush=True)


@callback(
    Output("current-month", "data"),
    [Input("prev-month", "n_clicks"), Input("next-month", "n_clicks")],
    State("current-month", "data"),
    prevent_initial_call=True,
)
def change_month(prev_clicks, next_clicks, current):
    year = current["year"]
    month = current["month"]

    if not dash.ctx.triggered_id:
        return current

    if dash.ctx.triggered_id == "prev-month":
        month -= 1
        if month == 0:
            month = 12
            year -= 1

    if dash.ctx.triggered_id == "next-month":
        month += 1
        if month == 13:
            month = 1
            year += 1

    return {"year": year, "month": month}


@callback(
    Output("dashboard-content", "children"),
    Input("current-month", "data"),
)
def update_dashboard(current):
    return render_dashboard(current["year"], current["month"])
