"""
Analytics Dashboard
Comprehensive spending analysis, trends, and insights
"""

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate

from database.db import db

dash.register_page(__name__, path="/analytics", title="Analytics")

COLORS = {
    "Needs": "#3498db",
    "Wants": "#e74c3c",
    "Savings": "#2ecc71",
    "Unexpected": "#DBE2E9",
    "Additional": "#f39c12",
    "Income": "#1abc9c",
}

BUDGET_TYPE_ORDER = ["Needs", "Wants", "Savings", "Unexpected", "Additional"]


def get_date_range(preset: str, start_date: str = None, end_date: str = None):
    """Calculate date range based on preset or custom dates."""
    today = datetime.now()

    if preset == "custom" and start_date and end_date:
        return start_date, end_date

    if preset == "last_month":
        first = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        last = today.replace(day=1) - timedelta(days=1)
    elif preset == "last_3_months":
        first = today.replace(day=1) - relativedelta(months=2)
        last = today
    elif preset == "last_6_months":
        first = today.replace(day=1) - relativedelta(months=5)
        last = today
    elif preset == "this_year":
        first = today.replace(month=1, day=1)
        last = today
    elif preset == "all_time":
        first = datetime(2020, 1, 1)
        last = today
    else:
        first = today.replace(day=1) - relativedelta(months=2)
        last = today

    return first.strftime("%Y-%m-%d"), last.strftime("%Y-%m-%d")


def get_spending_data(start_date: str, end_date: str):
    """Fetch all transaction data for the date range."""
    return db.fetch_df(
        """
        SELECT 
            date,
            strftime('%Y-%m', date) as month,
            budget_type,
            category,
            subcategory,
            amount_eur,
            description
        FROM transactions
        WHERE date BETWEEN ? AND ?
            AND is_quorum = 0
            AND budget_type IS NOT NULL
            AND budget_type != 'Income'
        ORDER BY date
        """,
        (start_date, end_date),
    )


def get_budget_data(start_date: str, end_date: str):
    """Fetch budget data for the date range."""
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    budgets = []
    current = start_dt.replace(day=1)

    while current <= end_dt:
        month_budget = db.fetch_df(
            """
            SELECT budget_type, category, budgeted_amount
            FROM monthly_budgets
            WHERE year = ? AND month = ?
            """,
            (current.year, current.month),
        )

        if month_budget.empty:
            template_id = db.fetch_one(
                "SELECT id FROM budget_templates WHERE is_active = 1"
            )
            if template_id:
                month_budget = db.fetch_df(
                    """
                    SELECT budget_type, category, budgeted_amount
                    FROM template_categories
                    WHERE template_id = ?
                    """,
                    (template_id[0],),
                )

        if not month_budget.empty:
            month_budget["month"] = current.strftime("%Y-%m")
            budgets.append(month_budget)

        current += relativedelta(months=1)

    if budgets:
        return pd.concat(budgets, ignore_index=True)
    return pd.DataFrame()


def get_income_data(start_date: str, end_date: str):
    """Fetch income data for the date range."""
    return db.fetch_df(
        """
        SELECT 
            date,
            strftime('%Y-%m', date) as month,
            amount_eur,
            description
        FROM income_transactions
        WHERE date BETWEEN ? AND ?
        ORDER BY date
        """,
        (start_date, end_date),
    )


def calculate_monthly_spending(df: pd.DataFrame, group_by: str = "budget_type"):
    """Calculate spending aggregated by month and grouping."""
    if df.empty:
        return pd.DataFrame()

    return df.groupby(["month", group_by])["amount_eur"].sum().reset_index()


def calculate_spending_drift(df: pd.DataFrame, months: int = 6):
    """Detect long-term spending drift by comparing recent to historical averages."""
    if df.empty or len(df["month"].unique()) < 3:
        return None

    monthly = df.groupby("month")["amount_eur"].sum().reset_index()
    monthly = monthly.sort_values("month")

    if len(monthly) < 3:
        return None

    mid = len(monthly) // 2
    early_avg = monthly.iloc[:mid]["amount_eur"].mean()
    recent_avg = monthly.iloc[mid:]["amount_eur"].mean()

    drift_pct = ((recent_avg - early_avg) / early_avg * 100) if early_avg > 0 else 0

    return {
        "early_avg": early_avg,
        "recent_avg": recent_avg,
        "drift_pct": drift_pct,
        "direction": "up" if drift_pct > 5 else "down" if drift_pct < -5 else "stable",
    }


