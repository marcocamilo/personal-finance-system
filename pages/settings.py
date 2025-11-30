"""
Settings Page
Configure application preferences, categories, templates, and data management
"""

import json
from datetime import datetime

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate

from database.db import db

dash.register_page(__name__, path="/settings", title="Settings")


def get_setting(key: str, default: str = ""):
    """Retrieve a setting from app_config"""
    result = db.fetch_one("SELECT value FROM app_config WHERE key = ?", (key,))
    return result[0] if result else default


def get_categories():
    """Get all categories from database"""
    query = """
        SELECT id, budget_type, category, subcategory, is_active
        FROM categories
        ORDER BY budget_type, category, subcategory
    """
    return db.fetch_df(query)


def get_budget_templates():
    """Get all budget templates"""
    query = """
        SELECT id, name, is_active, created_at
        FROM budget_templates
        ORDER BY name
    """
    return db.fetch_df(query)


def get_income_streams():
    """Get all income streams"""
    query = """
        SELECT id, name, amount, frequency, is_active, owner
        FROM income_streams
        ORDER BY owner, name
    """
    return db.fetch_df(query)


def get_merchant_mappings():
    """Get all merchant mappings"""
    query = """
        SELECT merchant_pattern, subcategory, confidence, last_used
        FROM merchant_mapping
        ORDER BY last_used DESC
    """
    return db.fetch_df(query)


def layout():
    """Settings page layout with tabbed sections"""

    return dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.H2([html.I(className="bi bi-gear me-2"), "Settings"], className="mb-0"),
                html.P("Configure application preferences and manage data", className="text-muted"),
            ], width=12),
        ], className="mb-4"),

        # Tabbed interface for different settings sections
        dbc.Tabs([
            dbc.Tab(label="Categories", tab_id="categories", children=[
                html.Div(id="categories-content", className="mt-4")
            ]),
            dbc.Tab(label="Budget Templates", tab_id="templates", children=[
                html.Div(id="templates-content", className="mt-4")
            ]),
            dbc.Tab(label="Income Streams", tab_id="income", children=[
                html.Div(id="income-content", className="mt-4")
            ]),
            dbc.Tab(label="Merchant Mapping", tab_id="merchants", children=[
                html.Div(id="merchants-content", className="mt-4")
            ]),
            dbc.Tab(label="Backup & Restore", tab_id="backup", children=[
                html.Div(id="backup-content", className="mt-4")
            ]),
        ], id="settings-tabs", active_tab="categories"),

        # Stores
        dcc.Store(id="refresh-trigger"),
        dcc.Store(id="edit-category-store"),
        dcc.Store(id="edit-income-store"),
        dcc.Store(id="edit-merchant-store"),
        dcc.Download(id="download-backup"),

    ], fluid=True)


def create_category_modal():
    """Modal for adding new category"""
    return dbc.Modal([
        dbc.ModalHeader("Add New Category"),
        dbc.ModalBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Budget Type"),
                    dcc.Dropdown(
                        id="new-category-budget-type",
                        options=[
                            {"label": "Personal", "value": "Personal"},
                            {"label": "Shared", "value": "Shared"},
                        ],
                        placeholder="Select budget type",
                    ),
                ], width=12, className="mb-3"),
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Category"),
                    dbc.Input(id="new-category-name", type="text", placeholder="e.g., Groceries"),
                ], width=12, className="mb-3"),
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Subcategory (optional)"),
                    dbc.Input(id="new-category-subcategory", type="text", placeholder="e.g., Whole Foods"),
                ], width=12, className="mb-3"),
            ]),
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancel", id="cancel-new-category", outline=True, className="me-2"),
            dbc.Button("Add Category", id="save-new-category", color="primary"),
        ]),
    ], id="new-category-modal", size="lg", is_open=False)


