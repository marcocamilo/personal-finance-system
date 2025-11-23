"""
Budgets Page
Manage monthly budgets, track spending, and switch templates
"""

import calendar
from datetime import datetime

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate

from database.db import db

dash.register_page(__name__, path="/budgets", title="Budgets")


def get_current_budget(year: int, month: int):
    """Get budget for current month, create from template if doesn't exist"""

    existing = db.fetch_df(
        """
        SELECT budget_type, category, subcategory, budgeted_amount, template_id
        FROM monthly_budgets
        WHERE year = ? AND month = ?
        ORDER BY 
            CASE budget_type
                WHEN 'Income' THEN 1
                WHEN 'Savings' THEN 2
                WHEN 'Needs' THEN 3
                WHEN 'Wants' THEN 4
                WHEN 'Additional' THEN 5
                WHEN 'Unexpected' THEN 6
                ELSE 7
            END,
            category, subcategory
    """,
        (year, month),
    )

    if not existing.empty:
        return existing

    template_id = db.fetch_one("SELECT id FROM budget_templates WHERE is_active = 1")[0]

    template_budgets = db.fetch_df(
        """
        SELECT budget_type, category, subcategory, budgeted_amount
        FROM template_categories
        WHERE template_id = ?
        ORDER BY 
            CASE budget_type
                WHEN 'Income' THEN 1
                WHEN 'Savings' THEN 2
                WHEN 'Needs' THEN 3
                WHEN 'Wants' THEN 4
                WHEN 'Additional' THEN 5
                WHEN 'Unexpected' THEN 6
                ELSE 7
            END,
            category, subcategory
    """,
        (template_id,),
    )

    for _, row in template_budgets.iterrows():
        db.write_execute(
            """
            INSERT INTO monthly_budgets (
                year, month, template_id, budget_type, category, 
                subcategory, budgeted_amount, is_locked
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        """,
            (
                year,
                month,
                template_id,
                row["budget_type"],
                row["category"],
                row["subcategory"],
                row["budgeted_amount"],
            ),
        )

    return get_current_budget(year, month)


def get_actual_spending(year: int, month: int):
    """Get actual spending for the month"""
    first_day = f"{year}-{month:02d}-01"
    last_day = f"{year}-{month:02d}-{calendar.monthrange(year, month)[1]}"

    actual = db.fetch_df(
        """
        SELECT 
            budget_type,
            category,
            subcategory,
            SUM(amount_eur) as actual_amount,
            COUNT(*) as transaction_count
        FROM transactions
        WHERE date BETWEEN ? AND ?
            AND is_quorum = 0
            AND budget_type IS NOT NULL
        GROUP BY budget_type, category, subcategory
    """,
        (first_day, last_day),
    )

    return actual