def calculate_month_variance(df: pd.DataFrame):
    """Calculate month-to-month spending variance by category."""
    if df.empty:
        return pd.DataFrame()

    monthly = df.groupby(["month", "budget_type"])["amount_eur"].sum().reset_index()

    variance_data = []
    for budget_type in monthly["budget_type"].unique():
        type_data = monthly[monthly["budget_type"] == budget_type].sort_values("month")
        if len(type_data) >= 2:
            amounts = type_data["amount_eur"].values
            avg = amounts.mean()
            std = amounts.std()
            cv = (std / avg * 100) if avg > 0 else 0

            mom_changes = []
            for i in range(1, len(amounts)):
                if amounts[i - 1] > 0:
                    change = (amounts[i] - amounts[i - 1]) / amounts[i - 1] * 100
                    mom_changes.append(change)

            max_change = max(mom_changes, key=abs) if mom_changes else 0

            variance_data.append(
                {
                    "budget_type": budget_type,
                    "avg_monthly": avg,
                    "std_dev": std,
                    "cv_pct": cv,
                    "max_mom_change": max_change,
                    "volatility": "High" if cv > 30 else "Medium" if cv > 15 else "Low",
                }
            )

    return pd.DataFrame(variance_data)


def get_top_merchants(df: pd.DataFrame, limit: int = 10):
    """Get top merchants by total spending."""
    if df.empty or "description" not in df.columns:
        return pd.DataFrame()

    merchant_df = df[df["description"].notna() & (df["description"] != "")]
    if merchant_df.empty:
        return pd.DataFrame()

    merchants = (
        merchant_df.groupby("description")
        .agg(
            total_spent=("amount_eur", "sum"),
            transactions=("amount_eur", "count"),
            avg_transaction=("amount_eur", "mean"),
            categories=("category", lambda x: ", ".join(x.unique()[:3])),
        )
        .reset_index()
    )

    merchants = merchants.sort_values("total_spent", ascending=False).head(limit)
    merchants["rank"] = range(1, len(merchants) + 1)

    return merchants


def build_spending_trends_chart(df: pd.DataFrame, group_by: str = "budget_type"):
    """Build line chart showing spending trends over time."""
    if df.empty:
        return go.Figure().add_annotation(
            text="No spending data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )

    monthly = calculate_monthly_spending(df, group_by)
    if monthly.empty:
        return go.Figure()

    fig = px.line(
        monthly,
        x="month",
        y="amount_eur",
        color=group_by,
        markers=True,
        color_discrete_map=COLORS if group_by == "budget_type" else None,
    )

    fig.update_layout(
        title="Spending Trends Over Time",
        xaxis_title="Month",
        yaxis_title="Amount (€)",
        hovermode="x unified",
        legend_title=group_by.replace("_", " ").title(),
        template="plotly_white",
        height=400,
    )

    fig.update_traces(hovertemplate="%{y:,.2f}€")

    return fig


def build_category_breakdown_chart(df: pd.DataFrame):
    """Build bar chart showing breakdown by budget type."""
    if df.empty:
        return go.Figure()

    totals = df.groupby("budget_type")["amount_eur"].sum().reset_index()
    totals = totals.sort_values("amount_eur", ascending=True)

    grand_total = totals["amount_eur"].sum()
    totals["percentage"] = totals["amount_eur"] / grand_total * 100

    fig = go.Figure()

    for _, row in totals.iterrows():
        fig.add_trace(
            go.Bar(
                y=[row["budget_type"]],
                x=[row["amount_eur"]],
                orientation="h",
                name=row["budget_type"],
                marker_color=COLORS.get(row["budget_type"], "#95a5a6"),
                text=f"€{row['amount_eur']:,.0f} ({row['percentage']:.1f}%)",
                textposition="auto",
                hovertemplate=f"{row['budget_type']}<br>€%{{x:,.2f}}<br>{row['percentage']:.1f}%<extra></extra>",
            )
        )

    fig.update_layout(
        title="Spending by Category",
        xaxis_title="Amount (€)",
        yaxis_title="",
        showlegend=False,
        template="plotly_white",
        height=300,
    )

    return fig


def build_budget_adherence_chart(spending_df: pd.DataFrame, budget_df: pd.DataFrame):
    """Build chart comparing budgeted vs actual spending by month."""
    if spending_df.empty or budget_df.empty:
        return go.Figure()

    actual = spending_df.groupby("month")["amount_eur"].sum().reset_index()
    actual.columns = ["month", "actual"]

    expense_budget = budget_df[~budget_df["budget_type"].isin(["Income", "Savings"])]
    budgeted = expense_budget.groupby("month")["budgeted_amount"].sum().reset_index()
    budgeted.columns = ["month", "budgeted"]

    comparison = actual.merge(budgeted, on="month", how="outer").fillna(0)
    comparison = comparison.sort_values("month")

    comparison["diff"] = comparison["budgeted"] - comparison["actual"]
    comparison["status"] = comparison["diff"].apply(
        lambda x: "Under Budget" if x >= 0 else "Over Budget"
    )

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=comparison["month"],
            y=comparison["budgeted"],
            name="Budgeted",
            marker_color="#3498db",
            opacity=0.7,
        )
    )

    fig.add_trace(
        go.Bar(
            x=comparison["month"],
            y=comparison["actual"],
            name="Actual",
            marker_color=comparison["diff"].apply(
                lambda x: "#2ecc71" if x >= 0 else "#e74c3c"
            ),
        )
    )

    if len(comparison) >= 2:
        fig.add_trace(
            go.Scatter(
                x=comparison["month"],
                y=comparison["actual"],
                mode="lines",
                name="Trend",
                line=dict(color="#95a5a6", dash="dot"),
            )
        )

    fig.update_layout(
        title="Budget vs Actual Spending",
        xaxis_title="Month",
        yaxis_title="Amount (€)",
        barmode="group",
        template="plotly_white",
        height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )

    return fig


