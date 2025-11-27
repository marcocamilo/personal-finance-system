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


def get_billing_cycle_dates(year: int, month: int):
    """
    Calculate billing cycle dates for a given month.

    Pattern: Starts on 26th of the given month, ends based on days in NEXT month:
    - If next month has 31 days → ends on 25th
    - If next month has 30 days → ends on 24th
    - If next month has 29 days → ends on 23rd (Feb leap year)
    - If next month has 28 days → ends on 22nd (Feb normal)

    Examples:
    - Oct 26 → Nov 24 (Nov has 30 days)
    - Jul 26 → Aug 25 (Aug has 31 days)
    - Mar 26 → Apr 24 (Apr has 30 days)
    - Dec 26 → Jan 25 (Jan has 31 days)
    - Jan 26 → Feb 22 (Feb has 28 days in 2025)

    Args:
        year: Year to calculate cycle for
        month: Month to calculate cycle for (1-12)

    Returns:
        tuple: (cycle_start_date, cycle_end_date) as strings in YYYY-MM-DD format
    """
    # Start date: 26th of the given month
    cycle_start = datetime(year, month, 26)

    # Calculate next month
    if month == 12:
        next_month_year = year + 1
        next_month = 1
    else:
        next_month_year = year
        next_month = month + 1

    end_day = 25
    cycle_end = datetime(next_month_year, next_month, end_day)

    return (cycle_start.strftime("%Y-%m-%d"), cycle_end.strftime("%Y-%m-%d"))


