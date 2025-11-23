"""
Savings Page
Manage savings goals, track progress, and view savings buckets
"""

from datetime import datetime

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate

from database.db import db

dash.register_page(__name__, path="/savings", title="Savings")


def get_savings_buckets():
    """Get all savings buckets with current balances"""
    buckets = db.fetch_df("""
        SELECT 
            sb.id,
            sb.name,
            sb.currency,
            sb.goal_amount,
            sb.start_amount,
            sb.target_date,
            sb.is_active,
            COALESCE(SUM(
                CASE 
                    WHEN st.transaction_type = 'credit' THEN st.amount
                    WHEN st.transaction_type = 'debit' THEN -st.amount
                    ELSE 0
                END
            ), 0) as transactions_total
        FROM savings_buckets sb
        LEFT JOIN savings_transactions st ON sb.id = st.bucket_id
        GROUP BY sb.id, sb.name, sb.currency, sb.goal_amount, sb.start_amount, sb.target_date, sb.is_active
        ORDER BY sb.is_active DESC, sb.created_at DESC
    """)
    
    if not buckets.empty:
        buckets["current_amount"] = buckets["start_amount"] + buckets["transactions_total"]
    
    return buckets


def layout():
    buckets = get_savings_buckets()
    
    # Calculate totals
    if not buckets.empty:
        total_saved_eur = buckets[buckets["currency"] == "EUR"]["current_amount"].sum()
        total_saved_usd = buckets[buckets["currency"] == "USD"]["current_amount"].sum()
        total_goal_eur = buckets[buckets["currency"] == "EUR"]["goal_amount"].sum()
        total_goal_usd = buckets[buckets["currency"] == "USD"]["goal_amount"].sum()
    else:
        total_saved_eur = total_saved_usd = 0
        total_goal_eur = total_goal_usd = 0
    
    return dbc.Container(
        [
            # Header
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
                        [
                            dbc.Button(
                                [html.I(className="bi bi-plus-circle me-2"), "New Goal"],
                                id="new-goal-btn",
                                color="primary",
                            )
                        ],
                        width=4,
                        className="text-end",
                    ),
                ],
                className="mb-4",
            ),
            
            # Summary cards
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H6(
                                                "Total Saved (EUR)",
                                                className="text-muted mb-2",
                                            ),
                                            html.H3(
                                                f"€{total_saved_eur:,.2f}",
                                                className="mb-0 text-success",
                                            ),
                                            html.Small(
                                                f"Goal: €{total_goal_eur:,.2f}",
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
                                                "Total Saved (USD)",
                                                className="text-muted mb-2",
                                            ),
                                            html.H3(
                                                f"${total_saved_usd:,.2f}",
                                                className="mb-0 text-success",
                                            ),
                                            html.Small(
                                                f"Goal: ${total_goal_usd:,.2f}",
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
                                                "Active Goals", className="text-muted mb-2"
                                            ),
                                            html.H3(
                                                str(
                                                    len(buckets[buckets["is_active"]])
                                                    if not buckets.empty
                                                    else 0
                                                ),
                                                className="mb-0",
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
                                                "Goals Completed",
                                                className="text-muted mb-2",
                                            ),
                                            html.H3(
                                                str(
                                                    len(
                                                        buckets[
                                                            buckets["current_amount"]
                                                            >= buckets["goal_amount"]
                                                        ]
                                                    )
                                                    if not buckets.empty
                                                    else 0
                                                ),
                                                className="mb-0 text-success",
                                            ),
                                        ]
                                    )
                                ],
                                className="h-100",
                            )
                        ],
                        width=3,
                    ),
                ],
                className="mb-4",
            ),
            
            # Savings buckets
            html.Div(id="savings-buckets-container"),
            
            # New goal modal
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
                                            dbc.Input(
                                                id="new-goal-name",
                                                placeholder="e.g., Emergency Fund",
                                            ),
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
                                            dbc.Label("Goal Amount *"),
                                            dbc.Input(
                                                id="new-goal-amount",
                                                type="number",
                                                step=0.01,
                                                placeholder="10000.00",
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
                                            dbc.Label("Target Date (optional)"),
                                            dbc.Input(
                                                id="new-goal-date", type="date"
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
                            dbc.Button(
                                "Cancel", id="cancel-new-goal", color="secondary"
                            ),
                            dbc.Button("Create", id="save-new-goal", color="primary"),
                        ]
                    ),
                ],
                id="new-goal-modal",
                is_open=False,
            ),
            
            # Transaction modal
            dbc.Modal(
                [
                    dbc.ModalHeader("Add Transaction"),
                    dbc.ModalBody([html.Div(id="transaction-form")]),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Cancel", id="cancel-transaction", color="secondary"
                            ),
                            dbc.Button("Save", id="save-transaction", color="primary"),
                        ]
                    ),
                ],
                id="transaction-modal",
                is_open=False,
            ),
        ],
        fluid=True,
    )