def build_merchant_distribution_chart(df: pd.DataFrame):
    """Build pie chart showing merchant distribution."""
    merchants = get_top_merchants(df, limit=8)
    if merchants.empty:
        return go.Figure()

    total = df["amount_eur"].sum()
    top_total = merchants["total_spent"].sum()
    other = total - top_total

    if other > 0:
        merchants = pd.concat(
            [merchants, pd.DataFrame([{"description": "Other", "total_spent": other}])],
            ignore_index=True,
        )

    fig = px.pie(
        merchants,
        values="total_spent",
        names="description",
        hole=0.4,
    )

    fig.update_layout(
        title="Spending Distribution by Merchant",
        template="plotly_white",
        height=350,
    )

    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="%{label}<br>€%{value:,.2f}<br>%{percent}<extra></extra>",
    )

    return fig


def build_variance_chart(variance_df: pd.DataFrame):
    """Build chart showing month-to-month variance by category."""
    if variance_df.empty:
        return go.Figure()

    variance_df = variance_df.sort_values("cv_pct", ascending=True)

    colors = variance_df["volatility"].map(
        {
            "Low": "#2ecc71",
            "Medium": "#f39c12",
            "High": "#e74c3c",
        }
    )

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            y=variance_df["budget_type"],
            x=variance_df["cv_pct"],
            orientation="h",
            marker_color=colors,
            text=variance_df["volatility"],
            textposition="auto",
            hovertemplate=(
                "%{y}<br>"
                "Variability: %{x:.1f}%<br>"
                "Avg Monthly: €%{customdata[0]:,.0f}<br>"
                "Max Change: %{customdata[1]:+.1f}%<extra></extra>"
            ),
            customdata=variance_df[["avg_monthly", "max_mom_change"]].values,
        )
    )

    fig.update_layout(
        title="Spending Volatility by Category",
        xaxis_title="Coefficient of Variation (%)",
        yaxis_title="",
        template="plotly_white",
        height=250,
    )

    return fig


