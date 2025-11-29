"""
Transactions Page (SQLite)
View, filter, and manage all transactions
"""

import calendar
import uuid as uuid_lib
from datetime import datetime

import dash
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, callback, ctx, dcc, html
from dash.exceptions import PreventUpdate

from database.db import db
from import_pipeline.categorizer import Categorizer

dash.register_page(__name__, path="/transactions", title="Transactions")

categorizer = Categorizer()


def layout():
    today = datetime.now()
    current_month = today.strftime("%Y-%m")

    categories = db.fetch_all(
        "SELECT DISTINCT category FROM categories WHERE is_active = 1 ORDER BY category"
    )
    category_options = [{"label": "All Categories", "value": "all"}] + [
        {"label": cat[0], "value": cat[0]} for cat in categories
    ]

    subcategories = db.fetch_all(
        "SELECT DISTINCT subcategory FROM categories WHERE is_active = 1 ORDER BY subcategory"
    )
    subcat_options = [{"label": "All Subcategories", "value": "all"}] + [
        {"label": subcat[0], "value": subcat[0]} for subcat in subcategories
    ]

    new_tx_subcat_options = [
        {"label": subcat[0], "value": subcat[0]} for subcat in subcategories
    ]

    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2("Transactions", className="mb-0"),
                            html.P(
                                "View, filter, and manage all transactions",
                                className="text-muted",
                            ),
                        ],
                        width=8,
                    ),
                    dbc.Col(
                        [
                            dbc.Button(
                                [
                                    html.I(className="bi bi-plus-circle me-2"),
                                    "Add Transaction",
                                ],
                                id="add-transaction-btn",
                                color="primary",
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
                            dbc.Label("Month"),
                            dcc.Dropdown(
                                id="month-filter",
                                options=generate_month_options(),
                                value=current_month,
                                clearable=False,
                            ),
                        ],
                        width=2,
                    ),
                    dbc.Col(
                        [
                            dbc.Label("Category"),
                            dcc.Dropdown(
                                id="category-filter",
                                options=category_options,
                                value="all",
                            ),
                        ],
                        width=2,
                    ),
                    dbc.Col(
                        [
                            dbc.Label("Subcategory"),
                            dcc.Dropdown(
                                id="subcategory-filter",
                                options=subcat_options,
                                value="all",
                            ),
                        ],
                        width=2,
                    ),
                    dbc.Col(
                        [
                            dbc.Label("Search"),
                            dbc.Input(
                                id="search-filter",
                                type="text",
                                placeholder="Search across all fields...",
                                debounce=True,
                            ),
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            dbc.Label("Options"),
                            dbc.Checklist(
                                id="show-quorum",
                                options=[
                                    {"label": " Show Quorum", "value": "show"},
                                    {"label": " Uncategorized Only", "value": "uncat"},
                                ],
                                value=["show"],
                                switch=True,
                            ),
                        ],
                        width=2,
                    ),
                    dbc.Col(
                        [
                            dbc.Label(" "),
                            dbc.Button(
                                [
                                    html.I(className="bi bi-arrow-clockwise me-2"),
                                    "Refresh",
                                ],
                                id="refresh-btn",
                                color="secondary",
                                outline=True,
                                className="w-100",
                            ),
                        ],
                        width=1,
                    ),
                ],
                className="mb-4",
            ),
            dbc.Row([dbc.Col([html.Div(id="transaction-stats")])], className="mb-3"),
            dbc.Row(
                [
                    dbc.Col(
                        [dbc.Card([dbc.CardBody([html.Div(id="transactions-table")])])]
                    )
                ]
            ),
            dbc.Modal(
                [
                    dbc.ModalHeader("Add Manual Transaction"),
                    dbc.ModalBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Date *"),
                                            dbc.Input(
                                                id="new-tx-date",
                                                type="date",
                                                value=today.strftime("%Y-%m-%d"),
                                            ),
                                        ],
                                        width=4,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Amount *"),
                                            dbc.Input(
                                                id="new-tx-amount",
                                                type="number",
                                                step=0.01,
                                                placeholder="0.00",
                                            ),
                                        ],
                                        width=4,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Currency"),
                                            dcc.Dropdown(
                                                id="new-tx-currency",
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
                                        width=4,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Description *"),
                                            dbc.Input(
                                                id="new-tx-description",
                                                type="text",
                                                placeholder="e.g., REWE Grocery, Coffee Shop",
                                            ),
                                        ],
                                    ),
                                ],
                                className="mb-3",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Subcategory *"),
                                            dcc.Dropdown(
                                                id="new-tx-subcategory",
                                                options=new_tx_subcat_options,
                                                placeholder="Select subcategory...",
                                            ),
                                        ],
                                    ),
                                ],
                                className="mb-3",
                            ),
                            html.Small(
                                "* Required fields. Manual transactions are marked separately from imported ones.",
                                className="text-muted",
                            ),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Cancel",
                                id="cancel-add-tx",
                                color="secondary",
                                outline=True,
                            ),
                            dbc.Button(
                                "Add Transaction", id="save-add-tx", color="primary"
                            ),
                        ]
                    ),
                ],
                id="add-tx-modal",
                size="lg",
                is_open=False,
            ),
            dbc.Modal(
                [
                    dbc.ModalHeader("Edit Transaction"),
                    dbc.ModalBody([html.Div(id="edit-transaction-form")]),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Cancel",
                                id="cancel-edit",
                                color="secondary",
                                outline=True,
                            ),
                            dbc.Button("Save Changes", id="save-edit", color="primary"),
                        ]
                    ),
                ],
                id="edit-modal",
                size="lg",
                is_open=False,
            ),
            dbc.Modal(
                [
                    dbc.ModalHeader("Confirm Delete"),
                    dbc.ModalBody(
                        [
                            html.P("Are you sure you want to delete this transaction?"),
                            html.Div(id="delete-transaction-info"),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Cancel",
                                id="cancel-delete",
                                color="secondary",
                            ),
                            dbc.Button(
                                "Delete",
                                id="confirm-delete",
                                color="danger",
                            ),
                        ]
                    ),
                ],
                id="delete-modal",
                is_open=False,
            ),
            dcc.Store(id="subcat-options", data=subcat_options),
            dcc.Store(id="new-tx-subcat-options", data=new_tx_subcat_options),
            dcc.Store(id="delete-uuid-store"),
            dcc.Store(id="refresh-trigger", data=0),
        ],
        fluid=True,
    )