def layout():
    today = datetime.now()
    year = today.year
    month = today.month
    month_name = calendar.month_name[month]

    active_template = db.fetch_one(
        "SELECT name FROM budget_templates WHERE is_active = 1"
    )[0]

    templates = db.fetch_all("SELECT id, name FROM budget_templates ORDER BY name")
    template_options = [{"label": t[1], "value": t[0]} for t in templates]

    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2(f"Budget - {month_name} {year}", className="mb-0"),
                            html.P(
                                f"Active Template: {active_template}",
                                className="text-muted",
                            ),
                        ],
                        width=8,
                    ),
                    dbc.Col(
                        [
                            dbc.Button(
                                "Previous Month",
                                id="budget-prev-month",
                                outline=True,
                                color="secondary",
                                size="sm",
                                className="me-2",
                            ),
                            dbc.Button(
                                "Next Month",
                                id="budget-next-month",
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
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            dbc.Label(
                                                                "Switch Template"
                                                            ),
                                                            dcc.Dropdown(
                                                                id="template-selector",
                                                                options=template_options,
                                                                value=db.fetch_one(
                                                                    "SELECT id FROM budget_templates WHERE is_active = 1"
                                                                )[0],
                                                                clearable=False,
                                                            ),
                                                        ],
                                                        width=4,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dbc.Label("Actions"),
                                                            html.Br(),
                                                            dbc.ButtonGroup(
                                                                [
                                                                    dbc.Button(
                                                                        [
                                                                            html.I(
                                                                                className="bi bi-pencil me-2"
                                                                            ),
                                                                            "Edit Template",
                                                                        ],
                                                                        id="edit-template-btn",
                                                                        color="primary",
                                                                        outline=True,
                                                                        size="sm",
                                                                    ),
                                                                    dbc.Button(
                                                                        [
                                                                            html.I(
                                                                                className="bi bi-arrow-clockwise me-2"
                                                                            ),
                                                                            "Reset to Template",
                                                                        ],
                                                                        id="reset-budget-btn",
                                                                        color="warning",
                                                                        outline=True,
                                                                        size="sm",
                                                                    ),
                                                                    dbc.Button(
                                                                        [
                                                                            html.I(
                                                                                className="bi bi-lock me-2"
                                                                            ),
                                                                            "Lock Month",
                                                                        ],
                                                                        id="lock-month-btn",
                                                                        color="secondary",
                                                                        outline=True,
                                                                        size="sm",
                                                                    ),
                                                                ],
                                                            ),
                                                        ],
                                                        width=8,
                                                    ),
                                                ]
                                            )
                                        ]
                                    )
                                ]
                            )
                        ]
                    )
                ],
                className="mb-4",
            ),
            html.Div(id="budget-summary-cards", className="mb-4"),
            html.Div(id="budget-details"),
            dcc.Store(id="current-year", data=year),
            dcc.Store(id="current-month", data=month),
            dbc.Modal(
                [
                    dbc.ModalHeader("Edit Budget Amount"),
                    dbc.ModalBody([html.Div(id="edit-budget-form")]),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Cancel", id="cancel-budget-edit", color="secondary"
                            ),
                            dbc.Button("Save", id="save-budget-edit", color="primary"),
                        ]
                    ),
                ],
                id="edit-budget-modal",
                is_open=False,
            ),
            dbc.Modal(
                [
                    dbc.ModalHeader("Edit Budget Template"),
                    dbc.ModalBody([html.Div(id="edit-template-form")]),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Cancel", id="cancel-template-edit", color="secondary"
                            ),
                            dbc.Button(
                                "Save Template",
                                id="save-template-edit",
                                color="primary",
                            ),
                        ]
                    ),
                ],
                id="edit-template-modal",
                size="xl",
                is_open=False,
            ),
        ],
        fluid=True,
    )


@callback(
    [
        Output("budget-summary-cards", "children"),
        Output("budget-details", "children"),
    ],
    [Input("current-year", "data"), Input("current-month", "data")],
)
def update_budget_view(year, month):
    """Update budget view with summary and details"""

    budget_df = get_current_budget(year, month)
    actual_df = get_actual_spending(year, month)

    merged = budget_df.merge(
        actual_df,
        on=["budget_type", "category", "subcategory"],
        how="left",
    )
    merged["actual_amount"] = merged["actual_amount"].fillna(0)
    merged["transaction_count"] = merged["transaction_count"].fillna(0).astype(int)

    summary = create_summary_cards(merged)
    details = create_budget_details(merged, year, month)

    return summary, details