def layout():
    today = datetime.now()
    default_start = (today.replace(day=1) - relativedelta(months=5)).strftime(
        "%Y-%m-%d"
    )
    default_end = today.strftime("%Y-%m-%d")

    return dbc.Container(
        [
            dcc.Store(id="analytics-data-store"),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2("Analytics Dashboard", className="mb-0"),
                            html.P(
                                "Deep insights into your spending patterns",
                                className="text-muted",
                            ),
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            dbc.ButtonGroup(
                                [
                                    dbc.Button(
                                        [
                                            html.I(className="bi bi-download me-2"),
                                            "Export CSV",
                                        ],
                                        id="export-csv-btn",
                                        color="secondary",
                                        outline=True,
                                        size="sm",
                                    ),
                                    dbc.Button(
                                        [
                                            html.I(className="bi bi-file-pdf me-2"),
                                            "Export PDF",
                                        ],
                                        id="export-pdf-btn",
                                        color="secondary",
                                        outline=True,
                                        size="sm",
                                    ),
                                ]
                            ),
                            dcc.Download(id="download-csv"),
                            dcc.Download(id="download-pdf"),
                        ],
                        width=6,
                        className="text-end",
                    ),
                ],
                className="mb-4",
            ),
            dbc.Card(
                dbc.CardBody(
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Time Range", className="fw-bold"),
                                    dcc.Dropdown(
                                        id="time-range-preset",
                                        options=[
                                            {
                                                "label": "Last Month",
                                                "value": "last_month",
                                            },
                                            {
                                                "label": "Last 3 Months",
                                                "value": "last_3_months",
                                            },
                                            {
                                                "label": "Last 6 Months",
                                                "value": "last_6_months",
                                            },
                                            {
                                                "label": "This Year",
                                                "value": "this_year",
                                            },
                                            {"label": "All Time", "value": "all_time"},
                                            {
                                                "label": "Custom Range",
                                                "value": "custom",
                                            },
                                        ],
                                        value="this_year",
                                        clearable=False,
                                    ),
                                ],
                                width=3,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("Start Date"),
                                    dbc.Input(
                                        id="custom-start-date",
                                        type="date",
                                        value=default_start,
                                        disabled=True,
                                    ),
                                ],
                                width=2,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("End Date"),
                                    dbc.Input(
                                        id="custom-end-date",
                                        type="date",
                                        value=default_end,
                                        disabled=True,
                                    ),
                                ],
                                width=2,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("Group By"),
                                    dcc.Dropdown(
                                        id="group-by-selector",
                                        options=[
                                            {
                                                "label": "Budget Type",
                                                "value": "budget_type",
                                            },
                                            {"label": "Category", "value": "category"},
                                            {"label": "Merchant", "value": "merchant"},
                                        ],
                                        value="budget_type",
                                        clearable=False,
                                    ),
                                ],
                                width=2,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label(" ", className="d-block"),
                                    dbc.Button(
                                        [
                                            html.I(
                                                className="bi bi-arrow-clockwise me-2"
                                            ),
                                            "Refresh",
                                        ],
                                        id="refresh-analytics-btn",
                                        color="primary",
                                        className="w-100",
                                    ),
                                ],
                                width=2,
                            ),
                        ]
                    )
                ),
                className="mb-4",
            ),
            html.Div(id="summary-cards-container", className="mb-4"),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Spending Trends"),
                                dbc.CardBody(dcc.Graph(id="spending-trends-chart")),
                            ]
                        ),
                        width=8,
                    ),
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Category Breakdown"),
                                dbc.CardBody(dcc.Graph(id="category-breakdown-chart")),
                            ]
                        ),
                        width=4,
                    ),
                ],
                className="mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Budget Adherence"),
                                dbc.CardBody(dcc.Graph(id="budget-adherence-chart")),
                            ]
                        ),
                        width=6,
                    ),
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Merchant Distribution"),
                                dbc.CardBody(
                                    dcc.Graph(id="merchant-distribution-chart")
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
                            [
                                dbc.CardHeader("Top Merchants"),
                                dbc.CardBody(html.Div(id="top-merchants-table")),
                            ]
                        ),
                        width=7,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader("Month-to-Month Variance"),
                                    dbc.CardBody(dcc.Graph(id="variance-chart")),
                                ],
                                className="mb-3",
                            ),
                            dbc.Card(
                                [
                                    dbc.CardHeader("Spending Drift Detection"),
                                    dbc.CardBody(html.Div(id="drift-analysis")),
                                ]
                            ),
                        ],
                        width=5,
                    ),
                ],
                className="mb-4",
            ),
        ],
        fluid=True,
    )