def edit_category_modal():
    """Modal for editing existing category"""
    return dbc.Modal([
        dbc.ModalHeader("Edit Category"),
        dbc.ModalBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Budget Type"),
                    dcc.Dropdown(id="edit-category-budget-type", disabled=True),
                ], width=12, className="mb-3"),
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Category"),
                    dbc.Input(id="edit-category-name", type="text", disabled=True),
                ], width=12, className="mb-3"),
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Subcategory"),
                    dbc.Input(id="edit-category-subcategory", type="text", disabled=True),
                ], width=12, className="mb-3"),
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Status"),
                    dbc.RadioItems(
                        id="edit-category-status",
                        options=[
                            {"label": "Active", "value": 1},
                            {"label": "Inactive", "value": 0},
                        ],
                        value=1,
                        inline=True,
                    ),
                ], width=12, className="mb-3"),
            ]),
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancel", id="cancel-edit-category", outline=True, className="me-2"),
            dbc.Button("Save Changes", id="save-edit-category", color="primary"),
        ]),
    ], id="edit-category-modal", size="lg", is_open=False)


def create_income_modal():
    """Modal for adding new income stream"""
    return dbc.Modal([
        dbc.ModalHeader("Add Income Stream"),
        dbc.ModalBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Name"),
                    dbc.Input(id="new-income-name", type="text", placeholder="e.g., Salary"),
                ], width=12, className="mb-3"),
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Amount (EUR)"),
                    dbc.Input(id="new-income-amount", type="number", placeholder="0.00", step=0.01),
                ], width=6, className="mb-3"),
                dbc.Col([
                    dbc.Label("Frequency"),
                    dcc.Dropdown(
                        id="new-income-frequency",
                        options=[
                            {"label": "Monthly", "value": "monthly"},
                            {"label": "Bi-weekly", "value": "bi-weekly"},
                            {"label": "Weekly", "value": "weekly"},
                            {"label": "Annual", "value": "annual"},
                        ],
                        value="monthly",
                    ),
                ], width=6, className="mb-3"),
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Owner"),
                    dbc.Input(id="new-income-owner", type="text", placeholder="e.g., Marco"),
                ], width=12, className="mb-3"),
            ]),
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancel", id="cancel-new-income", outline=True, className="me-2"),
            dbc.Button("Add Income Stream", id="save-new-income", color="primary"),
        ]),
    ], id="new-income-modal", size="lg", is_open=False)


def edit_income_modal():
    """Modal for editing income stream"""
    return dbc.Modal([
        dbc.ModalHeader("Edit Income Stream"),
        dbc.ModalBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Name"),
                    dbc.Input(id="edit-income-name", type="text"),
                ], width=12, className="mb-3"),
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Amount (EUR)"),
                    dbc.Input(id="edit-income-amount", type="number", step=0.01),
                ], width=6, className="mb-3"),
                dbc.Col([
                    dbc.Label("Frequency"),
                    dcc.Dropdown(
                        id="edit-income-frequency",
                        options=[
                            {"label": "Monthly", "value": "monthly"},
                            {"label": "Bi-weekly", "value": "bi-weekly"},
                            {"label": "Weekly", "value": "weekly"},
                            {"label": "Annual", "value": "annual"},
                        ],
                    ),
                ], width=6, className="mb-3"),
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Owner"),
                    dbc.Input(id="edit-income-owner", type="text"),
                ], width=6, className="mb-3"),
                dbc.Col([
                    dbc.Label("Status"),
                    dbc.RadioItems(
                        id="edit-income-status",
                        options=[
                            {"label": "Active", "value": 1},
                            {"label": "Inactive", "value": 0},
                        ],
                        value=1,
                        inline=True,
                    ),
                ], width=6, className="mb-3"),
            ]),
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancel", id="cancel-edit-income", outline=True, className="me-2"),
            dbc.Button("Save Changes", id="save-edit-income", color="primary"),
        ]),
    ], id="edit-income-modal", size="lg", is_open=False)


