"""
Savings Page
Manage savings goals, track progress, and view savings buckets
"""

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate

from database.db import db

dash.register_page(__name__, path="/savings", title="Savings")


def get_savings_buckets():
    buckets = db.fetch_df("""
        SELECT 
            sb.id,
            sb.name,
            sb.currency,
            sb.goal_amount,
            sb.start_amount,
            sb.target_date,
            sb.is_active,
            sb.is_ongoing,
            COALESCE(SUM(
                CASE 
                    WHEN st.transaction_type = 'credit' THEN st.amount
                    WHEN st.transaction_type = 'debit' THEN -st.amount
                    ELSE 0
                END
            ), 0) as transactions_total
        FROM savings_buckets sb
        LEFT JOIN savings_transactions st ON sb.id = st.bucket_id
        GROUP BY sb.id, sb.name, sb.currency, sb.goal_amount, sb.start_amount, sb.target_date, sb.is_active, sb.is_ongoing
        ORDER BY sb.is_active DESC, sb.created_at DESC
    """)
    if not buckets.empty:
        buckets["current_amount"] = buckets["start_amount"] + buckets["transactions_total"]
    return buckets


def get_contribution_stats(bucket_id: int, months: int = 3):
    """Calculate average monthly contribution for a bucket"""
    cutoff_date = (datetime.now() - relativedelta(months=months)).strftime("%Y-%m-%d")
    
    result = db.fetch_one("""
        SELECT 
            COALESCE(SUM(CASE WHEN transaction_type = 'credit' THEN amount ELSE 0 END), 0) as total_credits,
            COUNT(DISTINCT strftime('%Y-%m', date)) as active_months
        FROM savings_transactions
        WHERE bucket_id = ? AND date >= ? AND transaction_type = 'credit'
    """, (bucket_id, cutoff_date))
    
    if result and result[1] and result[1] > 0:
        return result[0] / result[1]
    return 0


def calculate_projection(current_amount: float, goal_amount: float, avg_monthly: float, target_date: str = None):
    """Calculate timeline projection for reaching goal"""
    if goal_amount is None or goal_amount <= 0:
        return None
    
    remaining = goal_amount - current_amount
    if remaining <= 0:
        return {"status": "completed", "months_ahead": 0}
    
    if avg_monthly <= 0:
        return {"status": "no_data", "months_to_goal": None}
    
    months_to_goal = remaining / avg_monthly
    projected_date = datetime.now() + relativedelta(months=int(months_to_goal))
    
    result = {
        "months_to_goal": months_to_goal,
        "projected_date": projected_date.strftime("%b %Y"),
        "avg_monthly": avg_monthly
    }
    
    if target_date:
        target = datetime.strptime(target_date, "%Y-%m-%d")
        months_until_target = (target.year - datetime.now().year) * 12 + (target.month - datetime.now().month)
        
        if months_to_goal <= months_until_target:
            result["status"] = "on_track"
            result["months_ahead"] = months_until_target - months_to_goal
        else:
            result["status"] = "behind"
            result["months_behind"] = months_to_goal - months_until_target
    else:
        result["status"] = "on_track"
    
    return result


def get_projection_chart_data(bucket_id: int, current_amount: float, goal_amount: float, avg_monthly: float):
    """Generate data for projection chart"""
    history = db.fetch_df("""
        SELECT 
            strftime('%Y-%m', date) as month,
            SUM(CASE WHEN transaction_type = 'credit' THEN amount 
                     WHEN transaction_type = 'debit' THEN -amount 
                     ELSE 0 END) as net_amount
        FROM savings_transactions
        WHERE bucket_id = ?
        GROUP BY strftime('%Y-%m', date)
        ORDER BY month
    """, (bucket_id,))
    
    historical_months = []
    historical_balances = []
    
    if not history.empty:
        running_balance = 0
        start_amount = db.fetch_one(
            "SELECT start_amount FROM savings_buckets WHERE id = ?", (bucket_id,)
        )
        running_balance = start_amount[0] if start_amount else 0
        
        for _, row in history.iterrows():
            running_balance += row["net_amount"]
            historical_months.append(row["month"])
            historical_balances.append(running_balance)
    
    projected_months = []
    projected_balances = []
    
    if avg_monthly > 0 and goal_amount and goal_amount > current_amount:
        balance = current_amount
        current_date = datetime.now()
        
        for i in range(1, 25):
            if balance >= goal_amount:
                break
            future_date = current_date + relativedelta(months=i)
            balance += avg_monthly
            projected_months.append(future_date.strftime("%Y-%m"))
            projected_balances.append(min(balance, goal_amount))
    
    return {
        "historical_months": historical_months,
        "historical_balances": historical_balances,
        "projected_months": projected_months,
        "projected_balances": projected_balances,
        "goal": goal_amount
    }


