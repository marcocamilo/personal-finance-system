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
    """Get budget for current month, create from template if doesn't exist
    Shows ALL expense categories, actual Income and Savings only"""

    existing = db.fetch_df(
        """
        SELECT budget_type, category, SUM(budgeted_amount) as budgeted_amount, 
               MAX(template_id) as template_id
        FROM monthly_budgets
        WHERE year = ? AND month = ?
        GROUP BY budget_type, category
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
            category
    """,
        (year, month),
    )

    if not existing.empty:
        expense_cats = db.fetch_df("""
            SELECT DISTINCT budget_type, category
            FROM categories
            WHERE is_active = 1
            AND budget_type IN ('Needs', 'Wants', 'Unexpected', 'Additional')
            ORDER BY budget_type, category
        """)

        template_id = db.fetch_one(
            "SELECT id FROM budget_templates WHERE is_active = 1"
        )[0]

        existing_keys = set(zip(existing["budget_type"], existing["category"]))
        missing = []

        for _, row in expense_cats.iterrows():
            key = (row["budget_type"], row["category"])
            if key not in existing_keys:
                missing.append(
                    {
                        "budget_type": row["budget_type"],
                        "category": row["category"],
                        "budgeted_amount": 0.0,
                        "template_id": template_id,
                    }
                )

        if missing:
            import pandas as pd

            missing_df = pd.DataFrame(missing)
            existing = pd.concat([existing, missing_df], ignore_index=True)
            existing = existing.sort_values(
                by=["budget_type", "category"],
                key=lambda col: col.map(
                    {
                        "Income": 1,
                        "Savings": 2,
                        "Needs": 3,
                        "Wants": 4,
                        "Additional": 5,
                        "Unexpected": 6,
                    }
                )
                if col.name == "budget_type"
                else col,
            )

        return existing

    template_id = db.fetch_one("SELECT id FROM budget_templates WHERE is_active = 1")[0]

    expense_cats = db.fetch_df("""
        SELECT DISTINCT budget_type, category
        FROM categories
        WHERE is_active = 1
        AND budget_type IN ('Needs', 'Wants', 'Unexpected', 'Additional')
        ORDER BY budget_type, category
    """)

    template_budgets = db.fetch_df(
        """
        SELECT budget_type, category, SUM(budgeted_amount) as budgeted_amount
        FROM template_categories
        WHERE template_id = ?
        GROUP BY budget_type, category
    """,
        (template_id,),
    )

    expense_merged = expense_cats.merge(
        template_budgets, on=["budget_type", "category"], how="left"
    )
    expense_merged["budgeted_amount"] = expense_merged["budgeted_amount"].fillna(0)

    income_savings = template_budgets[
        template_budgets["budget_type"].isin(["Income", "Savings"])
    ]

    import pandas as pd

    merged = pd.concat([income_savings, expense_merged], ignore_index=True)

    for _, row in merged.iterrows():
        db.write_execute(
            """
            INSERT INTO monthly_budgets (
                year, month, template_id, budget_type, category, 
                subcategory, budgeted_amount, is_locked
            ) VALUES (?, ?, ?, ?, ?, NULL, ?, 0)
        """,
            (
                year,
                month,
                template_id,
                row["budget_type"],
                row["category"],
                row["budgeted_amount"],
            ),
        )

    return get_current_budget(year, month)