def create_merchant_mapping_modal():
    """Modal for adding merchant mapping rule"""
    return dbc.Modal([
        dbc.ModalHeader("Add Merchant Mapping Rule"),
        dbc.ModalBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Merchant Pattern"),
                    dbc.Input(id="new-merchant-pattern", type="text", placeholder="e.g., WHOLE FOODS"),
                    html.Small("Enter merchant name as it appears in transactions", className="text-muted"),
                ], width=12, className="mb-3"),
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Subcategory"),
                    dbc.Input(id="new-merchant-subcategory", type="text", placeholder="e.g., Groceries"),
                ], width=12, className="mb-3"),
            ]),
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancel", id="cancel-new-merchant", outline=True, className="me-2"),
            dbc.Button("Add Mapping", id="save-new-merchant", color="primary"),
        ]),
    ], id="new-merchant-modal", size="lg", is_open=False)


def edit_merchant_mapping_modal():
    """Modal for editing merchant mapping rule"""
    return dbc.Modal([
        dbc.ModalHeader("Edit Merchant Mapping Rule"),
        dbc.ModalBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Merchant Pattern"),
                    dbc.Input(id="edit-merchant-pattern", type="text", disabled=True),
                ], width=12, className="mb-3"),
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Subcategory"),
                    dbc.Input(id="edit-merchant-subcategory", type="text"),
                ], width=12, className="mb-3"),
            ]),
        ]),
        dbc.ModalFooter([
            dbc.Button("Delete", id="delete-merchant-mapping", color="danger", outline=True, className="me-auto"),
            dbc.Button("Cancel", id="cancel-edit-merchant", outline=True, className="me-2"),
            dbc.Button("Save Changes", id="save-edit-merchant", color="primary"),
        ]),
    ], id="edit-merchant-modal", size="lg", is_open=False)


# Callback to render content based on active tab
@callback(
    [
        Output("categories-content", "children"),
        Output("templates-content", "children"),
        Output("income-content", "children"),
        Output("merchants-content", "children"),
        Output("backup-content", "children"),
    ],
    [Input("settings-tabs", "active_tab"), Input("refresh-trigger", "data")],
)
def render_tab_content(active_tab, refresh):
    """Render content for the active tab"""

    # Only render the active tab to avoid triggering all button callbacks at once
    if active_tab == "categories":
        categories_content = render_categories_tab()
    else:
        categories_content = html.Div()

    if active_tab == "templates":
        templates_content = render_templates_tab()
    else:
        templates_content = html.Div()

    if active_tab == "income":
        income_content = render_income_tab()
    else:
        income_content = html.Div()

    if active_tab == "merchants":
        merchants_content = render_merchants_tab()
    else:
        merchants_content = html.Div()

    if active_tab == "backup":
        backup_content = render_backup_tab()
    else:
        backup_content = html.Div()

    return categories_content, templates_content, income_content, merchants_content, backup_content


def render_categories_tab():
    """Render the categories management tab"""
    categories = get_categories()

    if categories.empty:
        table_content = html.P("No categories found.", className="text-muted")
    else:
        # Create table rows
        rows = []
        for _, cat in categories.iterrows():
            status_badge = dbc.Badge(
                "Active" if cat["is_active"] else "Inactive",
                color="success" if cat["is_active"] else "secondary",
                className="me-2",
            )
            rows.append(
                html.Tr([
                    html.Td(cat["budget_type"]),
                    html.Td(cat["category"]),
                    html.Td(cat["subcategory"] if cat["subcategory"] else html.Em("(none)", className="text-muted")),
                    html.Td(status_badge),
                    html.Td([
                        dbc.Button(
                            [html.I(className="bi bi-pencil")],
                            id={"type": "edit-category-btn", "index": cat["id"]},
                            size="sm",
                            color="primary",
                            outline=True,
                        ),
                    ]),
                ])
            )

        table_content = dbc.Table([
            html.Thead(html.Tr([
                html.Th("Budget Type"),
                html.Th("Category"),
                html.Th("Subcategory"),
                html.Th("Status"),
                html.Th("Actions"),
            ])),
            html.Tbody(rows),
        ], bordered=True, hover=True, responsive=True, striped=True)

    return html.Div([
        dbc.Card([
            dbc.CardHeader([
                dbc.Row([
                    dbc.Col(html.H5("Category Management", className="mb-0"), width=8),
                    dbc.Col([
                        dbc.Button(
                            [html.I(className="bi bi-plus-circle me-2"), "Add Category"],
                            id="add-category-btn",
                            color="primary",
                            size="sm",
                            className="float-end",
                        ),
                    ], width=4),
                ]),
            ]),
            dbc.CardBody([
                html.P("Manage transaction categories and subcategories. Inactive categories won't appear in dropdowns.", className="text-muted mb-3"),
                table_content,
            ]),
        ]),
        # Modals for this tab
        create_category_modal(),
        edit_category_modal(),
    ])