@callback(
    [Output("custom-start-date", "disabled"), Output("custom-end-date", "disabled")],
    Input("time-range-preset", "value"),
)
def toggle_custom_dates(preset):
    is_custom = preset == "custom"
    return not is_custom, not is_custom


@callback(
    [
        Output("summary-cards-container", "children"),
        Output("spending-trends-chart", "figure"),
        Output("category-breakdown-chart", "figure"),
        Output("budget-adherence-chart", "figure"),
        Output("merchant-distribution-chart", "figure"),
        Output("top-merchants-table", "children"),
        Output("variance-chart", "figure"),
        Output("drift-analysis", "children"),
        Output("analytics-data-store", "data"),
    ],
    [
        Input("refresh-analytics-btn", "n_clicks"),
        Input("time-range-preset", "value"),
    ],
    [
        State("custom-start-date", "value"),
        State("custom-end-date", "value"),
        State("group-by-selector", "value"),
    ],
)
def update_analytics(n_clicks, preset, start_date, end_date, group_by):
    start, end = get_date_range(preset, start_date, end_date)

    spending_df = get_spending_data(start, end)
    budget_df = get_budget_data(start, end)
    income_df = get_income_data(start, end)

    total_spending = spending_df["amount_eur"].sum() if not spending_df.empty else 0
    total_income = income_df["amount_eur"].sum() if not income_df.empty else 0
    num_transactions = len(spending_df)
    avg_transaction = total_spending / num_transactions if num_transactions > 0 else 0

    num_months = len(spending_df["month"].unique()) if not spending_df.empty else 1
    avg_monthly = total_spending / num_months if num_months > 0 else 0

    summary_cards = dbc.Row(
        [
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H6("Total Spending", className="text-muted mb-2"),
                            html.H3(
                                f"€{total_spending:,.2f}", className="mb-0 text-danger"
                            ),
                        ]
                    ),
                    className="h-100",
                ),
                width=3,
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H6("Total Income", className="text-muted mb-2"),
                            html.H3(
                                f"€{total_income:,.2f}", className="mb-0 text-success"
                            ),
                        ]
                    ),
                    className="h-100",
                ),
                width=3,
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H6(
                                "Avg Monthly Spending", className="text-muted mb-2"
                            ),
                            html.H3(f"€{avg_monthly:,.2f}", className="mb-0"),
                        ]
                    ),
                    className="h-100",
                ),
                width=3,
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H6("Transactions", className="text-muted mb-2"),
                            html.H3(f"{num_transactions:,}", className="mb-0"),
                            html.Small(
                                f"Avg: €{avg_transaction:.2f}", className="text-muted"
                            ),
                        ]
                    ),
                    className="h-100",
                ),
                width=3,
            ),
        ]
    )

    trends_chart = build_spending_trends_chart(spending_df, group_by)
    category_chart = build_category_breakdown_chart(spending_df)
    budget_chart = build_budget_adherence_chart(spending_df, budget_df)
    merchant_dist_chart = build_merchant_distribution_chart(spending_df)

    merchants = get_top_merchants(spending_df, limit=10)
    if not merchants.empty:
        merchants_table = dbc.Table(
            [
                html.Thead(
                    html.Tr(
                        [
                            html.Th("#", style={"width": "40px"}),
                            html.Th("Merchant"),
                            html.Th("Total Spent", className="text-end"),
                            html.Th("Transactions", className="text-center"),
                            html.Th("Avg/Transaction", className="text-end"),
                        ]
                    )
                ),
                html.Tbody(
                    [
                        html.Tr(
                            [
                                html.Td(row["rank"]),
                                html.Td(
                                    [
                                        html.Strong(row["description"]),
                                        html.Br(),
                                        html.Small(
                                            row["categories"], className="text-muted"
                                        ),
                                    ]
                                ),
                                html.Td(
                                    f"€{row['total_spent']:,.2f}", className="text-end"
                                ),
                                html.Td(
                                    str(row["transactions"]), className="text-center"
                                ),
                                html.Td(
                                    f"€{row['avg_transaction']:.2f}",
                                    className="text-end",
                                ),
                            ]
                        )
                        for _, row in merchants.iterrows()
                    ]
                ),
            ],
            striped=True,
            hover=True,
            size="sm",
        )
    else:
        merchants_table = dbc.Alert("No merchant data available", color="info")

    variance_df = calculate_month_variance(spending_df)
    variance_chart = build_variance_chart(variance_df)

    drift = calculate_spending_drift(spending_df)
    if drift:
        if drift["direction"] == "up":
            drift_icon = "bi-graph-up-arrow"
            drift_color = "text-danger"
            drift_text = f"Spending increased by {drift['drift_pct']:.1f}%"
        elif drift["direction"] == "down":
            drift_icon = "bi-graph-down-arrow"
            drift_color = "text-success"
            drift_text = f"Spending decreased by {abs(drift['drift_pct']):.1f}%"
        else:
            drift_icon = "bi-dash"
            drift_color = "text-muted"
            drift_text = "Spending is stable"

        drift_content = html.Div(
            [
                html.Div(
                    [
                        html.I(className=f"bi {drift_icon} me-2 fs-4 {drift_color}"),
                        html.Span(drift_text, className=f"fs-5 {drift_color}"),
                    ],
                    className="mb-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Small(
                                    "Early Period Avg", className="text-muted d-block"
                                ),
                                html.Strong(f"€{drift['early_avg']:,.0f}/mo"),
                            ],
                            width=6,
                        ),
                        dbc.Col(
                            [
                                html.Small(
                                    "Recent Period Avg", className="text-muted d-block"
                                ),
                                html.Strong(f"€{drift['recent_avg']:,.0f}/mo"),
                            ],
                            width=6,
                        ),
                    ]
                ),
            ]
        )
    else:
        drift_content = dbc.Alert(
            "Need at least 3 months of data for drift analysis",
            color="info",
            className="mb-0",
        )

    store_data = {
        "start_date": start,
        "end_date": end,
        "total_spending": total_spending,
        "total_income": total_income,
    }

    return (
        summary_cards,
        trends_chart,
        category_chart,
        budget_chart,
        merchant_dist_chart,
        merchants_table,
        variance_chart,
        drift_content,
        store_data,
    )