def get_actual_spending(year: int, month: int):
    """Get actual spending for the month - AGGREGATED BY CATEGORY"""
    first_day = f"{year}-{month:02d}-01"
    last_day = f"{year}-{month:02d}-{calendar.monthrange(year, month)[1]}"

    actual = db.fetch_df(
        """
        SELECT 
            budget_type,
            category,
            SUM(amount_eur) as actual_amount,
            COUNT(*) as transaction_count
        FROM transactions
        WHERE date BETWEEN ? AND ?
            AND is_quorum = 0
            AND budget_type IS NOT NULL
        GROUP BY budget_type, category
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
                            html.H2(id="budget-page-title", className="mb-0"),
                            html.P(
                                id="budget-active-template",
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
            dcc.Store(id="template-edit-data"),
            html.Div(id="template-items-container", style={"display": "none"}),
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
        Output("budget-page-title", "children"),
        Output("budget-active-template", "children"),
    ],
    [Input("current-year", "data"), Input("current-month", "data")],
)
def update_budget_view(year, month):
    """Update budget view with summary and details"""

    budget_df = get_current_budget(year, month)
    actual_df = get_actual_spending(year, month)

    merged = budget_df.merge(
        actual_df,
        on=["budget_type", "category"],
        how="left",
    )
    merged["actual_amount"] = merged["actual_amount"].fillna(0)
    merged["transaction_count"] = merged["transaction_count"].fillna(0).astype(int)

    summary = create_summary_cards(merged)
    details = create_budget_details(merged, year, month)

    month_name = calendar.month_name[month]
    title = f"Budget - {month_name} {year}"

    active_template = db.fetch_one(
        "SELECT name FROM budget_templates WHERE is_active = 1"
    )[0]
    template_text = f"Active Template: {active_template}"

    return summary, details, title, template_text


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
    """Create detailed budget breakdown"""

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
    """Create compact section for Income/Savings - CATEGORY ONLY"""
    badge_color = "secondary" if budget_type == "Income" else "success"

    rows = []
    for _, row in type_df.iterrows():
        budgeted = row["budgeted_amount"]
        actual = row["actual_amount"]

        rows.append(
            dbc.ListGroupItem(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Div(row["category"], className="fw-bold"),
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
    """Create detailed section for Expenses - CATEGORY ONLY"""

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

        rows.append(
            html.Tr(
                [
                    html.Td(row["category"]),
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
        Output("budget-active-template", "children", allow_duplicate=True),
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

    db.write_execute(
        "DELETE FROM monthly_budgets WHERE year = ? AND month = ?", (year, month)
    )

    budget_df = get_current_budget(year, month)
    actual_df = get_actual_spending(year, month)
    merged = budget_df.merge(actual_df, on=["budget_type", "category"], how="left")
    merged["actual_amount"] = merged["actual_amount"].fillna(0)
    merged["transaction_count"] = merged["transaction_count"].fillna(0).astype(int)

    summary = create_summary_cards(merged)
    details = create_budget_details(merged, year, month)

    active_template = db.fetch_one(
        "SELECT name FROM budget_templates WHERE is_active = 1"
    )[0]
    template_text = f"Active Template: {active_template}"

    return summary, details, template_text


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

    result = db.fetch_one(
        """
        SELECT SUM(budgeted_amount) as budgeted_amount
        FROM monthly_budgets
        WHERE year = ? AND month = ? 
            AND budget_type = ? AND category = ?
        GROUP BY budget_type, category
    """,
        (year, month, budget_type, category),
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
            DELETE FROM monthly_budgets
            WHERE year = ? AND month = ? 
                AND budget_type = ? AND category = ?
        """,
            (
                data["year"],
                data["month"],
                data["budget_type"],
                data["category"],
            ),
        )

        template_id = db.fetch_one(
            "SELECT id FROM budget_templates WHERE is_active = 1"
        )[0]
        db.write_execute(
            """
            INSERT INTO monthly_budgets
            (year, month, template_id, budget_type, category, subcategory, budgeted_amount, is_locked)
            VALUES (?, ?, ?, ?, ?, NULL, ?, 0)
        """,
            (
                data["year"],
                data["month"],
                template_id,
                data["budget_type"],
                data["category"],
                amount,
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
    [
        State("edit-template-modal", "is_open"),
        State({"type": "template-amount", "index": dash.ALL}, "value"),
        State("template-edit-data", "data"),
    ],
    prevent_initial_call=True,
)
def toggle_template_modal(
    edit_click, cancel_click, save_click, is_open, amounts, template_data
):
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
            SELECT budget_type, category, SUM(budgeted_amount) as budgeted_amount
            FROM template_categories
            WHERE template_id = ?
            GROUP BY budget_type, category
            ORDER BY 
                CASE budget_type
                    WHEN 'Income' THEN 1
                    WHEN 'Savings' THEN 2
                    WHEN 'Needs' THEN 3
                    WHEN 'Wants' THEN 4
                    ELSE 5
                END,
                category
        """,
            (template_id,),
        )

        all_categories = db.fetch_df("""
            SELECT DISTINCT budget_type, category
            FROM categories
            WHERE is_active = 1
            ORDER BY budget_type, category
        """)

        current_items = []
        for idx, row in template_df.iterrows():
            cat_key = f"{row['budget_type']}|{row['category']}"
            current_items.append(
                {
                    "key": cat_key,
                    "budget_type": row["budget_type"],
                    "category": row["category"],
                    "amount": row["budgeted_amount"],
                }
            )

        income = template_df[template_df["budget_type"] == "Income"][
            "budgeted_amount"
        ].sum()
        total_allocated = template_df[template_df["budget_type"] != "Income"][
            "budgeted_amount"
        ].sum()
        remaining = income - total_allocated

        existing_keys = {item["key"] for item in current_items}
        available_options = [
            {
                "label": f"{row['budget_type']} → {row['category']}",
                "value": f"{row['budget_type']}|{row['category']}",
            }
            for _, row in all_categories.iterrows()
            if f"{row['budget_type']}|{row['category']}" not in existing_keys
        ]

        form = [
            html.H5(f"Editing Template: {template_name}", className="mb-3"),
            dbc.Alert(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [html.Strong("Income: "), html.Span(f"€{income:,.2f}")],
                                width=3,
                            ),
                            dbc.Col(
                                [
                                    html.Strong("Allocated: "),
                                    html.Span(f"€{total_allocated:,.2f}"),
                                ],
                                width=3,
                            ),
                            dbc.Col(
                                [
                                    html.Strong("Remaining: "),
                                    html.Span(
                                        f"€{remaining:,.2f}",
                                        className="text-success"
                                        if abs(remaining) < 0.01
                                        else "text-danger",
                                    ),
                                ],
                                width=3,
                            ),
                            dbc.Col(
                                [
                                    dbc.Badge(
                                        "✓ Zero-Based"
                                        if abs(remaining) < 0.01
                                        else "⚠ Not Balanced",
                                        color="success"
                                        if abs(remaining) < 0.01
                                        else "warning",
                                    )
                                ],
                                width=3,
                                className="text-end",
                            ),
                        ]
                    )
                ],
                color="success" if abs(remaining) < 0.01 else "warning",
                className="mb-3",
            ),
            html.Div(
                [
                    html.H6("Budget Items", className="mb-3"),
                    html.Div(
                        id="template-items-container",
                        children=[
                            create_template_item_row(item, idx)
                            for idx, item in enumerate(current_items)
                        ],
                    ),
                ],
                className="mb-4",
                style={"maxHeight": "400px", "overflowY": "auto"},
            ),
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            html.H6("Add Category", className="mb-3"),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dcc.Dropdown(
                                                id="new-template-category",
                                                options=available_options,
                                                placeholder="Select category to add...",
                                                value=None,
                                            )
                                        ],
                                        width=7,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Input(
                                                id="new-template-amount",
                                                type="number",
                                                step=0.01,
                                                placeholder="Amount (€)",
                                                size="sm",
                                                value=None,
                                            )
                                        ],
                                        width=4,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                html.I(className="bi bi-plus-circle"),
                                                id="add-template-item-btn",
                                                color="success",
                                                size="sm",
                                                className="w-100",
                                            )
                                        ],
                                        width=1,
                                    ),
                                ]
                            ),
                        ]
                    )
                ],
                className="mb-3",
            ),
            dcc.Store(
                id="template-edit-data",
                data={"template_id": template_id, "items": current_items},
            ),
        ]

        return True, form

    elif ctx.triggered_id == "save-template-edit":
        if template_data and amounts:
            template_id = template_data["template_id"]

            db.write_execute(
                "DELETE FROM template_categories WHERE template_id = ?", (template_id,)
            )

            for i, amount in enumerate(amounts):
                if amount and amount > 0 and i < len(template_data["items"]):
                    item = template_data["items"][i]
                    db.write_execute(
                        """
                        INSERT INTO template_categories 
                        (template_id, budget_type, category, subcategory, budgeted_amount)
                        VALUES (?, ?, ?, NULL, ?)
                        """,
                        (
                            template_id,
                            item["budget_type"],
                            item["category"],
                            float(amount),
                        ),
                    )

        return False, []

    else:
        return False, []


def create_template_item_row(item, idx):
    """Create an editable row for a template budget item - CATEGORY ONLY"""

    type_colors = {
        "Income": "secondary",
        "Savings": "success",
        "Needs": "primary",
        "Wants": "info",
        "Unexpected": "warning",
        "Additional": "dark",
    }

    return dbc.Card(
        [
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Badge(
                                        item["budget_type"],
                                        color=type_colors.get(
                                            item["budget_type"], "secondary"
                                        ),
                                        className="me-2",
                                    ),
                                    html.Span(item["category"], className="fw-bold"),
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    dbc.InputGroup(
                                        [
                                            dbc.InputGroupText("€"),
                                            dbc.Input(
                                                id={
                                                    "type": "template-amount",
                                                    "index": idx,
                                                },
                                                type="number",
                                                step=0.01,
                                                value=item["amount"],
                                                size="sm",
                                            ),
                                        ],
                                        size="sm",
                                    )
                                ],
                                width=5,
                            ),
                            dbc.Col(
                                [
                                    dbc.Button(
                                        html.I(className="bi bi-trash"),
                                        id={
                                            "type": "delete-template-item",
                                            "index": idx,
                                        },
                                        color="danger",
                                        size="sm",
                                        outline=True,
                                        disabled=(item["budget_type"] == "Income"),
                                    )
                                ],
                                width=1,
                                className="text-end",
                            ),
                        ],
                        align="center",
                    )
                ],
                className="py-2",
            )
        ],
        className="mb-2",
    )


@callback(
    [
        Output("template-edit-data", "data"),
        Output("new-template-category", "value"),
        Output("new-template-amount", "value"),
        Output("template-items-container", "children"),
    ],
    [Input("add-template-item-btn", "n_clicks")],
    [
        State("new-template-category", "value"),
        State("new-template-amount", "value"),
        State("template-edit-data", "data"),
    ],
    prevent_initial_call=True,
)
def add_template_item(n_clicks, category, amount, current_data):
    """Add new category to template"""
    if not n_clicks or not category or not amount or amount <= 0:
        raise PreventUpdate

    parts = category.split("|")
    if len(parts) != 2:
        raise PreventUpdate

    budget_type, cat = parts

    for item in current_data["items"]:
        if item["budget_type"] == budget_type and item["category"] == cat:
            raise PreventUpdate

    current_data["items"].append(
        {
            "key": category,
            "budget_type": budget_type,
            "category": cat,
            "amount": float(amount),
        }
    )

    items_display = [
        create_template_item_row(item, idx)
        for idx, item in enumerate(current_data["items"])
    ]

    return current_data, None, None, items_display


@callback(
    [
        Output("template-edit-data", "data", allow_duplicate=True),
        Output("template-items-container", "children", allow_duplicate=True),
    ],
    [Input({"type": "delete-template-item", "index": dash.ALL}, "n_clicks")],
    [State("template-edit-data", "data")],
    prevent_initial_call=True,
)
def delete_template_item(n_clicks, current_data):
    """Delete category from template"""
    from dash import ctx

    if not any(n_clicks):
        raise PreventUpdate

    button_id = ctx.triggered_id
    if not button_id:
        raise PreventUpdate

    idx = button_id["index"]

    if 0 <= idx < len(current_data["items"]):
        current_data["items"].pop(idx)

    items_display = [
        create_template_item_row(item, idx)
        for idx, item in enumerate(current_data["items"])
    ]

    return current_data, items_display


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
    merged = budget_df.merge(actual_df, on=["budget_type", "category"], how="left")
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