def layout():
    buckets = get_savings_buckets()

    total_saved_eur = buckets[buckets["currency"] == "EUR"]["current_amount"].sum() if not buckets.empty else 0
    total_saved_usd = buckets[buckets["currency"] == "USD"]["current_amount"].sum() if not buckets.empty else 0
    total_goal_eur = buckets[(buckets["currency"] == "EUR") & (buckets["goal_amount"].notna())]["goal_amount"].sum() if not buckets.empty else 0
    total_goal_usd = buckets[(buckets["currency"] == "USD") & (buckets["goal_amount"].notna())]["goal_amount"].sum() if not buckets.empty else 0

    active_count = len(buckets[buckets["is_active"] == 1]) if not buckets.empty else 0
    
    completed_count = 0
    if not buckets.empty:
        goal_buckets = buckets[buckets["goal_amount"].notna() & (buckets["goal_amount"] > 0)]
        if not goal_buckets.empty:
            completed_count = len(goal_buckets[goal_buckets["current_amount"] >= goal_buckets["goal_amount"]])

    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2("Savings Goals", className="mb-0"),
                            html.P("Track your savings progress", className="text-muted"),
                        ],
                        width=8,
                    ),
                    dbc.Col(
                        dbc.Button(
                            [html.I(className="bi bi-plus-circle me-2"), "New Goal"],
                            id="new-goal-btn",
                            color="primary",
                        ),
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
                                    html.H6("Total Saved (EUR)", className="text-muted mb-2"),
                                    html.H3(f"€{total_saved_eur:,.2f}", className="mb-0 text-success"),
                                    html.Small(f"Goal: €{total_goal_eur:,.2f}", className="text-muted") if total_goal_eur > 0 else html.Small("No goals set", className="text-muted"),
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
                                    html.H6("Total Saved (USD)", className="text-muted mb-2"),
                                    html.H3(f"${total_saved_usd:,.2f}", className="mb-0 text-success"),
                                    html.Small(f"Goal: ${total_goal_usd:,.2f}", className="text-muted") if total_goal_usd > 0 else html.Small("No goals set", className="text-muted"),
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
                                    html.H6("Active Goals", className="text-muted mb-2"),
                                    html.H3(str(active_count), className="mb-0"),
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
                                    html.H6("Goals Completed", className="text-muted mb-2"),
                                    html.H3(str(completed_count), className="mb-0 text-success"),
                                ]
                            ),
                            className="h-100",
                        ),
                        width=3,
                    ),
                ],
                className="mb-4",
            ),
            html.Div(id="savings-buckets-container"),
            dbc.Modal(
                [
                    dbc.ModalHeader("Create New Savings Goal"),
                    dbc.ModalBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Goal Name *"),
                                            dbc.Input(id="new-goal-name", placeholder="e.g., Emergency Fund"),
                                        ]
                                    )
                                ],
                                className="mb-3",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Currency *"),
                                            dcc.Dropdown(
                                                id="new-goal-currency",
                                                options=[
                                                    {"label": "EUR (€)", "value": "EUR"},
                                                    {"label": "USD ($)", "value": "USD"},
                                                ],
                                                value="EUR",
                                                clearable=False,
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Goal Type"),
                                            dcc.Dropdown(
                                                id="new-goal-type",
                                                options=[
                                                    {"label": "Fixed Goal", "value": "fixed"},
                                                    {"label": "Ongoing", "value": "ongoing"},
                                                ],
                                                value="fixed",
                                                clearable=False,
                                            ),
                                        ],
                                        width=6,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            html.Div(
                                id="goal-amount-section",
                                children=[
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Label("Goal Amount"),
                                                    dbc.Input(
                                                        id="new-goal-amount",
                                                        type="number",
                                                        step=0.01,
                                                        placeholder="10000.00",
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Label("Target Date (optional)"),
                                                    dbc.Input(id="new-goal-date", type="date"),
                                                ],
                                                width=6,
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                ],
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Starting Amount"),
                                            dbc.Input(
                                                id="new-goal-start",
                                                type="number",
                                                step=0.01,
                                                value=0,
                                                placeholder="0.00",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Monthly Contribution (optional)"),
                                            dbc.Input(
                                                id="new-goal-monthly",
                                                type="number",
                                                step=0.01,
                                                placeholder="500.00",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                ],
                                className="mb-3",
                            ),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button("Cancel", id="cancel-new-goal", color="secondary"),
                            dbc.Button("Create", id="save-new-goal", color="primary"),
                        ]
                    ),
                ],
                id="new-goal-modal",
                is_open=False,
            ),
            dbc.Modal(
                [
                    dbc.ModalHeader(id="transaction-modal-header"),
                    dbc.ModalBody([html.Div(id="transaction-form")]),
                    dbc.ModalFooter(
                        [
                            dbc.Button("Cancel", id="cancel-transaction", color="secondary"),
                            dbc.Button("Save", id="save-transaction", color="primary"),
                        ]
                    ),
                ],
                id="transaction-modal",
                is_open=False,
            ),
            dbc.Modal(
                [
                    dbc.ModalHeader(id="projection-modal-header"),
                    dbc.ModalBody([html.Div(id="projection-content")]),
                    dbc.ModalFooter(
                        dbc.Button("Close", id="close-projection", color="secondary"),
                    ),
                ],
                id="projection-modal",
                size="lg",
                is_open=False,
            ),
        ],
        fluid=True,
    )


