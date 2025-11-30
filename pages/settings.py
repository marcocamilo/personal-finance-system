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
        dcc.Store(id="settings-template-edit-data"),
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


def create_template_editor_modal():
    """Modal for editing budget templates"""
    return dbc.Modal([
        dbc.ModalHeader("Edit Budget Template"),
        dbc.ModalBody([html.Div(id="settings-template-editor-form")]),
        dbc.ModalFooter([
            dbc.Button("Cancel", id="settings-cancel-template-edit", color="secondary", className="me-2"),
            dbc.Button("Save Changes", id="settings-save-template-edit", color="primary"),
        ]),
    ], id="settings-template-editor-modal", size="xl", is_open=False)


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
            # Get template items count and total budget
            template_stats = db.fetch_one(
                """
                SELECT
                    COUNT(*) as item_count,
                    SUM(CASE WHEN budget_type != 'Income' THEN budgeted_amount ELSE 0 END) as total_budget
                FROM template_categories
                WHERE template_id = ?
                """,
                (tmpl["id"],)
            )

            item_count = template_stats[0] if template_stats else 0
            total_budget = template_stats[1] if template_stats and template_stats[1] else 0

            status_badge = dbc.Badge(
                "Active" if tmpl["is_active"] else "Inactive",
                color="success" if tmpl["is_active"] else "secondary",
            )

            template_cards.append(
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.H5(tmpl["name"], className="mb-2"),
                                    html.Div([
                                        status_badge,
                                        html.Small(
                                            f" • {item_count} categories • €{total_budget:,.2f} total",
                                            className="text-muted ms-2",
                                        ),
                                    ]),
                                    html.Small(
                                        f"Created: {tmpl['created_at'][:10]}",
                                        className="text-muted d-block mt-1",
                                    ),
                                ], width=10),
                                dbc.Col([
                                    dbc.Button(
                                        html.I(className="bi bi-pencil"),
                                        id={"type": "settings-template-edit-btn", "index": tmpl["id"]},
                                        color="primary",
                                        size="sm",
                                        outline=True,
                                        className="float-end",
                                    ),
                                ], width=2, className="text-end"),
                            ], align="center"),
                        ]),
                    ], className="mb-3"),
                ], width=4),
            )

        content = dbc.Row(template_cards)

    return html.Div([
        dbc.Card([
            dbc.CardHeader(html.H5("Budget Templates", className="mb-0")),
            dbc.CardBody([
                html.P("View and edit budget templates with live balance tracking.", className="text-muted mb-3"),
                content,
            ]),
        ]),
        # Template editor modal
        create_template_editor_modal(),
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


# Template editor callbacks
def create_settings_template_editor_form(template_name, current_items, available_options, income, total_allocated, remaining, template_id):
    """Create the template editor form"""
    return [
        html.H5(f"Editing Template: {template_name}", className="mb-3"),
        html.Div(
            id="settings-template-live-summary",
            children=[
                dbc.Alert(
                    [
                        dbc.Row([
                            dbc.Col([
                                html.Strong("Income: "),
                                html.Span(f"€{income:,.2f}"),
                            ], width=3),
                            dbc.Col([
                                html.Strong("Allocated: "),
                                html.Span(f"€{total_allocated:,.2f}"),
                            ], width=3),
                            dbc.Col([
                                html.Strong("Remaining: "),
                                html.Span(
                                    f"€{remaining:,.2f}",
                                    className="text-success" if abs(remaining) < 0.01 else "text-danger",
                                ),
                            ], width=3),
                            dbc.Col([
                                dbc.Badge(
                                    "✓ Zero-Based" if abs(remaining) < 0.01 else "⚠ Not Balanced",
                                    color="success" if abs(remaining) < 0.01 else "warning",
                                )
                            ], width=3, className="text-end"),
                        ])
                    ],
                    color="success" if abs(remaining) < 0.01 else "warning",
                    className="mb-3",
                )
            ],
        ),
        html.Div([
            html.H6("Budget Items", className="mb-3"),
            html.Div(
                id="settings-template-items-list",
                children=[
                    create_settings_template_item_row(item, idx)
                    for idx, item in enumerate(current_items)
                ],
            ),
        ], className="mb-4", style={"maxHeight": "400px", "overflowY": "auto"}),
        dbc.Card([
            dbc.CardBody([
                html.H6("Add Category", className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dcc.Dropdown(
                            id="settings-new-template-category",
                            options=available_options,
                            placeholder="Select category to add...",
                            value=None,
                        )
                    ], width=7),
                    dbc.Col([
                        dbc.Input(
                            id="settings-new-template-amount",
                            type="number",
                            step=0.01,
                            placeholder="Amount (€)",
                            size="sm",
                            value=None,
                        )
                    ], width=4),
                    dbc.Col([
                        dbc.Button(
                            html.I(className="bi bi-plus-circle"),
                            id="settings-add-template-item-btn",
                            color="success",
                            size="sm",
                            className="w-100",
                        )
                    ], width=1),
                ])
            ])
        ], className="mb-3"),
        dcc.Store(
            id="settings-template-edit-data",
            data={"template_id": template_id, "items": current_items},
        ),
    ]