@callback(
    Output("download-csv", "data"),
    Input("export-csv-btn", "n_clicks"),
    [State("analytics-data-store", "data")],
    prevent_initial_call=True,
)
def export_csv(n_clicks, store_data):
    if not n_clicks or not store_data:
        raise PreventUpdate

    start = store_data.get("start_date")
    end = store_data.get("end_date")

    df = get_spending_data(start, end)
    if df.empty:
        raise PreventUpdate

    return dcc.send_data_frame(
        df.to_csv,
        f"spending_export_{start}_to_{end}.csv",
        index=False,
    )


@callback(
    Output("download-pdf", "data"),
    Input("export-pdf-btn", "n_clicks"),
    [State("analytics-data-store", "data")],
    prevent_initial_call=True,
)
def export_pdf(n_clicks, store_data):
    """Export analytics report as PDF (generates HTML for now)."""
    if not n_clicks or not store_data:
        raise PreventUpdate

    start = store_data.get("start_date")
    end = store_data.get("end_date")
    total_spending = store_data.get("total_spending", 0)
    total_income = store_data.get("total_income", 0)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Analytics Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 40px; }}
            h1 {{ color: #2c3e50; }}
            .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
            .card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; flex: 1; }}
            .amount {{ font-size: 24px; font-weight: bold; }}
            .spending {{ color: #e74c3c; }}
            .income {{ color: #2ecc71; }}
        </style>
    </head>
    <body>
        <h1>Analytics Report</h1>
        <p>Period: {start} to {end}</p>
        <div class="summary">
            <div class="card">
                <div>Total Spending</div>
                <div class="amount spending">€{total_spending:,.2f}</div>
            </div>
            <div class="card">
                <div>Total Income</div>
                <div class="amount income">€{total_income:,.2f}</div>
            </div>
            <div class="card">
                <div>Net</div>
                <div class="amount">€{total_income - total_spending:,.2f}</div>
            </div>
        </div>
        <p><em>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M")}</em></p>
    </body>
    </html>
    """

    return dict(
        content=html_content,
        filename=f"analytics_report_{start}_to_{end}.html",
    )