def render_templates_tab():
    """Render the budget templates tab"""
    templates = get_budget_templates()

    if templates.empty:
        content = html.P("No budget templates found.", className="text-muted")
    else:
        template_cards = []
        for _, tmpl in templates.iterrows():
            status_badge = dbc.Badge(
                "Active" if tmpl["is_active"] else "Inactive",
                color="success" if tmpl["is_active"] else "secondary",
            )
            template_cards.append(
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5(tmpl["name"], className="mb-2"),
                            html.Div([
                                status_badge,
                                html.Small(
                                    f"Created: {tmpl['created_at'][:10]}",
                                    className="text-muted ms-2",
                                ),
                            ]),
                        ]),
                    ], className="mb-3"),
                ], width=4),
            )

        content = dbc.Row(template_cards)

    return dbc.Card([
        dbc.CardHeader(html.H5("Budget Templates", className="mb-0")),
        dbc.CardBody([
            html.P("View and manage budget templates. To edit template budgets, use the Budget Template Editor page.", className="text-muted mb-3"),
            content,
            html.Hr(className="my-4"),
            html.P("Note: Template editing is available on the Budget page.", className="text-muted small"),
        ]),
    ])


def render_income_tab():
    """Render the income streams tab"""
    income = get_income_streams()

    if income.empty:
        table_content = html.P("No income streams found.", className="text-muted")
    else:
        rows = []
        for _, inc in income.iterrows():
            status_badge = dbc.Badge(
                "Active" if inc["is_active"] else "Inactive",
                color="success" if inc["is_active"] else "secondary",
            )
            rows.append(
                html.Tr([
                    html.Td(inc["name"]),
                    html.Td(f"€{inc['amount']:,.2f}"),
                    html.Td(inc["frequency"].title()),
                    html.Td(inc["owner"] if inc["owner"] else html.Em("(none)", className="text-muted")),
                    html.Td(status_badge),
                    html.Td([
                        dbc.Button(
                            [html.I(className="bi bi-pencil")],
                            id={"type": "edit-income-btn", "index": inc["id"]},
                            size="sm",
                            color="primary",
                            outline=True,
                        ),
                    ]),
                ])
            )

        table_content = dbc.Table([
            html.Thead(html.Tr([
                html.Th("Name"),
                html.Th("Amount"),
                html.Th("Frequency"),
                html.Th("Owner"),
                html.Th("Status"),
                html.Th("Actions"),
            ])),
            html.Tbody(rows),
        ], bordered=True, hover=True, responsive=True, striped=True)

    return html.Div([
        dbc.Card([
            dbc.CardHeader([
                dbc.Row([
                    dbc.Col(html.H5("Income Stream Configuration", className="mb-0"), width=8),
                    dbc.Col([
                        dbc.Button(
                            [html.I(className="bi bi-plus-circle me-2"), "Add Income Stream"],
                            id="add-income-btn",
                            color="primary",
                            size="sm",
                            className="float-end",
                        ),
                    ], width=4),
                ]),
            ]),
            dbc.CardBody([
                html.P("Configure income sources for budget planning.", className="text-muted mb-3"),
                table_content,
            ]),
        ]),
        # Modals for this tab
        create_income_modal(),
        edit_income_modal(),
    ])