def create_settings_template_item_row(item, idx):
    """Create a row for a template item"""
    type_colors = {
        "Income": "secondary",
        "Savings": "success",
        "Needs": "primary",
        "Wants": "info",
        "Unexpected": "warning",
        "Additional": "dark",
    }

    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Badge(
                        item["budget_type"],
                        color=type_colors.get(item["budget_type"], "secondary"),
                        className="me-2",
                    ),
                    html.Span(item["category"], className="fw-bold"),
                ], width=6),
                dbc.Col([
                    dbc.InputGroup([
                        dbc.InputGroupText("€"),
                        dbc.Input(
                            id={"type": "settings-template-amount", "index": idx},
                            type="number",
                            step=0.01,
                            value=item["amount"],
                            size="sm",
                        ),
                    ], size="sm")
                ], width=5),
                dbc.Col([
                    dbc.Button(
                        html.I(className="bi bi-trash"),
                        id={"type": "settings-delete-template-item", "index": idx},
                        color="danger",
                        size="sm",
                        outline=True,
                        disabled=(item["budget_type"] == "Income"),
                    )
                ], width=1, className="text-end"),
            ], align="center")
        ], className="py-2")
    ], className="mb-2")


@callback(
    [
        Output("settings-template-editor-modal", "is_open"),
        Output("settings-template-editor-form", "children"),
    ],
    [
        Input({"type": "settings-template-edit-btn", "index": dash.ALL}, "n_clicks"),
        Input("settings-cancel-template-edit", "n_clicks"),
        Input("settings-save-template-edit", "n_clicks"),
    ],
    [
        State("settings-template-editor-modal", "is_open"),
    ],
    prevent_initial_call=True,
)
def toggle_settings_template_modal(edit_clicks, cancel_click, save_click, is_open):
    """Toggle the template editor modal"""
    # Check if any edit button was actually clicked
    if not any(edit_clicks or []):
        # If no edit button clicked, check if cancel/save was clicked
        if dash.ctx.triggered_id in ["settings-cancel-template-edit", "settings-save-template-edit"]:
            return False, []
        return is_open, dash.no_update

    trigger = dash.ctx.triggered_id

    # Check if an edit button was clicked
    if trigger and isinstance(trigger, dict) and trigger.get("type") == "settings-template-edit-btn":
        template_id = trigger["index"]

        # Get template data
        template_info = db.fetch_one(
            "SELECT name FROM budget_templates WHERE id = ?", (template_id,)
        )
        if not template_info:
            raise PreventUpdate

        template_name = template_info[0]

        # Get template items
        template_items = db.fetch_df(
            """
            SELECT budget_type, category, budgeted_amount
            FROM template_categories
            WHERE template_id = ?
            ORDER BY
                CASE budget_type
                    WHEN 'Income' THEN 1
                    WHEN 'Savings' THEN 2
                    WHEN 'Needs' THEN 3
                    WHEN 'Wants' THEN 4
                    WHEN 'Unexpected' THEN 5
                    ELSE 6
                END,
                category
            """,
            (template_id,)
        )

        current_items = [
            {
                "key": f"{row['budget_type']}|{row['category']}",
                "budget_type": row["budget_type"],
                "category": row["category"],
                "amount": float(row["budgeted_amount"]),
            }
            for _, row in template_items.iterrows()
        ]

        # Get available categories
        all_categories = db.fetch_df("""
            SELECT DISTINCT budget_type, category
            FROM categories
            WHERE is_active = 1
            ORDER BY budget_type, category
        """)

        existing_keys = {item["key"] for item in current_items}
        available_options = [
            {
                "label": f"{row['budget_type']} → {row['category']}",
                "value": f"{row['budget_type']}|{row['category']}",
            }
            for _, row in all_categories.iterrows()
            if f"{row['budget_type']}|{row['category']}" not in existing_keys
        ]

        # Calculate totals
        income = sum(item["amount"] for item in current_items if item["budget_type"] == "Income")
        total_allocated = sum(item["amount"] for item in current_items if item["budget_type"] != "Income")
        remaining = income - total_allocated

        form = create_settings_template_editor_form(
            template_name, current_items, available_options, income, total_allocated, remaining, template_id
        )

        return True, form

    elif trigger in ["settings-cancel-template-edit", "settings-save-template-edit"]:
        return False, []

    return is_open, dash.no_update