def generate_month_options():
    """Generate last 12 months for dropdown"""
    options = [{"label": "All Time", "value": "all"}]
    today = datetime.now()

    for i in range(12):
        month = today.month - i
        year = today.year

        while month <= 0:
            month += 12
            year -= 1

        month_str = f"{year}-{month:02d}"
        month_name = f"{calendar.month_name[month]} {year}"
        options.append({"label": month_name, "value": month_str})

    return options


@callback(
    [Output("transactions-table", "children"), Output("transaction-stats", "children")],
    [
        Input("month-filter", "value"),
        Input("category-filter", "value"),
        Input("subcategory-filter", "value"),
        Input("search-filter", "value"),
        Input("show-quorum", "value"),
        Input("refresh-btn", "n_clicks"),
        Input("refresh-trigger", "data"),
    ],
)
def update_transactions_table(
    month, category, subcategory, search, show_quorum, n_clicks, refresh_trigger
):
    """Update transactions table based on filters"""

    try:
        db.fetch_one("SELECT is_manual FROM transactions LIMIT 1")
        has_manual_column = True
    except:
        has_manual_column = False

    if has_manual_column:
        query = """
            SELECT 
                uuid,
                date,
                description,
                amount_usd,
                amount_eur,
                category,
                subcategory,
                budget_type,
                is_quorum,
                card_number,
                is_manual
            FROM transactions
            WHERE 1=1
        """
    else:
        query = """
            SELECT 
                uuid,
                date,
                description,
                amount_usd,
                amount_eur,
                category,
                subcategory,
                budget_type,
                is_quorum,
                card_number,
                0 as is_manual
            FROM transactions
            WHERE 1=1
        """
    params = []

    if month and month != "all":
        year, mon = month.split("-")
        first_day = f"{year}-{mon}-01"
        last_day = f"{year}-{mon}-{calendar.monthrange(int(year), int(mon))[1]}"
        query += " AND date BETWEEN ? AND ?"
        params.extend([first_day, last_day])

    if category and category != "all":
        query += " AND category = ?"
        params.append(category)

    if subcategory and subcategory != "all":
        query += " AND subcategory = ?"
        params.append(subcategory)

    if search:
        query += """ AND (
            LOWER(description) LIKE ? OR
            LOWER(category) LIKE ? OR
            LOWER(subcategory) LIKE ? OR
            LOWER(budget_type) LIKE ? OR
            CAST(amount_usd AS TEXT) LIKE ? OR
            CAST(amount_eur AS TEXT) LIKE ?
        )"""
        search_term = f"%{search.lower()}%"
        params.extend([search_term] * 6)

    if "show" not in show_quorum:
        query += " AND is_quorum = 0"

    if "uncat" in show_quorum:
        query += " AND subcategory = 'Uncategorized'"

    query += " ORDER BY date DESC LIMIT 1000"

    df = db.fetch_df(query, tuple(params) if params else None)

    if not df.empty:
        df["is_quorum"] = df["is_quorum"].astype(int).astype(bool)
        df["is_manual"] = df["is_manual"].fillna(0).astype(int).astype(bool)

    stats = create_stats_row(df)

    if df.empty:
        table = html.P("No transactions found", className="text-muted text-center py-4")
    else:
        table = create_transactions_table(df)

    return table, stats