@callback(
    Output("savings-buckets-container", "children"),
    [Input("new-goal-modal", "is_open"), Input("transaction-modal", "is_open")],
)
def update_savings_buckets(new_goal_open, transaction_open):
    """Update savings buckets display"""
    buckets = get_savings_buckets()
    
    if buckets.empty:
        return dbc.Alert(
            [
                html.H5("No Savings Goals Yet", className="alert-heading"),
                html.P(
                    "Create your first savings goal to start tracking your progress!"
                ),
                dbc.Button(
                    [html.I(className="bi bi-plus-circle me-2"), "Create Goal"],
                    id="new-goal-btn-empty",
                    color="primary",
                ),
            ],
            color="info",
        )
    
    cards = []
    for _, bucket in buckets.iterrows():
        progress_percent = (
            min((bucket["current_amount"] / bucket["goal_amount"]) * 100, 100)
            if bucket["goal_amount"] > 0
            else 0
        )
        
        remaining = bucket["goal_amount"] - bucket["current_amount"]
        
        # Currency symbol
        currency_symbol = "€" if bucket["currency"] == "EUR" else "$"
        
        # Progress color
        if progress_percent >= 100:
            progress_color = "success"
            card_color = "success"
        elif progress_percent >= 75:
            progress_color = "info"
            card_color = None
        elif progress_percent >= 50:
            progress_color = "warning"
            card_color = None
        else:
            progress_color = "primary"
            card_color = None
        
        # Status badge
        if not bucket["is_active"]:
            status_badge = dbc.Badge("Inactive", color="secondary", className="me-2")
        elif progress_percent >= 100:
            status_badge = dbc.Badge("Completed", color="success", className="me-2")
        else:
            status_badge = dbc.Badge("Active", color="primary", className="me-2")
        
        card = dbc.Col(
            [
                dbc.Card(
                    [
                        dbc.CardHeader(
                            [
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            [status_badge, html.Strong(bucket["name"])],
                                            width=8,
                                        ),
                                        dbc.Col(
                                            [
                                                html.Small(
                                                    bucket["currency"],
                                                    className="text-muted",
                                                )
                                            ],
                                            width=4,
                                            className="text-end",
                                        ),
                                    ]
                                )
                            ]
                        ),
                        dbc.CardBody(
                            [
                                # Current amount
                                html.H3(
                                    f"{currency_symbol}{bucket['current_amount']:,.2f}",
                                    className="mb-2",
                                ),
                                html.P(
                                    f"Goal: {currency_symbol}{bucket['goal_amount']:,.2f}",
                                    className="text-muted mb-3",
                                ),
                                
                                # Progress bar
                                dbc.Progress(
                                    value=progress_percent,
                                    color=progress_color,
                                    className="mb-3",
                                    style={"height": "25px"},
                                    label=f"{progress_percent:.1f}%",
                                ),
                                
                                # Remaining
                                html.P(
                                    [
                                        html.Strong("Remaining: "),
                                        f"{currency_symbol}{remaining:,.2f}"
                                        if remaining > 0
                                        else "Goal reached! 🎉",
                                    ],
                                    className="mb-3 "
                                    + ("text-success" if remaining <= 0 else ""),
                                ),
                                
                                # Target date
                                (
                                    html.P(
                                        [
                                            html.I(className="bi bi-calendar me-2"),
                                            f"Target: {bucket['target_date']}",
                                        ],
                                        className="text-muted mb-3",
                                    )
                                    if bucket["target_date"]
                                    else html.Div()
                                ),
                                
                                # Actions
                                dbc.ButtonGroup(
                                    [
                                        dbc.Button(
                                            [
                                                html.I(className="bi bi-plus-circle me-1"),
                                                "Add",
                                            ],
                                            id={
                                                "type": "add-transaction-btn",
                                                "bucket_id": bucket["id"],
                                                "action": "credit",
                                            },
                                            color="success",
                                            size="sm",
                                            outline=True,
                                        ),
                                        dbc.Button(
                                            [
                                                html.I(className="bi bi-dash-circle me-1"),
                                                "Withdraw",
                                            ],
                                            id={
                                                "type": "add-transaction-btn",
                                                "bucket_id": bucket["id"],
                                                "action": "debit",
                                            },
                                            color="warning",
                                            size="sm",
                                            outline=True,
                                        ),
                                        dbc.Button(
                                            html.I(className="bi bi-list"),
                                            id={
                                                "type": "view-transactions-btn",
                                                "bucket_id": bucket["id"],
                                            },
                                            color="info",
                                            size="sm",
                                            outline=True,
                                        ),
                                    ],
                                    className="w-100",
                                ),
                            ]
                        ),
                    ],
                    color=card_color,
                    outline=True if card_color else False,
                    className="h-100",
                )
            ],
            width=6,
            lg=4,
            className="mb-4",
        )
        
        cards.append(card)
    
    return dbc.Row(cards)


