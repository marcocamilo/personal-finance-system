"""
Savings Page
Manage savings goals, track progress, and view savings buckets
"""

from datetime import datetime

import dash
import dash_bootstrap_components as dbc
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
        buckets["current_amount"] = (
            buckets["start_amount"] + buckets["transactions_total"]
        )

    return buckets


def layout():
    buckets = get_savings_buckets()

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
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2("Savings Goals", className="mb-0"),
                            html.P(
                                "Track your savings progress", className="text-muted"
                            ),
                        ],
                        width=8,
                    ),
                    dbc.Col(
                        [
                            dbc.Button(
                                [
                                    html.I(className="bi bi-plus-circle me-2"),
                                    "New Goal",
                                ],
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
                                                "Active Goals",
                                                className="text-muted mb-2",
                                            ),
                                            html.H3(
                                                str(
                                                    len(
                                                        buckets[
                                                            buckets["is_active"] == 1
                                                        ]
                                                    )
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
                                                    {
                                                        "label": "EUR (€)",
                                                        "value": "EUR",
                                                    },
                                                    {
                                                        "label": "USD ($)",
                                                        "value": "USD",
                                                    },
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
                                            dbc.Input(id="new-goal-date", type="date"),
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
            dbc.Modal(
                [
                    dbc.ModalHeader(id="transaction-modal-header"),
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
    Output("new-goal-modal", "is_open"),
    [
        Input("new-goal-btn", "n_clicks"),
        Input("save-new-goal", "n_clicks"),
        Input("cancel-new-goal", "n_clicks"),
    ],
    [
        State("new-goal-name", "value"),
        State("new-goal-currency", "value"),
        State("new-goal-amount", "value"),
        State("new-goal-start", "value"),
        State("new-goal-date", "value"),
    ],
    prevent_initial_call=True,
)
def toggle_new_goal_modal(
    new_btn, save_btn, cancel_btn, name, currency, amount, start, date
):
    from dash import ctx

    trigger = ctx.triggered_id
    if not trigger:
        raise PreventUpdate

    if trigger == "new-goal-btn":
        return True

    if trigger == "save-new-goal":
        if name and currency and amount:
            db.write_execute(
                """
                INSERT INTO savings_buckets (
                    name, currency, goal_amount, start_amount, target_date, is_active
                ) VALUES (?, ?, ?, ?, ?, 1)
                """,
                (name, currency, float(amount), float(start or 0), date or None),
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
    """Update savings buckets display"""
    buckets = get_savings_buckets()

    if buckets.empty:
        return html.Div(
            [
                dbc.Alert(
                    [
                        html.H5("No Savings Goals Yet", className="alert-heading"),
                        html.P(
                            "Create your first savings goal to start tracking your progress!"
                        ),
                        html.P(
                            "Click the 'New Goal' button above to get started.",
                            className="mb-0 text-muted",
                        ),
                    ],
                    color="info",
                )
            ]
        )

    cards = []
    for _, bucket in buckets.iterrows():
        progress_percent = (
            min((bucket["current_amount"] / bucket["goal_amount"]) * 100, 100)
            if bucket["goal_amount"] > 0
            else 0
        )
        remaining = bucket["goal_amount"] - bucket["current_amount"]
        currency_symbol = "€" if bucket["currency"] == "EUR" else "$"

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

        if bucket["is_active"] == 0:
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
                                html.H3(
                                    f"{currency_symbol}{bucket['current_amount']:,.2f}",
                                    className="mb-2",
                                ),
                                html.P(
                                    f"Goal: {currency_symbol}{bucket['goal_amount']:,.2f}",
                                    className="text-muted mb-3",
                                ),
                                dbc.Progress(
                                    value=progress_percent,
                                    color=progress_color,
                                    className="mb-3",
                                    style={"height": "25px"},
                                    label=f"{progress_percent:.1f}%",
                                ),
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
                                dbc.ButtonGroup(
                                    [
                                        dbc.Button(
                                            [
                                                html.I(
                                                    className="bi bi-plus-circle me-1"
                                                ),
                                                "Add",
                                            ],
                                            id={
                                                "type": "add-transaction-btn",
                                                "bucket_id": int(bucket["id"]),
                                                "action": "credit",
                                            },
                                            color="success",
                                            size="sm",
                                            outline=True,
                                        ),
                                        dbc.Button(
                                            [
                                                html.I(
                                                    className="bi bi-dash-circle me-1"
                                                ),
                                                "Withdraw",
                                            ],
                                            id={
                                                "type": "add-transaction-btn",
                                                "bucket_id": int(bucket["id"]),
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
                                                "bucket_id": int(bucket["id"]),
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
    [
        Output("transaction-modal", "is_open"),
        Output("transaction-modal-header", "children"),
        Output("transaction-form", "children"),
    ],
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
    ],
    prevent_initial_call=True,
)
def handle_transaction_modal(add_clicks, save_click, cancel_click, btn_ids, is_open):
    from dash import ctx

    trigger = ctx.triggered_id

# Ignore initial None or 0 clicks
    if trigger is None:
        raise PreventUpdate

    if trigger == "cancel-transaction" or trigger == "save-transaction":
        return False, "", []

# Only respond if the trigger is an actual add/withdraw button
    if isinstance(trigger, dict) and trigger.get("type") == "add-transaction-btn":
        bucket_id = trigger["bucket_id"]
        action = trigger["action"]

        # Only proceed if the button was actually clicked (n_clicks > 0)
        # ctx.triggered[0]['value'] corresponds to the button n_clicks
        value = ctx.triggered[0]["value"]
        if not value or value <= 0:
            raise PreventUpdate

        bucket = db.fetch_one(
            "SELECT name, currency FROM savings_buckets WHERE id = ?", (bucket_id,)
        )

        action_text = "Add to" if action == "credit" else "Withdraw from"
        header = f"{action_text} {bucket[0]}"

        form = [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label("Amount *"),
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
    """Save transaction to database"""
    if not n_clicks or not bucket_id or not action:
        raise PreventUpdate

    amount = amounts[0] if amounts and amounts[0] else None
    date = dates[0] if dates and dates[0] else datetime.now().strftime("%Y-%m-%d")
    description = descs[0] if descs and descs[0] else ""

    if not amount:
        raise PreventUpdate

    db.write_execute(
        """
        INSERT INTO savings_transactions (
            bucket_id, date, amount, transaction_type, description
        ) VALUES (?, ?, ?, ?, ?)
    """,
        (
            bucket_id,
            date,
            float(amount),
            action,
            description,
        ),
    )

    return False


if __name__ == "__main__":
    print("Savings page module loaded")