@callback(
    Output("goal-amount-section", "style"),
    Input("new-goal-type", "value"),
)
def toggle_goal_amount_section(goal_type):
    if goal_type == "ongoing":
        return {"display": "none"}
    return {"display": "block"}


@callback(
    Output("new-goal-modal", "is_open"),
    [
        Input("new-goal-btn", "n_clicks"),
        Input("save-new-goal", "n_clicks"),
        Input("cancel-new-goal", "n_clicks"),
    ],
    [
        State("new-goal-name", "value"),
        State("new-goal-currency", "value"),
        State("new-goal-type", "value"),
        State("new-goal-amount", "value"),
        State("new-goal-start", "value"),
        State("new-goal-date", "value"),
        State("new-goal-monthly", "value"),
    ],
    prevent_initial_call=True,
)
def toggle_new_goal_modal(new_btn, save_btn, cancel_btn, name, currency, goal_type, amount, start, date, monthly):
    from dash import ctx

    trigger = ctx.triggered_id
    if not trigger:
        raise PreventUpdate
    
    if trigger == "new-goal-btn":
        return True
    
    if trigger == "save-new-goal":
        if name and currency:
            is_ongoing = 1 if goal_type == "ongoing" else 0
            goal_amount = None if goal_type == "ongoing" else (float(amount) if amount else None)
            target_date = None if goal_type == "ongoing" else date
            
            db.write_execute(
                """
                INSERT INTO savings_buckets (name, currency, goal_amount, start_amount, target_date, is_active, is_ongoing)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (name, currency, goal_amount, float(start or 0), target_date, is_ongoing),
            )
        return False
    
    if trigger == "cancel-new-goal":
        return False
    
    raise PreventUpdate


@callback(
    Output("savings-buckets-container", "children"),
    [Input("new-goal-modal", "is_open"), Input("transaction-modal", "is_open")],
)
def update_savings_buckets(new_goal_open, transaction_open):
    buckets = get_savings_buckets()
    if buckets.empty:
        return html.Div(
            dbc.Alert(
                [
                    html.H5("No Savings Goals Yet", className="alert-heading"),
                    html.P("Create your first savings goal to start tracking your progress!"),
                    html.P("Click the 'New Goal' button above to get started.", className="mb-0 text-muted"),
                ],
                color="info",
            )
        )

    cards = []
    for _, bucket in buckets.iterrows():
        bucket_id = int(bucket["id"])
        is_ongoing = bucket.get("is_ongoing", 0) == 1
        has_goal = bucket["goal_amount"] is not None and bucket["goal_amount"] > 0
        currency_symbol = "€" if bucket["currency"] == "EUR" else "$"
        
        avg_monthly = get_contribution_stats(bucket_id)
        projection = None
        
        if has_goal:
            progress_percent = min((bucket["current_amount"] / bucket["goal_amount"]) * 100, 100)
            remaining = bucket["goal_amount"] - bucket["current_amount"]
            projection = calculate_projection(
                bucket["current_amount"],
                bucket["goal_amount"],
                avg_monthly,
                bucket["target_date"]
            )
        else:
            progress_percent = 0
            remaining = 0

        if not bucket["is_active"]:
            status_badge = dbc.Badge("Inactive", color="secondary", className="me-2")
            card_color = None
            progress_color = "secondary"
        elif is_ongoing:
            status_badge = dbc.Badge("Ongoing", color="info", className="me-2")
            card_color = None
            progress_color = "info"
        elif has_goal and progress_percent >= 100:
            status_badge = dbc.Badge("Completed", color="success", className="me-2")
            card_color = "success"
            progress_color = "primary"
        else:
            status_badge = dbc.Badge("Active", color="primary", className="me-2")
            card_color = None
            progress_color = "success"

        projection_info = []
        if projection:
            if projection["status"] == "completed":
                projection_info = [html.P("🎉 Goal reached!", className="text-success mb-2")]
            elif projection["status"] == "on_track":
                projection_info = [
                    html.P([
                        html.I(className="bi bi-graph-up-arrow me-2 text-success"),
                        f"Projected: {projection['projected_date']}",
                    ], className="mb-1"),
                    html.Small(f"Avg: {currency_symbol}{projection['avg_monthly']:,.0f}/mo", className="text-muted"),
                ]
            elif projection["status"] == "behind":
                projection_info = [
                    html.P([
                        html.I(className="bi bi-exclamation-triangle me-2 text-warning"),
                        f"Projected: {projection['projected_date']}",
                    ], className="mb-1 text-warning"),
                    html.Small(f"{projection['months_behind']:.0f} months behind target", className="text-warning"),
                ]
            elif projection["status"] == "no_data":
                projection_info = [html.Small("Add contributions to see projections", className="text-muted")]
        elif is_ongoing and avg_monthly > 0:
            projection_info = [
                html.P([
                    html.I(className="bi bi-arrow-repeat me-2"),
                    f"Avg: {currency_symbol}{avg_monthly:,.0f}/month",
                ], className="mb-1 text-muted"),
            ]

        card_body_content = [
            html.H3(f"{currency_symbol}{bucket['current_amount']:,.2f}", className="mb-2"),
        ]
        
        if has_goal:
            card_body_content.extend([
                html.P(f"Goal: {currency_symbol}{bucket['goal_amount']:,.2f}", className="text-muted mb-3"),
                dbc.Progress(
                    value=progress_percent,
                    color=progress_color,
                    className="mb-3",
                    style={"height": "25px"},
                    label=f"{progress_percent:.1f}%",
                ),
                html.P([
                    html.Strong("Remaining: "),
                    f"{currency_symbol}{remaining:,.2f}" if remaining > 0 else "Goal reached! 🎉",
                ], className="mb-2 " + ("text-success" if remaining <= 0 else "")),
            ])
        else:
            card_body_content.append(
                html.P("No target amount", className="text-muted mb-3")
            )
        
        if bucket["target_date"] and has_goal:
            card_body_content.append(
                html.P([
                    html.I(className="bi bi-calendar me-2"),
                    f"Target: {bucket['target_date']}",
                ], className="text-muted mb-2")
            )
        
        if projection_info:
            card_body_content.append(html.Div(projection_info, className="mb-3"))
        
        card_body_content.append(
            dbc.ButtonGroup(
                [
                    dbc.Button(
                        [html.I(className="bi bi-plus-circle me-1"), "Add"],
                        id={"type": "add-transaction-btn", "bucket_id": bucket_id, "action": "credit"},
                        color="success",
                        size="sm",
                        outline=True,
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-dash-circle me-1"), "Withdraw"],
                        id={"type": "add-transaction-btn", "bucket_id": bucket_id, "action": "debit"},
                        color="warning",
                        size="sm",
                        outline=True,
                    ),
                    dbc.Button(
                        html.I(className="bi bi-graph-up"),
                        id={"type": "view-projection-btn", "bucket_id": bucket_id},
                        color="info",
                        size="sm",
                        outline=True,
                    ),
                    dbc.Button(
                        html.I(className="bi bi-list"),
                        id={"type": "view-transactions-btn", "bucket_id": bucket_id},
                        color="secondary",
                        size="sm",
                        outline=True,
                    ),
                ],
                className="w-100",
            )
        )

        card = dbc.Col(
            dbc.Card(
                [
                    dbc.CardHeader(
                        dbc.Row(
                            [
                                dbc.Col([status_badge, html.Strong(bucket["name"])], width=8),
                                dbc.Col([html.Small(bucket["currency"], className="text-muted")], width=4, className="text-end"),
                            ]
                        )
                    ),
                    dbc.CardBody(card_body_content),
                ],
                color=card_color,
                outline=True if card_color else False,
                className="h-100",
            ),
            width=6,
            lg=4,
            className="mb-4",
        )
        cards.append(card)
    
    return dbc.Row(cards)


@callback(
    [
        Output("projection-modal", "is_open"),
        Output("projection-modal-header", "children"),
        Output("projection-content", "children"),
    ],
    [
        Input({"type": "view-projection-btn", "bucket_id": dash.ALL}, "n_clicks"),
        Input("close-projection", "n_clicks"),
    ],
    [State({"type": "view-projection-btn", "bucket_id": dash.ALL}, "id")],
    prevent_initial_call=True,
)
def toggle_projection_modal(view_clicks, close_click, view_ids):
    from dash import ctx
    
    trigger = ctx.triggered_id
    if not trigger:
        raise PreventUpdate
    
    if trigger == "close-projection":
        return False, "", []
    
    if isinstance(trigger, dict) and trigger.get("type") == "view-projection-btn":
        if not any(view_clicks):
            raise PreventUpdate
        
        bucket_id = trigger["bucket_id"]
        bucket = db.fetch_one(
            "SELECT name, currency, goal_amount, start_amount FROM savings_buckets WHERE id = ?",
            (bucket_id,)
        )
        
        if not bucket:
            raise PreventUpdate
        
        name, currency, goal_amount, start_amount = bucket
        currency_symbol = "€" if currency == "EUR" else "$"
        
        current_result = db.fetch_one("""
            SELECT COALESCE(SUM(
                CASE WHEN transaction_type = 'credit' THEN amount
                     WHEN transaction_type = 'debit' THEN -amount
                     ELSE 0 END
            ), 0) FROM savings_transactions WHERE bucket_id = ?
        """, (bucket_id,))
        current_amount = (start_amount or 0) + (current_result[0] if current_result else 0)
        
        avg_monthly = get_contribution_stats(bucket_id)
        chart_data = get_projection_chart_data(bucket_id, current_amount, goal_amount, avg_monthly)
        
        fig = go.Figure()
        
        if chart_data["historical_months"]:
            fig.add_trace(go.Scatter(
                x=chart_data["historical_months"],
                y=chart_data["historical_balances"],
                mode="lines+markers",
                name="Actual",
                line=dict(color="#28a745", width=3),
                marker=dict(size=8),
            ))
        
        if chart_data["projected_months"]:
            all_proj_months = [chart_data["historical_months"][-1]] + chart_data["projected_months"] if chart_data["historical_months"] else chart_data["projected_months"]
            all_proj_balances = [current_amount] + chart_data["projected_balances"]
            
            fig.add_trace(go.Scatter(
                x=all_proj_months,
                y=all_proj_balances,
                mode="lines",
                name="Projected",
                line=dict(color="#17a2b8", width=2, dash="dash"),
            ))
        
        if goal_amount:
            all_months = chart_data["historical_months"] + chart_data["projected_months"]
            if all_months:
                fig.add_trace(go.Scatter(
                    x=[all_months[0], all_months[-1]],
                    y=[goal_amount, goal_amount],
                    mode="lines",
                    name="Goal",
                    line=dict(color="#dc3545", width=2, dash="dot"),
                ))
        
        fig.update_layout(
            height=400,
            margin=dict(t=20, b=40, l=60, r=20),
            xaxis_title="Month",
            yaxis_title=f"Balance ({currency_symbol})",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified",
        )
        
        projection = calculate_projection(current_amount, goal_amount, avg_monthly) if goal_amount else None
        
        stats_content = [
            dbc.Row([
                dbc.Col([
                    html.Small("Current Balance", className="text-muted"),
                    html.H5(f"{currency_symbol}{current_amount:,.2f}"),
                ], width=3),
                dbc.Col([
                    html.Small("Avg Monthly", className="text-muted"),
                    html.H5(f"{currency_symbol}{avg_monthly:,.2f}" if avg_monthly > 0 else "N/A"),
                ], width=3),
                dbc.Col([
                    html.Small("Goal", className="text-muted"),
                    html.H5(f"{currency_symbol}{goal_amount:,.2f}" if goal_amount else "No goal"),
                ], width=3),
                dbc.Col([
                    html.Small("Projected Completion", className="text-muted"),
                    html.H5(projection["projected_date"] if projection and projection.get("projected_date") else "N/A"),
                ], width=3),
            ], className="mb-4"),
        ]
        
        content = [
            html.Div(stats_content),
            dcc.Graph(figure=fig, config={"displayModeBar": False}),
        ]
        
        return True, f"Projection: {name}", content
    
    raise PreventUpdate


@callback(
    [
        Output("transaction-modal", "is_open"),
        Output("transaction-modal-header", "children"),
        Output("transaction-form", "children"),
    ],
    [
        Input({"type": "add-transaction-btn", "bucket_id": dash.ALL, "action": dash.ALL}, "n_clicks"),
        Input({"type": "view-transactions-btn", "bucket_id": dash.ALL}, "n_clicks"),
        Input("save-transaction", "n_clicks"),
        Input("cancel-transaction", "n_clicks"),
    ],
    [
        State({"type": "add-transaction-btn", "bucket_id": dash.ALL, "action": dash.ALL}, "id"),
        State({"type": "view-transactions-btn", "bucket_id": dash.ALL}, "id"),
        State("transaction-modal", "is_open"),
    ],
    prevent_initial_call=True,
)
def handle_transaction_modal(add_clicks, view_clicks, save_click, cancel_click, add_ids, view_ids, is_open):
    from dash import ctx

    trigger = ctx.triggered_id
    if not trigger:
        raise PreventUpdate

    if trigger == "cancel-transaction" or trigger == "save-transaction":
        return False, "", []

    if isinstance(trigger, dict) and trigger.get("type") == "add-transaction-btn":
        if not any(c for c in add_clicks if c):
            raise PreventUpdate
        
        bucket_id = trigger["bucket_id"]
        action = trigger["action"]
        bucket = db.fetch_one(
            "SELECT name, currency FROM savings_buckets WHERE id = ?", (bucket_id,)
        )
        header = f"{'Add to' if action == 'credit' else 'Withdraw from'} {bucket[0]}"
        currency_symbol = "€" if bucket[1] == "EUR" else "$"
        
        form = [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label(f"Amount ({currency_symbol}) *"),
                            dbc.Input(
                                id={"type": "trans-amount", "bucket": bucket_id},
                                type="number",
                                step=0.01,
                                placeholder="100.00",
                            ),
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            dbc.Label("Date"),
                            dbc.Input(
                                id={"type": "trans-date", "bucket": bucket_id},
                                type="date",
                                value=datetime.now().strftime("%Y-%m-%d"),
                            ),
                        ],
                        width=6,
                    ),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label("Description (optional)"),
                            dbc.Input(
                                id={"type": "trans-desc", "bucket": bucket_id},
                                placeholder="e.g., Monthly savings",
                            ),
                        ]
                    )
                ],
                className="mb-3",
            ),
            dcc.Store(id="trans-bucket-id", data=bucket_id),
            dcc.Store(id="trans-action", data=action),
        ]
        return True, header, form

    if isinstance(trigger, dict) and trigger.get("type") == "view-transactions-btn":
        if not any(c for c in view_clicks if c):
            raise PreventUpdate
        
        bucket_id = trigger["bucket_id"]
        bucket = db.fetch_one("SELECT name, currency FROM savings_buckets WHERE id = ?", (bucket_id,))
        currency_symbol = "€" if bucket[1] == "EUR" else "$"
        
        transactions = db.fetch_df(
            """SELECT date, amount, transaction_type, description 
               FROM savings_transactions 
               WHERE bucket_id=? 
               ORDER BY date DESC""",
            (bucket_id,),
        )
        
        if transactions.empty:
            table = html.P("No transactions yet.", className="text-muted")
        else:
            rows = []
            for _, tx in transactions.iterrows():
                amount_class = "text-success" if tx["transaction_type"] == "credit" else "text-danger"
                amount_prefix = "+" if tx["transaction_type"] == "credit" else "-"
                rows.append(
                    html.Tr([
                        html.Td(tx["date"]),
                        html.Td(tx["description"] or "-"),
                        html.Td(
                            f"{amount_prefix}{currency_symbol}{tx['amount']:,.2f}",
                            className=amount_class
                        ),
                    ])
                )
            
            table = dbc.Table(
                [
                    html.Thead(html.Tr([html.Th("Date"), html.Th("Description"), html.Th("Amount")])),
                    html.Tbody(rows),
                ],
                striped=True,
                hover=True,
                size="sm",
            )
        
        header = f"Transactions: {bucket[0]}"
        return True, header, table

    raise PreventUpdate


@callback(
    Output("transaction-modal", "is_open", allow_duplicate=True),
    [Input("save-transaction", "n_clicks")],
    [
        State({"type": "trans-amount", "bucket": dash.ALL}, "value"),
        State({"type": "trans-date", "bucket": dash.ALL}, "value"),
        State({"type": "trans-desc", "bucket": dash.ALL}, "value"),
        State("trans-bucket-id", "data"),
        State("trans-action", "data"),
    ],
    prevent_initial_call=True,
)
def save_transaction(n_clicks, amounts, dates, descs, bucket_id, action):
    if not n_clicks or not bucket_id or not action:
        raise PreventUpdate
    
    amount = amounts[0] if amounts and amounts[0] else None
    date = dates[0] if dates and dates[0] else datetime.now().strftime("%Y-%m-%d")
    description = descs[0] if descs and descs[0] else ""
    
    if not amount:
        raise PreventUpdate
    
    db.write_execute(
        "INSERT INTO savings_transactions (bucket_id, date, amount, transaction_type, description) VALUES (?, ?, ?, ?, ?)",
        (bucket_id, date, float(amount), action, description),
    )
    return False


if __name__ == "__main__":
    print("Savings page module loaded")