def create_stats_row(df):
    """Create statistics row"""
    if df.empty:
        return dbc.Alert(
            "No transactions match your filters", color="info", className="mb-0"
        )

    total_count = len(df)
    your_count = (~df["is_quorum"]).sum()
    quorum_count = df["is_quorum"].sum()
    manual_count = df["is_manual"].sum() if "is_manual" in df.columns else 0

    your_eur = df[~df["is_quorum"]]["amount_eur"].sum()
    your_usd = df[~df["is_quorum"]]["amount_usd"].sum()
    quorum_usd = df[df["is_quorum"]]["amount_usd"].sum()

    uncategorized = (df["subcategory"] == "Uncategorized").sum()

    return dbc.Row(
        [
            dbc.Col(
                [
                    html.Small("Total Transactions", className="text-muted d-block"),
                    html.Strong(str(total_count)),
                ],
                width=2,
            ),
            dbc.Col(
                [
                    html.Small("Your Transactions", className="text-muted d-block"),
                    html.Strong(f"{your_count} (€{your_eur:,.2f})"),
                ],
                width=2,
            ),
            dbc.Col(
                [
                    html.Small("Quorum Transactions", className="text-muted d-block"),
                    html.Strong(
                        f"{quorum_count} (${quorum_usd:,.2f})", className="text-success"
                    ),
                ],
                width=2,
            ),
            dbc.Col(
                [
                    html.Small("Manual Entries", className="text-muted d-block"),
                    html.Strong(str(manual_count), className="text-info"),
                ],
                width=2,
            ),
            dbc.Col(
                [
                    html.Small("Uncategorized", className="text-muted d-block"),
                    html.Strong(
                        str(uncategorized),
                        className="text-warning" if uncategorized > 0 else "",
                    ),
                ],
                width=2,
            ),
        ]
    )