@callback(
    Output("new-goal-modal", "is_open"),
    [
        Input("new-goal-btn", "n_clicks"),
        Input("new-goal-btn-empty", "n_clicks"),
        Input("save-new-goal", "n_clicks"),
        Input("cancel-new-goal", "n_clicks"),
    ],
    [
        State("new-goal-name", "value"),
        State("new-goal-currency", "value"),
        State("new-goal-amount", "value"),
        State("new-goal-start", "value"),
        State("new-goal-date", "value"),
        State("new-goal-modal", "is_open"),
    ],
    prevent_initial_call=True,
)
def toggle_new_goal_modal(
    new_btn, empty_btn, save_btn, cancel_btn, name, currency, amount, start, date, is_open
):
    """Toggle new goal modal"""
    from dash import ctx
    
    if not ctx.triggered_id:
        raise PreventUpdate
    
    if ctx.triggered_id == "save-new-goal":
        if name and currency and amount:
            # Create new savings bucket
            db.write_execute(
                """
                INSERT INTO savings_buckets (
                    name, currency, goal_amount, start_amount, target_date, is_active
                ) VALUES (?, ?, ?, ?, ?, 1)
            """,
                (name, currency, float(amount), float(start or 0), date or None),
            )
        return False
    
    if ctx.triggered_id == "cancel-new-goal":
        return False
    
    return not is_open


@callback(
    [Output("transaction-modal", "is_open"), Output("transaction-form", "children")],
    [
        Input(
            {"type": "add-transaction-btn", "bucket_id": dash.ALL, "action": dash.ALL},
            "n_clicks",
        ),
        Input("save-transaction", "n_clicks"),
        Input("cancel-transaction", "n_clicks"),
    ],
    [
        State(
            {"type": "add-transaction-btn", "bucket_id": dash.ALL, "action": dash.ALL},
            "id",
        ),
        State("transaction-modal", "is_open"),
        State("transaction-amount-input", "value"),
        State("transaction-desc-input", "value"),
        State("transaction-date-input", "value"),
        State("transaction-bucket-id", "data"),
        State("transaction-type", "data"),
    ],
    prevent_initial_call=True,
)
def handle_transaction_modal(
    add_clicks,
    save_click,
    cancel_click,
    btn_ids,
    is_open,
    amount,
    description,
    date,
    bucket_id,
    transaction_type,
):
    """Handle transaction modal"""
    from dash import ctx
    
    if not ctx.triggered_id:
        raise PreventUpdate
    
    # Cancel
    if ctx.triggered_id == "cancel-transaction":
        return False, []
    
    # Save
    if ctx.triggered_id == "save-transaction":
        if amount and bucket_id and transaction_type:
            db.write_execute(
                """
                INSERT INTO savings_transactions (
                    bucket_id, date, amount, transaction_type, description
                ) VALUES (?, ?, ?, ?, ?)
            """,
                (
                    bucket_id,
                    date or datetime.now().strftime("%Y-%m-%d"),
                    float(amount),
                    transaction_type,
                    description or "",
                ),
            )
        return False, []
    
    # Open for add/withdraw
    if ctx.triggered_id and ctx.triggered_id.get("type") == "add-transaction-btn":
        bucket_id = ctx.triggered_id["bucket_id"]
        action = ctx.triggered_id["action"]
        
        # Get bucket info
        bucket = db.fetch_one(
            "SELECT name, currency FROM savings_buckets WHERE id = ?", (bucket_id,)
        )
        
        form = [
            html.P(
                [html.Strong("Bucket: "), bucket[0]], className="mb-3"
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label("Amount *"),
                            dbc.Input(
                                id="transaction-amount-input",
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
                                id="transaction-date-input",
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
                                id="transaction-desc-input",
                                placeholder="e.g., Monthly savings",
                            ),
                        ]
                    )
                ]
            ),
            dcc.Store(id="transaction-bucket-id", data=bucket_id),
            dcc.Store(id="transaction-type", data=action),
        ]
        
        return True, form
    
    return is_open, []


if __name__ == "__main__":
    print("Savings page module loaded")