def render_merchants_tab():
    """Render the merchant mapping tab"""
    merchants = get_merchant_mappings()

    if merchants.empty:
        table_content = html.P("No merchant mapping rules found.", className="text-muted")
    else:
        rows = []
        for _, merch in merchants.iterrows():
            rows.append(
                html.Tr([
                    html.Td(html.Code(merch["merchant_pattern"])),
                    html.Td(merch["subcategory"]),
                    html.Td(
                        html.Small(f"Last used: {merch['last_used'][:10]}", className="text-muted")
                        if merch["last_used"] else html.Em("Never", className="text-muted")
                    ),
                    html.Td([
                        dbc.Button(
                            [html.I(className="bi bi-pencil")],
                            id={"type": "edit-merchant-btn", "index": merch["merchant_pattern"]},
                            size="sm",
                            color="primary",
                            outline=True,
                        ),
                    ]),
                ])
            )

        table_content = dbc.Table([
            html.Thead(html.Tr([
                html.Th("Merchant Pattern"),
                html.Th("Subcategory"),
                html.Th("Last Used"),
                html.Th("Actions"),
            ])),
            html.Tbody(rows),
        ], bordered=True, hover=True, responsive=True, striped=True)

    return html.Div([
        dbc.Card([
            dbc.CardHeader([
                dbc.Row([
                    dbc.Col(html.H5("Merchant Mapping Rules", className="mb-0"), width=8),
                    dbc.Col([
                        dbc.Button(
                            [html.I(className="bi bi-plus-circle me-2"), "Add Rule"],
                            id="add-merchant-btn",
                            color="primary",
                            size="sm",
                            className="float-end",
                        ),
                    ], width=4),
                ]),
            ]),
            dbc.CardBody([
                html.P("Define rules to automatically categorize transactions based on merchant names.", className="text-muted mb-3"),
                table_content,
            ]),
        ]),
        # Modals for this tab
        create_merchant_mapping_modal(),
        edit_merchant_mapping_modal(),
    ])


def render_backup_tab():
    """Render the backup and restore tab"""
    return dbc.Card([
        dbc.CardHeader(html.H5("Backup & Restore", className="mb-0")),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5([html.I(className="bi bi-download me-2"), "Export Data"], className="mb-3"),
                            html.P("Download a complete backup of your database.", className="text-muted"),
                            dbc.Button(
                                [html.I(className="bi bi-file-earmark-arrow-down me-2"), "Download Backup"],
                                id="download-backup-btn",
                                color="primary",
                                className="w-100",
                            ),
                        ]),
                    ], className="mb-3"),
                ], width=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5([html.I(className="bi bi-upload me-2"), "Restore Data"], className="mb-3"),
                            html.P("Restore your database from a backup file.", className="text-muted"),
                            dcc.Upload(
                                id="upload-backup",
                                children=dbc.Button(
                                    [html.I(className="bi bi-file-earmark-arrow-up me-2"), "Upload Backup"],
                                    color="secondary",
                                    outline=True,
                                    className="w-100",
                                ),
                            ),
                            html.Div(id="restore-status", className="mt-3"),
                        ]),
                    ]),
                ], width=6),
            ]),
            html.Hr(className="my-4"),
            dbc.Alert([
                html.I(className="bi bi-exclamation-triangle me-2"),
                "Warning: Restoring a backup will replace all current data. Make sure to download a backup first!",
            ], color="warning"),
        ]),
    ])