def create_transactions_table(df):
    """Create transactions table"""

    header = html.Thead(
        html.Tr(
            [
                html.Th("Date", style={"width": "100px"}),
                html.Th("Merchant"),
                html.Th("Category", style={"width": "140px"}),
                html.Th("Subcategory", style={"width": "140px"}),
                html.Th("Amount", className="text-end", style={"width": "120px"}),
                html.Th("Actions", className="text-center", style={"width": "120px"}),
            ]
        )
    )

    rows = []
    for idx, row in df.iterrows():
        is_manual = row.get("is_manual", False)

        if is_manual:
            badge_color = "info"
            type_badge = dbc.Badge("Manual", color="info", className="ms-2", pill=True)
        elif row["is_quorum"]:
            badge_color = "success"
            type_badge = None
        else:
            badge_color = "primary"
            type_badge = None

        amount_display = (
            f"€{row['amount_eur']:.2f}"
            if not row["is_quorum"]
            else f"${row['amount_usd']:.2f}"
        )

        row_class = "table-warning" if row["subcategory"] == "Uncategorized" else ""

        rows.append(
            html.Tr(
                [
                    html.Td(row["date"]),
                    html.Td(
                        [
                            html.Strong(row["description"][:50]),
                            type_badge,
                            html.Br() if row["card_number"] else "",
                            html.Small(
                                f"Card: ...{row['card_number']}", className="text-muted"
                            )
                            if row["card_number"]
                            else "",
                        ]
                    ),
                    html.Td(
                        dbc.Badge(
                            row["category"] or "N/A",
                            color=badge_color,
                            className="me-1",
                        )
                    ),
                    html.Td(row["subcategory"] or "N/A"),
                    html.Td(html.Strong(amount_display), className="text-end"),
                    html.Td(
                        [
                            dbc.ButtonGroup(
                                [
                                    dbc.Button(
                                        html.I(className="bi bi-pencil"),
                                        id={"type": "edit-btn", "index": row["uuid"]},
                                        color="primary",
                                        size="sm",
                                        outline=True,
                                    ),
                                    dbc.Button(
                                        html.I(className="bi bi-trash"),
                                        id={"type": "delete-btn", "index": row["uuid"]},
                                        color="danger",
                                        size="sm",
                                        outline=True,
                                    ),
                                ],
                                size="sm",
                            )
                        ],
                        className="text-center",
                    ),
                ],
                className=row_class,
            )
        )

    body = html.Tbody(rows)

    return dbc.Table(
        [header, body], striped=True, hover=True, responsive=True, className="mb-0"
    )


@callback(
    Output("add-tx-modal", "is_open"),
    [Input("add-transaction-btn", "n_clicks"), Input("cancel-add-tx", "n_clicks")],
    [State("add-tx-modal", "is_open")],
    prevent_initial_call=True,
)
def toggle_add_tx_modal(add_clicks, cancel_clicks, is_open):
    """Toggle add transaction modal"""
    if ctx.triggered_id in ["add-transaction-btn", "cancel-add-tx"]:
        return not is_open
    return is_open


