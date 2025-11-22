"""
Dashboard Home Page
Overview of finances for current month
"""

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import calendar
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
          AND is_quorum = FALSE
    """,
        (first_day, last_day),
    )[0][0]

    quorum_spending = db.fetch_all(
        """
        SELECT COALESCE(SUM(amount_usd), 0)
        FROM transactions
        WHERE date BETWEEN ? AND ?
          AND is_quorum = TRUE
    """,
        (first_day, last_day),
    )[0][0]

    your_eur = db.fetch_all(
        """
        SELECT COALESCE(SUM(amount_eur), 0)
        FROM transactions
        WHERE date BETWEEN ? AND ?
          AND is_quorum = FALSE
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
          AND is_quorum = FALSE
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
    year = today.year
    month = today.month
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

    return dbc.Container(
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
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H6(
                                                "Your Spending",
                                                className="text-muted mb-2",
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
                                ],
                                className="h-100",
                            )
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
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
                                                "USD transactions",
                                                className="text-muted",
                                            ),
                                        ]
                                    )
                                ],
                                className="h-100",
                            )
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H6(
                                                "Total Credit Card",
                                                className="text-muted mb-2",
                                            ),
                                            html.H3(
                                                f"${summary['total_spending_usd']:,.2f}",
                                                className="mb-0",
                                            ),
                                            html.Small(
                                                "Total USD charged",
                                                className="text-muted",
                                            ),
                                        ]
                                    )
                                ],
                                className="h-100",
                            )
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H6(
                                                "Need Review",
                                                className="text-muted mb-2",
                                            ),
                                            html.H3(
                                                str(uncategorized_count),
                                                className="mb-0 text-warning"
                                                if uncategorized_count > 0
                                                else "mb-0",
                                            ),
                                            html.Small(
                                                "Uncategorized transactions",
                                                className="text-muted",
                                            ),
                                        ]
                                    )
                                ],
                                className="h-100",
                                color="warning" if uncategorized_count > 0 else None,
                                outline=True,
                            )
                        ],
                        width=3,
                    ),
                ],
                className="mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader("Spending by Category (EUR)"),
                                    dbc.CardBody(
                                        [
                                            dcc.Graph(
                                                id="category-pie-chart",
                                                figure=create_category_pie_chart(
                                                    summary["category_breakdown"]
                                                ),
                                                config={"displayModeBar": False},
                                            )
                                        ]
                                    ),
                                ]
                            )
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader("Recent Transactions"),
                                    dbc.CardBody(
                                        [create_recent_transactions_list(recent_df)],
                                        style={
                                            "maxHeight": "400px",
                                            "overflowY": "auto",
                                        },
                                    ),
                                ]
                            )
                        ],
                        width=6,
                    ),
                ],
                className="mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
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
                                ]
                            )
                        ]
                    )
                ]
            ),
        ],
        fluid=True,
    )


def create_category_pie_chart(df):
    """Create pie chart for category breakdown"""
    if df.empty:
        return go.Figure().add_annotation(
            text="No data available", showarrow=False, font=dict(size=16)
        )

    fig = px.pie(df, values="total_eur", names="category", title="", hole=0.4)

    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>€%{value:.2f}<br>%{percent}<extra></extra>",
    )

    fig.update_layout(showlegend=True, height=350, margin=dict(t=20, b=20, l=20, r=20))

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
                [
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
                                [
                                    dbc.Badge(
                                        badge_text, color=badge_color, className="me-2"
                                    )
                                ],
                                width=3,
                            ),
                            dbc.Col(
                                [
                                    html.Strong(
                                        amount_display, className="text-end d-block"
                                    )
                                ],
                                width=2,
                                className="text-end",
                            ),
                        ]
                    )
                ]
            )
        )

    return dbc.ListGroup(items, flush=True)