# Category management callbacks
@callback(
    Output("new-category-modal", "is_open"),
    [Input("add-category-btn", "n_clicks"), Input("cancel-new-category", "n_clicks"), Input("save-new-category", "n_clicks")],
    State("new-category-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_new_category_modal(add_click, cancel_click, save_click, is_open):
    """Toggle the add category modal"""
    if dash.ctx.triggered_id in ["add-category-btn", "cancel-new-category", "save-new-category"]:
        return not is_open
    return is_open


@callback(
    Output("refresh-trigger", "data", allow_duplicate=True),
    Input("save-new-category", "n_clicks"),
    [State("new-category-budget-type", "value"), State("new-category-name", "value"), State("new-category-subcategory", "value")],
    prevent_initial_call=True,
)
def save_new_category(n_clicks, budget_type, category_name, subcategory):
    """Save a new category to the database"""
    if not n_clicks or not budget_type or not category_name:
        raise PreventUpdate

    db.write_execute(
        "INSERT OR IGNORE INTO categories (budget_type, category, subcategory, is_active) VALUES (?, ?, ?, 1)",
        (budget_type, category_name, subcategory if subcategory else None)
    )

    return datetime.now().isoformat()


@callback(
    [Output("edit-category-modal", "is_open"), Output("edit-category-store", "data")],
    [Input({"type": "edit-category-btn", "index": dash.ALL}, "n_clicks"), Input("cancel-edit-category", "n_clicks"), Input("save-edit-category", "n_clicks")],
    [State("edit-category-modal", "is_open")],
    prevent_initial_call=True,
)
def toggle_edit_category_modal(edit_clicks, cancel_click, save_click, is_open):
    """Toggle the edit category modal and store category ID"""
    # Check if any edit button was actually clicked
    if not any(edit_clicks or []):
        # If no edit button clicked, check if cancel/save was clicked
        if dash.ctx.triggered_id in ["cancel-edit-category", "save-edit-category"]:
            return False, {}
        return is_open, dash.no_update

    # An edit button was clicked
    if dash.ctx.triggered_id and "edit-category-btn" in str(dash.ctx.triggered_id):
        button_id = dash.ctx.triggered_id
        category_id = button_id["index"]
        return True, {"category_id": category_id}

    # Close modal for cancel/save
    if dash.ctx.triggered_id in ["cancel-edit-category", "save-edit-category"]:
        return False, {}

    return is_open, dash.no_update


@callback(
    [
        Output("edit-category-budget-type", "value"),
        Output("edit-category-name", "value"),
        Output("edit-category-subcategory", "value"),
        Output("edit-category-status", "value"),
    ],
    Input("edit-category-store", "data"),
    prevent_initial_call=True,
)
def populate_edit_category_modal(store_data):
    """Populate the edit category modal with data"""
    if not store_data or "category_id" not in store_data:
        raise PreventUpdate

    category_id = store_data["category_id"]
    cat = db.fetch_one(
        "SELECT budget_type, category, subcategory, is_active FROM categories WHERE id = ?",
        (category_id,)
    )

    if not cat:
        raise PreventUpdate

    return cat[0], cat[1], cat[2] if cat[2] else "", cat[3]


@callback(
    Output("refresh-trigger", "data", allow_duplicate=True),
    Input("save-edit-category", "n_clicks"),
    [State("edit-category-store", "data"), State("edit-category-status", "value")],
    prevent_initial_call=True,
)
def save_edit_category(n_clicks, store_data, status):
    """Save category edits"""
    if not n_clicks or not store_data or "category_id" not in store_data:
        raise PreventUpdate

    category_id = store_data["category_id"]

    db.write_execute(
        "UPDATE categories SET is_active = ? WHERE id = ?",
        (status, category_id)
    )

    return datetime.now().isoformat()


# Income stream callbacks
@callback(
    Output("new-income-modal", "is_open"),
    [Input("add-income-btn", "n_clicks"), Input("cancel-new-income", "n_clicks"), Input("save-new-income", "n_clicks")],
    State("new-income-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_new_income_modal(add_click, cancel_click, save_click, is_open):
    """Toggle the add income modal"""
    if dash.ctx.triggered_id in ["add-income-btn", "cancel-new-income", "save-new-income"]:
        return not is_open
    return is_open


@callback(
    Output("refresh-trigger", "data", allow_duplicate=True),
    Input("save-new-income", "n_clicks"),
    [State("new-income-name", "value"), State("new-income-amount", "value"),
     State("new-income-frequency", "value"), State("new-income-owner", "value")],
    prevent_initial_call=True,
)
def save_new_income(n_clicks, name, amount, frequency, owner):
    """Save a new income stream"""
    if not n_clicks or not name or not amount:
        raise PreventUpdate

    db.write_execute(
        "INSERT INTO income_streams (name, amount, frequency, is_active, owner) VALUES (?, ?, ?, 1, ?)",
        (name, amount, frequency, owner if owner else None)
    )

    return datetime.now().isoformat()


@callback(
    [Output("edit-income-modal", "is_open"), Output("edit-income-store", "data")],
    [Input({"type": "edit-income-btn", "index": dash.ALL}, "n_clicks"), Input("cancel-edit-income", "n_clicks"), Input("save-edit-income", "n_clicks")],
    [State("edit-income-modal", "is_open")],
    prevent_initial_call=True,
)
def toggle_edit_income_modal(edit_clicks, cancel_click, save_click, is_open):
    """Toggle the edit income modal"""
    # Check if any edit button was actually clicked
    if not any(edit_clicks or []):
        # If no edit button clicked, check if cancel/save was clicked
        if dash.ctx.triggered_id in ["cancel-edit-income", "save-edit-income"]:
            return False, {}
        return is_open, dash.no_update

    # An edit button was clicked
    if dash.ctx.triggered_id and "edit-income-btn" in str(dash.ctx.triggered_id):
        button_id = dash.ctx.triggered_id
        income_id = button_id["index"]
        return True, {"income_id": income_id}

    # Close modal for cancel/save
    if dash.ctx.triggered_id in ["cancel-edit-income", "save-edit-income"]:
        return False, {}

    return is_open, dash.no_update


@callback(
    [
        Output("edit-income-name", "value"),
        Output("edit-income-amount", "value"),
        Output("edit-income-frequency", "value"),
        Output("edit-income-owner", "value"),
        Output("edit-income-status", "value"),
    ],
    Input("edit-income-store", "data"),
    prevent_initial_call=True,
)
def populate_edit_income_modal(store_data):
    """Populate the edit income modal"""
    if not store_data or "income_id" not in store_data:
        raise PreventUpdate

    income_id = store_data["income_id"]
    inc = db.fetch_one(
        "SELECT name, amount, frequency, owner, is_active FROM income_streams WHERE id = ?",
        (income_id,)
    )

    if not inc:
        raise PreventUpdate

    return inc[0], inc[1], inc[2], inc[3] if inc[3] else "", inc[4]


@callback(
    Output("refresh-trigger", "data", allow_duplicate=True),
    Input("save-edit-income", "n_clicks"),
    [State("edit-income-store", "data"), State("edit-income-name", "value"),
     State("edit-income-amount", "value"), State("edit-income-frequency", "value"),
     State("edit-income-owner", "value"), State("edit-income-status", "value")],
    prevent_initial_call=True,
)
def save_edit_income(n_clicks, store_data, name, amount, frequency, owner, status):
    """Save income stream edits"""
    if not n_clicks or not store_data or "income_id" not in store_data:
        raise PreventUpdate

    income_id = store_data["income_id"]

    db.write_execute(
        "UPDATE income_streams SET name = ?, amount = ?, frequency = ?, owner = ?, is_active = ? WHERE id = ?",
        (name, amount, frequency, owner if owner else None, status, income_id)
    )

    return datetime.now().isoformat()


# Merchant mapping callbacks
@callback(
    Output("new-merchant-modal", "is_open"),
    [Input("add-merchant-btn", "n_clicks"), Input("cancel-new-merchant", "n_clicks"), Input("save-new-merchant", "n_clicks")],
    State("new-merchant-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_new_merchant_modal(add_click, cancel_click, save_click, is_open):
    """Toggle the add merchant mapping modal"""
    if dash.ctx.triggered_id in ["add-merchant-btn", "cancel-new-merchant", "save-new-merchant"]:
        return not is_open
    return is_open


@callback(
    Output("refresh-trigger", "data", allow_duplicate=True),
    Input("save-new-merchant", "n_clicks"),
    [State("new-merchant-pattern", "value"), State("new-merchant-subcategory", "value")],
    prevent_initial_call=True,
)
def save_new_merchant_mapping(n_clicks, pattern, subcategory):
    """Save a new merchant mapping rule"""
    if not n_clicks or not pattern or not subcategory:
        raise PreventUpdate

    db.write_execute(
        "INSERT OR REPLACE INTO merchant_mapping (merchant_pattern, subcategory, confidence) VALUES (?, ?, 1)",
        (pattern.upper(), subcategory)
    )

    return datetime.now().isoformat()


@callback(
    [Output("edit-merchant-modal", "is_open"), Output("edit-merchant-store", "data")],
    [Input({"type": "edit-merchant-btn", "index": dash.ALL}, "n_clicks"),
     Input("cancel-edit-merchant", "n_clicks"), Input("save-edit-merchant", "n_clicks"),
     Input("delete-merchant-mapping", "n_clicks")],
    [State("edit-merchant-modal", "is_open")],
    prevent_initial_call=True,
)
def toggle_edit_merchant_modal(edit_clicks, cancel_click, save_click, delete_click, is_open):
    """Toggle the edit merchant mapping modal"""
    # Check if any edit button was actually clicked
    if not any(edit_clicks or []):
        # If no edit button clicked, check if cancel/save/delete was clicked
        if dash.ctx.triggered_id in ["cancel-edit-merchant", "save-edit-merchant", "delete-merchant-mapping"]:
            return False, {}
        return is_open, dash.no_update

    # An edit button was clicked
    if dash.ctx.triggered_id and "edit-merchant-btn" in str(dash.ctx.triggered_id):
        button_id = dash.ctx.triggered_id
        merchant_pattern = button_id["index"]
        return True, {"merchant_pattern": merchant_pattern}

    # Close modal for cancel/save/delete
    if dash.ctx.triggered_id in ["cancel-edit-merchant", "save-edit-merchant", "delete-merchant-mapping"]:
        return False, {}

    return is_open, dash.no_update


@callback(
    [Output("edit-merchant-pattern", "value"), Output("edit-merchant-subcategory", "value")],
    Input("edit-merchant-store", "data"),
    prevent_initial_call=True,
)
def populate_edit_merchant_modal(store_data):
    """Populate the edit merchant mapping modal"""
    if not store_data or "merchant_pattern" not in store_data:
        raise PreventUpdate

    pattern = store_data["merchant_pattern"]
    merchant = db.fetch_one(
        "SELECT merchant_pattern, subcategory FROM merchant_mapping WHERE merchant_pattern = ?",
        (pattern,)
    )

    if not merchant:
        raise PreventUpdate

    return merchant[0], merchant[1]


@callback(
    Output("refresh-trigger", "data", allow_duplicate=True),
    Input("save-edit-merchant", "n_clicks"),
    [State("edit-merchant-store", "data"), State("edit-merchant-subcategory", "value")],
    prevent_initial_call=True,
)
def save_edit_merchant_mapping(n_clicks, store_data, subcategory):
    """Save merchant mapping edits"""
    if not n_clicks or not store_data or "merchant_pattern" not in store_data:
        raise PreventUpdate

    pattern = store_data["merchant_pattern"]

    db.write_execute(
        "UPDATE merchant_mapping SET subcategory = ? WHERE merchant_pattern = ?",
        (subcategory, pattern)
    )

    return datetime.now().isoformat()


@callback(
    Output("refresh-trigger", "data", allow_duplicate=True),
    Input("delete-merchant-mapping", "n_clicks"),
    State("edit-merchant-store", "data"),
    prevent_initial_call=True,
)
def delete_merchant_mapping(n_clicks, store_data):
    """Delete a merchant mapping rule"""
    if not n_clicks or not store_data or "merchant_pattern" not in store_data:
        raise PreventUpdate

    pattern = store_data["merchant_pattern"]

    db.write_execute(
        "DELETE FROM merchant_mapping WHERE merchant_pattern = ?",
        (pattern,)
    )

    return datetime.now().isoformat()


# Backup and restore callbacks
@callback(
    Output("download-backup", "data"),
    Input("download-backup-btn", "n_clicks"),
    prevent_initial_call=True,
)
def download_backup(n_clicks):
    """Download database backup"""
    if not n_clicks:
        raise PreventUpdate

    import shutil
    from pathlib import Path

    db_path = Path("data/finance.db")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    return dcc.send_file(str(db_path), filename=f"finance_backup_{timestamp}.db")


if __name__ == "__main__":
    layout()
