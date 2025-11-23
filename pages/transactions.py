"""
Transactions Page (SQLite)
View, filter, and manage all transactions
"""

import calendar
from datetime import datetime

import dash
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, callback, ctx, dcc, html

from database.db import db
from import_pipeline.categorizer import Categorizer

dash.register_page(__name__, path="/transactions", title="Transactions")

categorizer = Categorizer()


def layout():
    today = datetime.now()
    current_month = today.strftime("%Y-%m")

    categories = db.fetch_all(
        "SELECT DISTINCT category FROM categories ORDER BY category"
    )
    category_options = [{"label": "All Categories", "value": "all"}] + [
        {"label": cat[0], "value": cat[0]} for cat in categories
    ]

    subcategories = db.fetch_all(
        "SELECT DISTINCT subcategory FROM categories ORDER BY subcategory"
    )
    subcat_options = [
        {"label": subcat[0], "value": subcat[0]} for subcat in subcategories
    ]

    return dbc.Container(
        [
            html.H2("Transactions", className="mb-4"),
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
                        width=3,
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
                        width=3,
                    ),
                    dbc.Col(
                        [
                            dbc.Label("Search"),
                            dbc.Input(
                                id="search-filter",
                                type="text",
                                placeholder="Search merchant name...",
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
                                options=[{"label": " Show Quorum", "value": "show"}],
                                value=[],
                                switch=True,
                            ),
                        ],
                        width=3,
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
                            dbc.Button("Save", id="save-edit", color="primary"),
                        ]
                    ),
                ],
                id="edit-modal",
                size="lg",
                is_open=False,
            ),
            dcc.Store(id="subcat-options", data=subcat_options),
        ],
        fluid=True,
    )


def generate_month_options():
    """Generate last 12 months for dropdown"""
    options = []
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
        Input("search-filter", "value"),
        Input("show-quorum", "value"),
    ],
)
def update_transactions_table(month, category, search, show_quorum):
    """Update transactions table based on filters"""

    query = """
        SELECT 
            uuid,
            date,
            description,
            amount_usd,
            amount_eur,
            category,
            subcategory,
            is_quorum,
            card_number
        FROM transactions
        WHERE 1=1
    """
    params = []

    if month:
        year, mon = month.split("-")
        first_day = f"{year}-{mon}-01"
        last_day = f"{year}-{mon}-{calendar.monthrange(int(year), int(mon))[1]}"
        query += " AND date BETWEEN ? AND ?"
        params.extend([first_day, last_day])

    if category and category != "all":
        query += " AND category = ?"
        params.append(category)

    if search:
        query += " AND LOWER(description) LIKE ?"
        params.append(f"%{search.lower()}%")

    if "show" not in show_quorum:
        query += " AND is_quorum = 0"

    query += " ORDER BY date DESC LIMIT 500"

    df = db.fetch_df(query, tuple(params) if params else None)
    df["is_quorum"] = df["is_quorum"].astype(int).astype(bool)

    stats = create_stats_row(df)

    if df.empty:
        table = html.P("No transactions found", className="text-muted text-center py-4")
    else:
        table = create_transactions_table(df)

    return table, stats


def create_stats_row(df):
    """Create statistics row"""
    if df.empty:
        return html.P("No data", className="text-muted")

    total_count = len(df)
    your_count = (~df["is_quorum"]).sum()
    quorum_count = df["is_quorum"].sum()

    your_eur = df[~df["is_quorum"]]["amount_eur"].sum()
    your_usd = df[~df["is_quorum"]]["amount_usd"].sum()
    quorum_usd = df[df["is_quorum"]]["amount_usd"].sum()

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
                width=3,
            ),
            dbc.Col(
                [
                    html.Small("Quorum Transactions", className="text-muted d-block"),
                    html.Strong(
                        f"{quorum_count} (${quorum_usd:,.2f})", className="text-success"
                    ),
                ],
                width=3,
            ),
            dbc.Col(
                [
                    html.Small("Total USD", className="text-muted d-block"),
                    html.Strong(f"${your_usd + quorum_usd:,.2f}"),
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
                html.Th("Category", style={"width": "150px"}),
                html.Th("Subcategory", style={"width": "150px"}),
                html.Th("Amount", className="text-end", style={"width": "120px"}),
                html.Th("Actions", className="text-center", style={"width": "100px"}),
            ]
        )
    )

    rows = []
    for idx, row in df.iterrows():
        badge_color = "success" if row["is_quorum"] else "primary"
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
                            html.Br() if row["card_number"] else "",
                            html.Small(
                                f"Card: ...{row['card_number']}", className="text-muted"
                            )
                            if row["card_number"]
                            else "",
                        ]
                    ),
                    html.Td(
                        dbc.Badge(row["category"], color=badge_color, className="me-1")
                    ),
                    html.Td(row["subcategory"]),
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

    suggestions = categorizer.categorize(tx_data["description"])
    suggestion_text = ""
    if suggestions["confidence"] > 0:
        suggestion_text = f"Suggested: {suggestions['subcategory']} ({suggestions['confidence']}% confidence)"

    form = [
        dbc.Row(
            [
                dbc.Col(
                    [html.Strong("Merchant:"), html.P(tx_data["description"])], width=6
                ),
                dbc.Col(
                    [
                        html.Strong("Amount:"),
                        html.P(
                            f"€{tx_data['amount_eur']:.2f}"
                            if not tx_data["is_quorum"]
                            else f"${tx_data['amount_usd']:.2f}"
                        ),
                    ],
                    width=3,
                ),
                dbc.Col([html.Strong("Date:"), html.P(tx_data["date"])], width=3),
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
                            options=subcat_options,
                            value=tx_data["subcategory"],
                            clearable=False,
                        ),
                        html.Small(suggestion_text, className="text-info")
                        if suggestion_text
                        else html.Div(),
                    ]
                )
            ]
        ),
        dcc.Store(id="edit-uuid", data=uuid),
    ]

    return True, form


@callback(
    Output("edit-modal", "is_open", allow_duplicate=True),
    [Input("save-edit", "n_clicks"), Input("cancel-edit", "n_clicks")],
    [State("edit-uuid", "data"), State("edit-subcategory", "value")],
    prevent_initial_call=True,
)
def save_transaction_edit(save_clicks, cancel_clicks, uuid, subcategory):
    """Save transaction edits"""
    if not ctx.triggered_id:
        return False

    if ctx.triggered_id == "cancel-edit":
        return False

    if ctx.triggered_id == "save-edit" and subcategory:
        category_info = db.fetch_all(
            """
            SELECT category, budget_type
            FROM categories
            WHERE subcategory = ?
        """,
            (subcategory,),
        )

        if category_info:
            category, budget_type = category_info[0]

            db.write_execute(
                """
                UPDATE transactions
                SET subcategory = ?,
                    category = ?,
                    budget_type = ?
                WHERE uuid = ?
            """,
                (subcategory, category, budget_type, uuid),
            )

            desc = db.fetch_all(
                "SELECT description FROM transactions WHERE uuid = ?", (uuid,)
            )[0][0]
            categorizer.learn_from_transaction(desc, subcategory)

    return False