@callback(
    [
        Output("add-tx-modal", "is_open", allow_duplicate=True),
        Output("refresh-trigger", "data", allow_duplicate=True),
        Output("new-tx-date", "value"),
        Output("new-tx-amount", "value"),
        Output("new-tx-description", "value"),
        Output("new-tx-subcategory", "value"),
    ],
    [Input("save-add-tx", "n_clicks")],
    [
        State("new-tx-date", "value"),
        State("new-tx-amount", "value"),
        State("new-tx-currency", "value"),
        State("new-tx-description", "value"),
        State("new-tx-subcategory", "value"),
        State("refresh-trigger", "data"),
    ],
    prevent_initial_call=True,
)
def save_new_transaction(
    n_clicks, date, amount, currency, description, subcategory, current_trigger
):
    """Save a new manual transaction"""
    if not n_clicks:
        raise PreventUpdate

    if not all([date, amount, description, subcategory]):
        raise PreventUpdate

    category_info = db.fetch_one(
        "SELECT category, budget_type FROM categories WHERE subcategory = ?",
        (subcategory,),
    )

    if not category_info:
        raise PreventUpdate

    category, budget_type = category_info

    tx_uuid = str(uuid_lib.uuid4())

    amount_val = float(amount)
    if currency == "EUR":
        amount_eur = amount_val
        amount_usd = amount_val * 1.08
    else:
        amount_usd = amount_val
        amount_eur = amount_val / 1.08

    db.write_execute(
        """
        INSERT INTO transactions (
            uuid, date, description, amount_usd, amount_eur,
            category, subcategory, budget_type, is_quorum, is_manual,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            tx_uuid,
            date,
            description,
            amount_usd,
            amount_eur,
            category,
            subcategory,
            budget_type,
        ),
    )

    today = datetime.now().strftime("%Y-%m-%d")
    return False, current_trigger + 1, today, None, None, None


@callback(
    [Output("edit-modal", "is_open"), Output("edit-transaction-form", "children")],
    [Input({"type": "edit-btn", "index": ALL}, "n_clicks")],
    [
        State({"type": "edit-btn", "index": ALL}, "id"),
        State("edit-modal", "is_open"),
        State("subcat-options", "data"),
    ],
    prevent_initial_call=True,
)
def toggle_edit_modal(n_clicks, btn_ids, is_open, subcat_options):
    """Open edit modal for selected transaction"""
    if not any(n_clicks):
        return is_open, []

    button_id = ctx.triggered_id
    if not button_id:
        return is_open, []

    uuid = button_id["index"]

    tx = db.fetch_df(
        """
        SELECT uuid, date, description, amount_usd, amount_eur, 
               category, subcategory, is_quorum
        FROM transactions
        WHERE uuid = ?
    """,
        (uuid,),
    )

    if tx.empty:
        return False, []

    tx_data = tx.iloc[0]
    is_quorum = tx_data["is_quorum"]

    if is_quorum:
        currency = "USD"
        amount = tx_data["amount_usd"]
    else:
        currency = "EUR"
        amount = tx_data["amount_eur"]

    suggestions = categorizer.categorize(tx_data["description"], is_quorum)
    suggestion_text = ""
    if (
        suggestions["confidence"] > 0
        and suggestions["subcategory"] != tx_data["subcategory"]
    ):
        suggestion_text = f"💡 Suggested: {suggestions['subcategory']} ({suggestions['confidence']}% confidence)"

    edit_subcat_options = [opt for opt in subcat_options if opt["value"] != "all"]

    form = [
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Date"),
                        dbc.Input(
                            id="edit-tx-date",
                            type="date",
                            value=tx_data["date"],
                        ),
                    ],
                    width=4,
                ),
                dbc.Col(
                    [
                        dbc.Label("Amount"),
                        dbc.Input(
                            id="edit-tx-amount",
                            type="number",
                            step=0.01,
                            value=round(amount, 2),
                        ),
                    ],
                    width=4,
                ),
                dbc.Col(
                    [
                        dbc.Label("Currency"),
                        dcc.Dropdown(
                            id="edit-tx-currency",
                            options=[
                                {"label": "EUR (€)", "value": "EUR"},
                                {"label": "USD ($)", "value": "USD"},
                            ],
                            value=currency,
                            clearable=False,
                        ),
                    ],
                    width=4,
                ),
            ],
            className="mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Description"),
                        dbc.Input(
                            id="edit-tx-description",
                            type="text",
                            value=tx_data["description"],
                        ),
                    ],
                ),
            ],
            className="mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Subcategory"),
                        dcc.Dropdown(
                            id="edit-subcategory",
                            options=edit_subcat_options,
                            value=tx_data["subcategory"],
                            clearable=False,
                        ),
                        html.Small(suggestion_text, className="text-info mt-1")
                        if suggestion_text
                        else html.Div(),
                    ],
                ),
            ],
            className="mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Checklist(
                            id="apply-mapping-checkbox",
                            options=[
                                {
                                    "label": " Apply category to all transactions with same description",
                                    "value": "apply",
                                }
                            ],
                            value=[],
                            switch=True,
                        ),
                    ]
                )
            ],
            className="mb-3",
        ),
        html.Div(
            dbc.Alert(
                [
                    html.I(className="bi bi-info-circle me-2"),
                    "This is a Quorum transaction. Currency cannot be changed.",
                ],
                color="info",
                className="mb-0 py-2",
            )
            if is_quorum
            else html.Div()
        ),
        dcc.Store(id="edit-uuid", data=uuid),
        dcc.Store(id="edit-is-quorum", data=is_quorum),
    ]

    return True, form


@callback(
    [
        Output("edit-modal", "is_open", allow_duplicate=True),
        Output("refresh-trigger", "data"),
    ],
    [Input("save-edit", "n_clicks"), Input("cancel-edit", "n_clicks")],
    [
        State("edit-uuid", "data"),
        State("edit-tx-date", "value"),
        State("edit-tx-amount", "value"),
        State("edit-tx-currency", "value"),
        State("edit-tx-description", "value"),
        State("edit-subcategory", "value"),
        State("apply-mapping-checkbox", "value"),
        State("edit-is-quorum", "data"),
        State("refresh-trigger", "data"),
    ],
    prevent_initial_call=True,
)
def save_transaction_edit(
    save_clicks,
    cancel_clicks,
    uuid,
    date,
    amount,
    currency,
    description,
    subcategory,
    apply_mapping,
    is_quorum,
    current_trigger,
):
    """Save transaction edits"""
    if not ctx.triggered_id:
        raise PreventUpdate

    if ctx.triggered_id == "cancel-edit":
        return False, current_trigger

    if ctx.triggered_id == "save-edit":
        if not all([date, amount, description, subcategory]):
            raise PreventUpdate

        category_info = db.fetch_one(
            "SELECT category, budget_type FROM categories WHERE subcategory = ?",
            (subcategory,),
        )

        if not category_info:
            raise PreventUpdate

        category, budget_type = category_info

        amount_val = float(amount)
        if is_quorum:
            amount_usd = amount_val
            amount_eur = amount_val / 1.08
        elif currency == "EUR":
            amount_eur = amount_val
            amount_usd = amount_val * 1.08
        else:
            amount_usd = amount_val
            amount_eur = amount_val / 1.08

        original_desc = db.fetch_one(
            "SELECT description FROM transactions WHERE uuid = ?", (uuid,)
        )

        db.write_execute(
            """
            UPDATE transactions
            SET date = ?,
                description = ?,
                amount_usd = ?,
                amount_eur = ?,
                subcategory = ?,
                category = ?,
                budget_type = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE uuid = ?
        """,
            (
                date,
                description,
                amount_usd,
                amount_eur,
                subcategory,
                category,
                budget_type,
                uuid,
            ),
        )

        categorizer.learn_from_transaction(description, subcategory)

        if "apply" in (apply_mapping or []) and original_desc:
            db.write_execute(
                """
                UPDATE transactions
                SET subcategory = ?,
                    category = ?,
                    budget_type = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE description = ?
                    AND uuid != ?
            """,
                (subcategory, category, budget_type, original_desc[0], uuid),
            )

        return False, current_trigger + 1

    return False, current_trigger


@callback(
    [
        Output("delete-modal", "is_open"),
        Output("delete-transaction-info", "children"),
        Output("delete-uuid-store", "data"),
    ],
    [Input({"type": "delete-btn", "index": ALL}, "n_clicks")],
    [
        State({"type": "delete-btn", "index": ALL}, "id"),
        State("delete-modal", "is_open"),
    ],
    prevent_initial_call=True,
)
def toggle_delete_modal(n_clicks, btn_ids, is_open):
    """Open delete confirmation modal"""
    if not any(n_clicks):
        return is_open, [], None

    button_id = ctx.triggered_id
    if not button_id:
        return is_open, [], None

    uuid = button_id["index"]

    tx = db.fetch_df(
        """
        SELECT date, description, amount_usd, amount_eur, is_quorum
        FROM transactions
        WHERE uuid = ?
    """,
        (uuid,),
    )

    if tx.empty:
        return False, [], None

    tx_data = tx.iloc[0]

    amount_display = (
        f"€{tx_data['amount_eur']:.2f}"
        if not tx_data["is_quorum"]
        else f"${tx_data['amount_usd']:.2f}"
    )

    info = dbc.Card(
        dbc.CardBody(
            [
                html.P([html.Strong("Date: "), tx_data["date"]]),
                html.P([html.Strong("Merchant: "), tx_data["description"]]),
                html.P([html.Strong("Amount: "), amount_display]),
            ]
        ),
        color="danger",
        outline=True,
    )

    return True, info, uuid


@callback(
    [
        Output("delete-modal", "is_open", allow_duplicate=True),
        Output("refresh-trigger", "data", allow_duplicate=True),
    ],
    [Input("confirm-delete", "n_clicks"), Input("cancel-delete", "n_clicks")],
    [State("delete-uuid-store", "data"), State("refresh-trigger", "data")],
    prevent_initial_call=True,
)
def confirm_delete_transaction(confirm_clicks, cancel_clicks, uuid, current_trigger):
    """Confirm and execute transaction deletion"""
    if not ctx.triggered_id:
        raise PreventUpdate

    if ctx.triggered_id == "cancel-delete":
        return False, current_trigger

    if ctx.triggered_id == "confirm-delete" and uuid:
        db.write_execute("DELETE FROM transactions WHERE uuid = ?", (uuid,))

        return False, current_trigger + 1

    return False, current_trigger