def create_summary_cards(df):
    """Create summary cards showing totals"""

    income = df[df["budget_type"] == "Income"]["budgeted_amount"].sum()
    savings_budget = df[df["budget_type"] == "Savings"]["budgeted_amount"].sum()
    savings_actual = df[df["budget_type"] == "Savings"]["actual_amount"].sum()
    needs_budget = df[df["budget_type"] == "Needs"]["budgeted_amount"].sum()
    needs_actual = df[df["budget_type"] == "Needs"]["actual_amount"].sum()
    wants_budget = df[df["budget_type"] == "Wants"]["budgeted_amount"].sum()
    wants_actual = df[df["budget_type"] == "Wants"]["actual_amount"].sum()
    total_budget = savings_budget + needs_budget + wants_budget
    total_actual = savings_actual + needs_actual + wants_actual
    remaining = income - total_actual

    return dbc.Row(
        [
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6("Income", className="text-muted mb-2"),
                                    html.H3(f"€{income:,.2f}", className="mb-0"),
                                ]
                            )
                        ],
                        className="h-100",
                    )
                ],
                width=2,
            ),
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6("Savings", className="text-muted mb-2"),
                                    html.H4(
                                        f"€{savings_actual:,.2f}", className="mb-0"
                                    ),
                                    html.Small(
                                        f"of €{savings_budget:,.2f}",
                                        className="text-muted",
                                    ),
                                    create_mini_progress_bar(
                                        savings_actual, savings_budget
                                    ),
                                ]
                            )
                        ],
                        className="h-100",
                        color="success"
                        if savings_actual <= savings_budget
                        else "danger",
                        outline=True,
                    )
                ],
                width=2,
            ),
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6("Needs", className="text-muted mb-2"),
                                    html.H4(f"€{needs_actual:,.2f}", className="mb-0"),
                                    html.Small(
                                        f"of €{needs_budget:,.2f}",
                                        className="text-muted",
                                    ),
                                    create_mini_progress_bar(
                                        needs_actual, needs_budget
                                    ),
                                ]
                            )
                        ],
                        className="h-100",
                        color="primary" if needs_actual <= needs_budget else "danger",
                        outline=True,
                    )
                ],
                width=2,
            ),
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6("Wants", className="text-muted mb-2"),
                                    html.H4(f"€{wants_actual:,.2f}", className="mb-0"),
                                    html.Small(
                                        f"of €{wants_budget:,.2f}",
                                        className="text-muted",
                                    ),
                                    create_mini_progress_bar(
                                        wants_actual, wants_budget
                                    ),
                                ]
                            )
                        ],
                        className="h-100",
                        color="info" if wants_actual <= wants_budget else "danger",
                        outline=True,
                    )
                ],
                width=2,
            ),
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6("Total Spent", className="text-muted mb-2"),
                                    html.H4(f"€{total_actual:,.2f}", className="mb-0"),
                                    html.Small(
                                        f"of €{total_budget:,.2f}",
                                        className="text-muted",
                                    ),
                                    create_mini_progress_bar(
                                        total_actual, total_budget
                                    ),
                                ]
                            )
                        ],
                        className="h-100",
                    )
                ],
                width=2,
            ),
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6("Remaining", className="text-muted mb-2"),
                                    html.H3(
                                        f"€{remaining:,.2f}",
                                        className="mb-0 text-success"
                                        if remaining >= 0
                                        else "mb-0 text-danger",
                                    ),
                                ]
                            )
                        ],
                        className="h-100",
                        color="success" if remaining >= 0 else "danger",
                        outline=True,
                    )
                ],
                width=2,
            ),
        ]
    )


def create_mini_progress_bar(actual, budget):
    """Create a small progress bar"""
    if budget == 0:
        percent = 0
    else:
        percent = min((actual / budget) * 100, 100)

    color = "success" if percent <= 100 else "danger"

    return dbc.Progress(
        value=percent, color=color, className="mt-2", style={"height": "5px"}
    )


def create_budget_details(df, year, month):
    """Create detailed budget breakdown with improved layout"""

    income_savings_types = ["Income", "Savings"]
    expense_types = ["Needs", "Wants", "Additional", "Unexpected"]

    left_sections = []
    for budget_type in income_savings_types:
        type_df = df[df["budget_type"] == budget_type]
        if type_df.empty:
            continue

        section = create_compact_budget_section(type_df, budget_type, year, month)
        left_sections.append(section)

    right_sections = []
    for budget_type in expense_types:
        type_df = df[df["budget_type"] == budget_type]
        if type_df.empty:
            continue

        section = create_detailed_budget_section(type_df, budget_type, year, month)
        right_sections.append(section)

    return dbc.Row(
        [
            dbc.Col(
                [
                    html.H5("Income & Savings", className="mb-3"),
                    html.Div(left_sections),
                ],
                width=4,
            ),
            dbc.Col(
                [
                    html.H5("Expenses", className="mb-3"),
                    html.Div(right_sections),
                ],
                width=8,
            ),
        ]
    )


def create_compact_budget_section(type_df, budget_type, year, month):
    """Create compact section for Income/Savings"""
    total_budget = type_df["budgeted_amount"].sum()
    total_actual = type_df["actual_amount"].sum()

    badge_color = "secondary" if budget_type == "Income" else "success"

    rows = []
    for _, row in type_df.iterrows():
        budgeted = row["budgeted_amount"]
        actual = row["actual_amount"]

        if row["subcategory"] and row["subcategory"] != "None":
            category_display = f"{row['category']} - {row['subcategory']}"
        else:
            category_display = row["category"]

        rows.append(
            dbc.ListGroupItem(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Div(category_display, className="fw-bold"),
                                    html.Small(
                                        f"€{actual:,.2f} / €{budgeted:,.2f}",
                                        className="text-muted",
                                    ),
                                ],
                                width=8,
                            ),
                            dbc.Col(
                                [
                                    dbc.Button(
                                        html.I(className="bi bi-pencil"),
                                        id={
                                            "type": "edit-budget-btn",
                                            "year": year,
                                            "month": month,
                                            "budget_type": budget_type,
                                            "category": row["category"],
                                            "subcategory": str(row["subcategory"]),
                                        },
                                        color="primary",
                                        size="sm",
                                        outline=True,
                                    )
                                ],
                                width=4,
                                className="text-end",
                            ),
                        ]
                    )
                ]
            )
        )

    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    dbc.Badge(budget_type, color=badge_color, className="me-2"),
                ]
            ),
            dbc.ListGroup(rows, flush=True),
        ],
        className="mb-3",
    )