def get_month_summary(year: int, month: int):
    """Get summary statistics for a specific month"""
    first_day = f"{year}-{month:02d}-01"
    last_day = f"{year}-{month:02d}-{calendar.monthrange(year, month)[1]}"

    # Your spending (EUR native)
    your_spending = db.fetch_all(
        """
        SELECT COALESCE(SUM(amount_usd), 0)
        FROM transactions
        WHERE date BETWEEN ? AND ?
          AND is_quorum = 0
    """,
        (first_day, last_day),
    )[0][0]

    # Quorum spending (USD native)
    quorum_spending = db.fetch_all(
        """
        SELECT COALESCE(SUM(amount_usd), 0)
        FROM transactions
        WHERE date BETWEEN ? AND ?
          AND is_quorum = 1
    """,
        (first_day, last_day),
    )[0][0]

    # Your EUR total
    your_eur = db.fetch_all(
        """
        SELECT COALESCE(SUM(amount_eur), 0)
        FROM transactions
        WHERE date BETWEEN ? AND ?
          AND is_quorum = 0
    """,
        (first_day, last_day),
    )[0][0]

    # Category breakdown (EUR only, excluding Quorum)
    category_breakdown = db.fetch_df(
        """
        SELECT 
            category,
            ROUND(SUM(amount_eur), 2) as total_eur,
            COUNT(*) as transaction_count
        FROM transactions
        WHERE date BETWEEN ? AND ?
          AND is_quorum = 0
          AND category IS NOT NULL
        GROUP BY category
        ORDER BY total_eur DESC
    """,
        (first_day, last_day),
    )

    # Get Quorum reimbursement status
    quorum_status = db.fetch_one(
        """
        SELECT 
            total_quorum_usd,
            reimbursed_amount_usd,
            reimbursement_date
        FROM reimbursements
        WHERE year = ? AND month = ?
    """,
        (year, month),
    )

    quorum_info = {
        "total": float(quorum_spending),
        "reimbursed": float(quorum_status[1])
        if quorum_status and quorum_status[1]
        else 0,
        "date": quorum_status[2] if quorum_status and quorum_status[2] else None,
        "pending": float(quorum_spending)
        - (float(quorum_status[1]) if quorum_status and quorum_status[1] else 0),
    }

    # FIXED: Get the billing cycle that ENDS within this month (most overlap)
    # For October, we want Sep 26 - Oct 24/25, not Oct 26 - Nov 24
    # So we calculate the cycle for the PREVIOUS month
    if month == 1:
        cycle_year = year - 1
        cycle_month = 12
    else:
        cycle_year = year
        cycle_month = month - 1

    cycle_start, cycle_end = get_billing_cycle_dates(cycle_year, cycle_month)

    # Your spending in this billing cycle
    cycle_your_spending = db.fetch_all(
        """
        SELECT COALESCE(SUM(amount_usd), 0)
        FROM transactions
        WHERE date BETWEEN ? AND ?
          AND is_quorum = 0
    """,
        (cycle_start, cycle_end),
    )[0][0]

    # Quorum spending in this billing cycle
    cycle_quorum_spending = db.fetch_all(
        """
        SELECT COALESCE(SUM(amount_usd), 0)
        FROM transactions
        WHERE date BETWEEN ? AND ?
          AND is_quorum = 1
    """,
        (cycle_start, cycle_end),
    )[0][0]

    return {
        "your_spending_usd": float(your_spending),
        "your_spending_eur": float(your_eur),
        "quorum_spending_usd": float(quorum_spending),
        "total_credit_card_usd": float(
            cycle_your_spending + cycle_quorum_spending
        ),  # Uses previous month's cycle (ends in current month)
        "net_you_pay_usd": float(your_spending + quorum_info["pending"]),
        "category_breakdown": category_breakdown,
        "quorum_info": quorum_info,
        "billing_cycle": {
            "start": cycle_start,
            "end": cycle_end,
            "year": cycle_year,
            "month": cycle_month,
            "your_usd": float(cycle_your_spending),
            "quorum_usd": float(cycle_quorum_spending),
        },
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

    # Format billing cycle dates for display
    cycle_start_date = datetime.strptime(summary["billing_cycle"]["start"], "%Y-%m-%d")
    cycle_end_date = datetime.strptime(summary["billing_cycle"]["end"], "%Y-%m-%d")
    cycle_display = (
        f"{cycle_start_date.strftime('%b %d')} - {cycle_end_date.strftime('%b %d')}"
    )

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2(f"{month_name} {year}", className="mb-0"),
                            html.P("Financial overview", className="text-muted"),
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
                            dbc.Alert(
                                [
                                    html.I(className="bi bi-exclamation-triangle me-2"),
                                    f"{uncategorized_count} transaction(s) need categorization. ",
                                    dbc.Button(
                                        "Review Now",
                                        href="/transactions",
                                        color="warning",
                                        size="sm",
                                        className="ms-2",
                                    ),
                                ],
                                color="warning",
                                className="mb-0",
                            )
                        ]
                    )
                ],
                className="mb-4",
            )
            if uncategorized_count > 0
            else None,
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
                                        f"Pending: ${summary['quorum_info']['pending']:,.2f}"
                                        if summary["quorum_info"]["pending"] > 0
                                        else "Reimbursed ✓",
                                        className="text-muted",
                                    ),
                                ]
                            ),
                            color="success"
                            if summary["quorum_info"]["pending"] == 0
                            else None,
                            outline=True,
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
                                        f"${summary['total_credit_card_usd']:,.2f}",
                                        className="mb-0",
                                    ),
                                    html.Small(
                                        f"Billing cycle: {cycle_display}",
                                        className="text-muted",
                                    ),
                                ]
                            ),
                            color="muted",
                            outline=True,
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
        "Rent": "#1f77b4",
        "Groceries & Living": "#d62728",
        "Phone Bill": "#17becf",
        "Transportation": "#bcbd22",
        "Travel": "#ff7f0e",
        "Shopping": "#ffbc79",
        "Restaurants": "#3EB489",
        "Subscriptions": "#9467bd",
        "Quorum": "#5dade2",
        "Unexpected": "#7f7f7f",
        "Taxes": "#2e2e2e",
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
        xaxis_range=[0, max_value * 1.15],
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