@callback(
    [
        Output("settings-template-edit-data", "data", allow_duplicate=True),
        Output("settings-template-live-summary", "children"),
    ],
    [Input({"type": "settings-template-amount", "index": dash.ALL}, "value")],
    [State("settings-template-edit-data", "data")],
    prevent_initial_call=True,
)
def update_settings_template_totals(amounts, template_data):
    """Update the live summary when amounts change"""
    if not template_data or not amounts:
        raise PreventUpdate

    for i, amount in enumerate(amounts):
        if i < len(template_data["items"]) and amount is not None:
            template_data["items"][i]["amount"] = float(amount) if amount else 0

    income = sum(
        item["amount"] for item in template_data["items"] if item["budget_type"] == "Income"
    )
    total_allocated = sum(
        item["amount"] for item in template_data["items"] if item["budget_type"] != "Income"
    )
    remaining = income - total_allocated

    summary = dbc.Alert([
        dbc.Row([
            dbc.Col([
                html.Strong("Income: "),
                html.Span(f"€{income:,.2f}")
            ], width=3),
            dbc.Col([
                html.Strong("Allocated: "),
                html.Span(f"€{total_allocated:,.2f}"),
            ], width=3),
            dbc.Col([
                html.Strong("Remaining: "),
                html.Span(
                    f"€{remaining:,.2f}",
                    className="text-success" if abs(remaining) < 0.01 else "text-danger",
                ),
            ], width=3),
            dbc.Col([
                dbc.Badge(
                    "✓ Zero-Based" if abs(remaining) < 0.01 else "⚠ Not Balanced",
                    color="success" if abs(remaining) < 0.01 else "warning",
                )
            ], width=3, className="text-end"),
        ])
    ], color="success" if abs(remaining) < 0.01 else "warning", className="mb-3")

    return template_data, summary