def create_detailed_budget_section(type_df, budget_type, year, month):
    """Create detailed section for Expenses"""
    total_budget = type_df["budgeted_amount"].sum()
    total_actual = type_df["actual_amount"].sum()

    if budget_type == "Needs":
        badge_color = "primary"
    elif budget_type == "Wants":
        badge_color = "info"
    else:
        badge_color = "warning"

    rows = []
    for _, row in type_df.iterrows():
        budgeted = row["budgeted_amount"]
        actual = row["actual_amount"]

        if budgeted == 0:
            percent = 0
        else:
            percent = (actual / budgeted) * 100

        progress_color = "success" if percent <= 100 else "danger"

        if row["subcategory"] and row["subcategory"] != "None":
            category_display = f"{row['category']} - {row['subcategory']}"
        else:
            category_display = row["category"]

        rows.append(
            html.Tr(
                [
                    html.Td(category_display),
                    html.Td(f"€{budgeted:,.2f}", className="text-end"),
                    html.Td(
                        f"€{actual:,.2f}",
                        className="text-end "
                        + ("text-danger" if percent > 100 else ""),
                    ),
                    html.Td(
                        [
                            dbc.Progress(
                                value=min(percent, 100),
                                color=progress_color,
                                style={"height": "20px"},
                                label=f"{percent:.0f}%",
                            )
                        ],
                        style={"width": "150px"},
                    ),
                    html.Td(
                        [
                            dbc.Button(
                                html.I(className="bi bi-pencil"),
                                id={
                                    "type": "edit-budget-btn",
                                    "year": year,
                                    "month": month,
                                    "budget_type": budget_type,
                                    "category": row["category"],
                                    "subcategory": str(row["subcategory"]),
                                },
                                color="primary",
                                size="sm",
                                outline=True,
                            )
                        ],
                        className="text-center",
                    ),
                ]
            )
        )

    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Badge(
                                        budget_type, color=badge_color, className="me-2"
                                    ),
                                ],
                                width=8,
                            ),
                            dbc.Col(
                                [
                                    html.Small(
                                        f"{len(type_df)} categories",
                                        className="text-muted",
                                    ),
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
                    dbc.Table(
                        [
                            html.Thead(
                                html.Tr(
                                    [
                                        html.Th("Category"),
                                        html.Th("Budgeted", className="text-end"),
                                        html.Th("Actual", className="text-end"),
                                        html.Th("Progress"),
                                        html.Th("", className="text-center"),
                                    ]
                                )
                            ),
                            html.Tbody(rows),
                        ],
                        striped=True,
                        hover=True,
                        size="sm",
                    )
                ]
            ),
        ],
        className="mb-3",
    )


@callback(
    [
        Output("budget-summary-cards", "children", allow_duplicate=True),
        Output("budget-details", "children", allow_duplicate=True),
    ],
    [Input("template-selector", "value")],
    [State("current-year", "data"), State("current-month", "data")],
    prevent_initial_call=True,
)
def switch_template(template_id, year, month):
    """Switch active template and refresh budget view"""
    if not template_id:
        raise PreventUpdate

    db.write_execute("UPDATE budget_templates SET is_active = 0")
    db.write_execute(
        "UPDATE budget_templates SET is_active = 1 WHERE id = ?", (template_id,)
    )

    budget_df = get_current_budget(year, month)
    actual_df = get_actual_spending(year, month)
    merged = budget_df.merge(
        actual_df, on=["budget_type", "category", "subcategory"], how="left"
    )
    merged["actual_amount"] = merged["actual_amount"].fillna(0)
    merged["transaction_count"] = merged["transaction_count"].fillna(0).astype(int)

    summary = create_summary_cards(merged)
    details = create_budget_details(merged, year, month)

    return summary, details


@callback(
    [
        Output("current-year", "data", allow_duplicate=True),
        Output("current-month", "data", allow_duplicate=True),
    ],
    [
        Input("budget-prev-month", "n_clicks"),
        Input("budget-next-month", "n_clicks"),
    ],
    [State("current-year", "data"), State("current-month", "data")],
    prevent_initial_call=True,
)
def navigate_months(prev_clicks, next_clicks, year, month):
    """Navigate between months"""
    from dash import ctx

    if not ctx.triggered_id:
        raise PreventUpdate

    if ctx.triggered_id == "budget-prev-month":
        month -= 1
        if month < 1:
            month = 12
            year -= 1
    elif ctx.triggered_id == "budget-next-month":
        month += 1
        if month > 12:
            month = 1
            year += 1

    return year, month


@callback(
    [Output("edit-budget-modal", "is_open"), Output("edit-budget-form", "children")],
    [
        Input(
            {
                "type": "edit-budget-btn",
                "year": dash.ALL,
                "month": dash.ALL,
                "budget_type": dash.ALL,
                "category": dash.ALL,
                "subcategory": dash.ALL,
            },
            "n_clicks",
        )
    ],
    [
        State(
            {
                "type": "edit-budget-btn",
                "year": dash.ALL,
                "month": dash.ALL,
                "budget_type": dash.ALL,
                "category": dash.ALL,
                "subcategory": dash.ALL,
            },
            "id",
        ),
        State("edit-budget-modal", "is_open"),
    ],
    prevent_initial_call=True,
)
def open_edit_modal(n_clicks, btn_ids, is_open):
    """Open edit modal for budget item"""
    from dash import ctx

    if not any(n_clicks):
        return is_open, []

    button_id = ctx.triggered_id
    if not button_id:
        return is_open, []

    year = button_id["year"]
    month = button_id["month"]
    budget_type = button_id["budget_type"]
    category = button_id["category"]
    subcategory = button_id["subcategory"]

    result = db.fetch_one(
        """
        SELECT budgeted_amount
        FROM monthly_budgets
        WHERE year = ? AND month = ? 
            AND budget_type = ? AND category = ?
            AND (subcategory = ? OR (subcategory IS NULL AND ? = 'None'))
    """,
        (year, month, budget_type, category, subcategory, subcategory),
    )

    current_amount = result[0] if result else 0

    form = [
        dbc.Row(
            [
                dbc.Col([html.Strong("Budget Type:"), html.P(budget_type)], width=6),
                dbc.Col([html.Strong("Category:"), html.P(category)], width=6),
            ],
            className="mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Budget Amount (€)"),
                        dbc.Input(
                            id="edit-budget-amount",
                            type="number",
                            step=0.01,
                            value=current_amount,
                            placeholder="Enter amount",
                        ),
                    ]
                )
            ]
        ),
        dcc.Store(
            id="edit-budget-data",
            data={
                "year": year,
                "month": month,
                "budget_type": budget_type,
                "category": category,
                "subcategory": subcategory,
            },
        ),
    ]

    return True, form


@callback(
    Output("edit-budget-modal", "is_open", allow_duplicate=True),
    [Input("save-budget-edit", "n_clicks"), Input("cancel-budget-edit", "n_clicks")],
    [State("edit-budget-amount", "value"), State("edit-budget-data", "data")],
    prevent_initial_call=True,
)
def save_budget_edit(save_clicks, cancel_clicks, amount, data):
    """Save budget edit"""
    from dash import ctx

    if not ctx.triggered_id:
        return False

    if ctx.triggered_id == "cancel-budget-edit":
        return False

    if ctx.triggered_id == "save-budget-edit" and amount is not None:
        db.write_execute(
            """
            UPDATE monthly_budgets
            SET budgeted_amount = ?
            WHERE year = ? AND month = ? 
                AND budget_type = ? AND category = ?
                AND (subcategory = ? OR (subcategory IS NULL AND ? = 'None'))
        """,
            (
                amount,
                data["year"],
                data["month"],
                data["budget_type"],
                data["category"],
                data["subcategory"],
                data["subcategory"],
            ),
        )

    return False