@callback(
    [
        Output("settings-template-edit-data", "data", allow_duplicate=True),
        Output("settings-template-items-list", "children"),
        Output("settings-new-template-category", "options"),
        Output("settings-new-template-category", "value"),
        Output("settings-new-template-amount", "value"),
    ],
    [Input("settings-add-template-item-btn", "n_clicks")],
    [
        State("settings-new-template-category", "value"),
        State("settings-new-template-amount", "value"),
        State("settings-template-edit-data", "data"),
    ],
    prevent_initial_call=True,
)
def add_settings_template_item(n_clicks, new_category, new_amount, template_data):
    """Add a new item to the template"""
    if not n_clicks or not template_data or not new_category or not new_amount or new_amount <= 0:
        raise PreventUpdate

    parts = new_category.split("|")
    if len(parts) != 2:
        raise PreventUpdate

    budget_type, cat = parts

    exists = any(
        item["budget_type"] == budget_type and item["category"] == cat
        for item in template_data["items"]
    )

    if not exists:
        template_data["items"].append({
            "key": new_category,
            "budget_type": budget_type,
            "category": cat,
            "amount": float(new_amount),
        })

    all_categories = db.fetch_df("""
        SELECT DISTINCT budget_type, category
        FROM categories
        WHERE is_active = 1
        ORDER BY budget_type, category
    """)

    existing_keys = {item["key"] for item in template_data["items"]}
    available_options = [
        {
            "label": f"{row['budget_type']} → {row['category']}",
            "value": f"{row['budget_type']}|{row['category']}",
        }
        for _, row in all_categories.iterrows()
        if f"{row['budget_type']}|{row['category']}" not in existing_keys
    ]

    items_list = [
        create_settings_template_item_row(item, idx)
        for idx, item in enumerate(template_data["items"])
    ]

    return template_data, items_list, available_options, None, None


@callback(
    [
        Output("settings-template-edit-data", "data", allow_duplicate=True),
        Output("settings-template-items-list", "children", allow_duplicate=True),
        Output("settings-new-template-category", "options", allow_duplicate=True),
    ],
    [Input({"type": "settings-delete-template-item", "index": dash.ALL}, "n_clicks")],
    [State("settings-template-edit-data", "data")],
    prevent_initial_call=True,
)
def delete_settings_template_item(n_clicks, template_data):
    """Delete an item from the template"""
    if not any(n_clicks or []) or not template_data:
        raise PreventUpdate

    button_id = dash.ctx.triggered_id
    if not button_id:
        raise PreventUpdate

    idx = button_id["index"]

    if 0 <= idx < len(template_data["items"]):
        template_data["items"].pop(idx)

    all_categories = db.fetch_df("""
        SELECT DISTINCT budget_type, category
        FROM categories
        WHERE is_active = 1
        ORDER BY budget_type, category
    """)

    existing_keys = {item["key"] for item in template_data["items"]}
    available_options = [
        {
            "label": f"{row['budget_type']} → {row['category']}",
            "value": f"{row['budget_type']}|{row['category']}",
        }
        for _, row in all_categories.iterrows()
        if f"{row['budget_type']}|{row['category']}" not in existing_keys
    ]

    items_list = [
        create_settings_template_item_row(item, idx)
        for idx, item in enumerate(template_data["items"])
    ]

    return template_data, items_list, available_options


@callback(
    [
        Output("settings-template-editor-modal", "is_open", allow_duplicate=True),
        Output("refresh-trigger", "data", allow_duplicate=True),
    ],
    [Input("settings-save-template-edit", "n_clicks")],
    [
        State({"type": "settings-template-amount", "index": dash.ALL}, "value"),
        State("settings-template-edit-data", "data"),
        State("refresh-trigger", "data"),
    ],
    prevent_initial_call=True,
)
def save_settings_template(save_click, amounts, template_data, current_refresh):
    """Save the template changes"""
    if not save_click or not template_data or not amounts:
        raise PreventUpdate

    target_template_id = template_data["template_id"]

    # Delete existing template categories
    db.write_execute(
        "DELETE FROM template_categories WHERE template_id = ?",
        (target_template_id,),
    )

    # Insert updated categories
    for i, amount in enumerate(amounts):
        if amount and amount > 0 and i < len(template_data["items"]):
            item = template_data["items"][i]
            db.write_execute(
                """
                INSERT INTO template_categories
                (template_id, budget_type, category, subcategory, budgeted_amount)
                VALUES (?, ?, ?, NULL, ?)
                """,
                (target_template_id, item["budget_type"], item["category"], float(amount)),
            )

    return False, datetime.now().isoformat()


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