@callback(
    [
        Output("edit-template-modal", "is_open"),
        Output("edit-template-form", "children"),
    ],
    [
        Input("edit-template-btn", "n_clicks"),
        Input("cancel-template-edit", "n_clicks"),
        Input("save-template-edit", "n_clicks"),
    ],
    [State("edit-template-modal", "is_open")],
    prevent_initial_call=True,
)
def toggle_template_modal(edit_click, cancel_click, save_click, is_open):
    """Toggle template editing modal"""
    from dash import ctx

    if ctx.triggered_id == "edit-template-btn":
        template_id = db.fetch_one(
            "SELECT id FROM budget_templates WHERE is_active = 1"
        )[0]
        template_name = db.fetch_one(
            "SELECT name FROM budget_templates WHERE is_active = 1"
        )[0]

        template_df = db.fetch_df(
            """
            SELECT budget_type, category, subcategory, budgeted_amount
            FROM template_categories
            WHERE template_id = ?
            ORDER BY 
                CASE budget_type
                    WHEN 'Income' THEN 1
                    WHEN 'Savings' THEN 2
                    WHEN 'Needs' THEN 3
                    WHEN 'Wants' THEN 4
                    ELSE 5
                END,
                category, subcategory
        """,
            (template_id,),
        )

        rows = []
        for idx, row in template_df.iterrows():
            category_display = (
                f"{row['category']} - {row['subcategory']}"
                if row["subcategory"]
                else row["category"]
            )
            rows.append(
                html.Tr(
                    [
                        html.Td(row["budget_type"]),
                        html.Td(category_display),
                        html.Td(
                            dbc.Input(
                                id={"type": "template-amount", "index": idx},
                                type="number",
                                step=0.01,
                                value=row["budgeted_amount"],
                                size="sm",
                            ),
                            className="text-end",
                        ),
                    ]
                )
            )

        form = [
            html.H5(f"Editing Template: {template_name}", className="mb-3"),
            html.P(
                "Changes will apply to future months using this template.",
                className="text-muted",
            ),
            dbc.Table(
                [
                    html.Thead(
                        html.Tr(
                            [
                                html.Th("Type"),
                                html.Th("Category"),
                                html.Th("Amount (€)", className="text-end"),
                            ]
                        )
                    ),
                    html.Tbody(rows),
                ],
                bordered=True,
                hover=True,
                size="sm",
                style={"maxHeight": "500px", "overflowY": "auto"},
            ),
            dcc.Store(id="template-data", data=template_df.to_dict("records")),
        ]

        return True, form

    elif ctx.triggered_id == "save-template-edit":
        return False, []

    else:
        return False, []


@callback(
    Output("budget-summary-cards", "children", allow_duplicate=True),
    [Input("reset-budget-btn", "n_clicks")],
    [State("current-year", "data"), State("current-month", "data")],
    prevent_initial_call=True,
)
def reset_to_template(n_clicks, year, month):
    """Reset current month's budget to active template"""
    if not n_clicks:
        raise PreventUpdate

    db.write_execute(
        "DELETE FROM monthly_budgets WHERE year = ? AND month = ?", (year, month)
    )

    budget_df = get_current_budget(year, month)
    actual_df = get_actual_spending(year, month)
    merged = budget_df.merge(
        actual_df, on=["budget_type", "category", "subcategory"], how="left"
    )
    merged["actual_amount"] = merged["actual_amount"].fillna(0)
    merged["transaction_count"] = merged["transaction_count"].fillna(0).astype(int)

    return create_summary_cards(merged)


@callback(
    Output("lock-month-btn", "children"),
    [Input("lock-month-btn", "n_clicks")],
    [State("current-year", "data"), State("current-month", "data")],
    prevent_initial_call=True,
)
def lock_month(n_clicks, year, month):
    """Lock month to prevent further edits"""
    if not n_clicks:
        raise PreventUpdate

    is_locked = db.fetch_one(
        """
        SELECT COALESCE(MAX(is_locked), 0)
        FROM monthly_budgets
        WHERE year = ? AND month = ?
    """,
        (year, month),
    )[0]

    if is_locked:
        db.write_execute(
            "UPDATE monthly_budgets SET is_locked = 0 WHERE year = ? AND month = ?",
            (year, month),
        )
        return [html.I(className="bi bi-lock me-2"), "Lock Month"]
    else:
        db.write_execute(
            "UPDATE monthly_budgets SET is_locked = 1 WHERE year = ? AND month = ?",
            (year, month),
        )
        return [html.I(className="bi bi-unlock me-2"), "Unlock Month"]


if __name__ == "__main__":
    print("Budgets page module loaded")
