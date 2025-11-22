"""
Import Page
Upload CSV files, preview transactions, and import to database
"""

import base64
import io

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate

from import_pipeline.categorizer import Categorizer
from import_pipeline.csv_processor import CSVProcessor
from import_pipeline.import_transactions import TransactionImporter

dash.register_page(__name__, path="/import", title="Import Transactions")

processor = CSVProcessor()
categorizer = Categorizer()
importer = TransactionImporter()


def layout():
    return dbc.Container(
        [
            html.H2("Import Transactions", className="mb-4"),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Alert(
                                [
                                    html.H5(
                                        "📝 How to Import", className="alert-heading"
                                    ),
                                    html.P(
                                        [
                                            "1. Download your credit card statement (CSV format)",
                                            html.Br(),
                                            "2. Upload the file below",
                                            html.Br(),
                                            "3. Review the preview",
                                            html.Br(),
                                            "4. Click 'Import to Database'",
                                        ]
                                    ),
                                    html.Hr(),
                                    html.P(
                                        [
                                            html.Strong("Supported format: "),
                                            "Capital One CSV with columns: Transaction Date, Description, Debit, Credit, Card No.",
                                        ],
                                        className="mb-0",
                                    ),
                                ],
                                color="info",
                            )
                        ]
                    )
                ],
                className="mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.I(className="bi bi-upload me-2"),
                                            "Step 1: Upload CSV File",
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [
                                            dcc.Upload(
                                                id="upload-csv",
                                                children=html.Div(
                                                    [
                                                        html.I(
                                                            className="bi bi-cloud-upload fs-1 text-primary"
                                                        ),
                                                        html.Br(),
                                                        html.Br(),
                                                        html.H5(
                                                            "Drag and Drop or Click to Select"
                                                        ),
                                                        html.P(
                                                            "CSV files only",
                                                            className="text-muted",
                                                        ),
                                                    ]
                                                ),
                                                style={
                                                    "width": "100%",
                                                    "height": "200px",
                                                    "lineHeight": "200px",
                                                    "borderWidth": "2px",
                                                    "borderStyle": "dashed",
                                                    "borderRadius": "10px",
                                                    "textAlign": "center",
                                                    "cursor": "pointer",
                                                    "backgroundColor": "#f8f9fa",
                                                },
                                                multiple=True,
                                            ),
                                            html.Div(
                                                id="upload-status", className="mt-3"
                                            ),
                                        ]
                                    ),
                                ]
                            )
                        ]
                    )
                ],
                className="mb-4",
            ),
            dbc.Row(
                [dbc.Col([html.Div(id="preview-section", style={"display": "none"})])],
                className="mb-4",
            ),
            dbc.Row(
                [dbc.Col([html.Div(id="import-section", style={"display": "none"})])]
            ),
            dcc.Store(id="processed-data-store"),
            dcc.Store(id="import-ready-store"),
            dbc.Modal(
                [
                    dbc.ModalHeader("Import Complete!"),
                    dbc.ModalBody(id="import-result-body"),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "View Transactions",
                                href="/transactions",
                                color="primary",
                            ),
                            dbc.Button(
                                "Import More",
                                id="import-another",
                                color="secondary",
                                outline=True,
                            ),
                        ]
                    ),
                ],
                id="import-complete-modal",
                size="lg",
                is_open=False,
            ),
        ],
        fluid=True,
    )


@callback(
    [
        Output("upload-status", "children"),
        Output("preview-section", "children"),
        Output("preview-section", "style"),
        Output("processed-data-store", "data"),
    ],
    [Input("upload-csv", "contents")],
    [State("upload-csv", "filename")],
)
def process_uploaded_files(list_of_contents, list_of_names):
    """Process uploaded CSV files"""
    if list_of_contents is None:
        raise PreventUpdate

    try:
        all_dfs = []

        for contents, filename in zip(list_of_contents, list_of_names):
            content_type, content_string = contents.split(",")
            decoded = base64.b64decode(content_string)

            try:
                df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))
                all_dfs.append(df)
            except Exception as e:
                return (
                    dbc.Alert(f"Error reading {filename}: {str(e)}", color="danger"),
                    None,
                    {"display": "none"},
                    None,
                )

        combined_df = pd.concat(all_dfs, ignore_index=True)

        processor = CSVProcessor()
        processor.raw_data = combined_df
        processed_df = processor.process()

        categorizer = Categorizer()
        categorized_df = categorizer.categorize_batch(processed_df)

        summary = processor.get_summary()

        from database.db import db

        existing_uuids = set(
            row[0] for row in db.fetch_all("SELECT uuid FROM transactions")
        )
        new_mask = ~categorized_df["UUID"].isin(existing_uuids)
        new_count = new_mask.sum()
        duplicate_count = (~new_mask).sum()

        status = dbc.Alert(
            [
                html.H5(
                    "✅ File(s) Processed Successfully!", className="alert-heading"
                ),
                html.P(
                    [
                        f"Loaded {len(list_of_names)} file(s) with {len(combined_df)} total rows",
                        html.Br(),
                        f"Processed {len(processed_df)} transactions",
                        html.Br(),
                        f"New transactions: {new_count}",
                        html.Br(),
                        f"Duplicates (will skip): {duplicate_count}",
                    ]
                ),
            ],
            color="success",
        )

        preview = create_preview_section(categorized_df, new_mask, summary)

        stored_data = {
            "data": categorized_df.to_dict("records"),
            "new_mask": new_mask.tolist(),
            "summary": summary,
        }

        return status, preview, {"display": "block"}, stored_data

    except Exception as e:
        error = dbc.Alert(
            [
                html.H5("❌ Error Processing File", className="alert-heading"),
                html.P(str(e)),
            ],
            color="danger",
        )
        return error, None, {"display": "none"}, None


def create_preview_section(df, new_mask, summary):
    """Create preview section with transaction table"""

    new_df = df[new_mask].head(50)

    if len(new_df) == 0:
        return dbc.Card(
            [
                dbc.CardHeader([html.I(className="bi bi-eye me-2"), "Step 2: Preview"]),
                dbc.CardBody(
                    [
                        dbc.Alert(
                            [
                                html.H5(
                                    "No New Transactions", className="alert-heading"
                                ),
                                html.P(
                                    "All transactions in this file have already been imported."
                                ),
                            ],
                            color="warning",
                        )
                    ]
                ),
            ]
        )

    stats = dbc.Row(
        [
            dbc.Col(
                [
                    html.Small("Total New", className="text-muted d-block"),
                    html.Strong(str(new_mask.sum())),
                ],
                width=2,
            ),
            dbc.Col(
                [
                    html.Small("Your Transactions", className="text-muted d-block"),
                    html.Strong(
                        f"{summary['your_count']} (${summary['your_amount']:.2f})"
                    ),
                ],
                width=3,
            ),
            dbc.Col(
                [
                    html.Small("Quorum", className="text-muted d-block"),
                    html.Strong(
                        f"{summary['quorum_count']} (${summary['quorum_amount']:.2f})",
                        className="text-success",
                    ),
                ],
                width=2,
            ),
            dbc.Col(
                [
                    html.Small("Auto-categorized", className="text-muted d-block"),
                    html.Strong(f"{(df['CONFIDENCE'] > 0).sum()} / {len(df)}"),
                ],
                width=3,
            ),
        ],
        className="mb-3",
    )

    table = create_preview_table(new_df)

    import_btn = dbc.Button(
        [
            html.I(className="bi bi-download me-2"),
            f"Import {new_mask.sum()} Transactions",
        ],
        id="import-btn",
        color="primary",
        size="lg",
        className="w-100",
    )

    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.I(className="bi bi-eye me-2"),
                    f"Step 2: Preview (Showing first {len(new_df)} of {new_mask.sum()} new transactions)",
                ]
            ),
            dbc.CardBody(
                [
                    stats,
                    html.Div(table, style={"maxHeight": "400px", "overflowY": "auto"}),
                    html.Hr(),
                    import_btn,
                ]
            ),
        ]
    )


def create_preview_table(df):
    """Create preview table"""

    header = html.Thead(
        html.Tr(
            [
                html.Th("Date", style={"width": "100px"}),
                html.Th("Merchant"),
                html.Th("Amount", className="text-end", style={"width": "100px"}),
                html.Th("Category", style={"width": "150px"}),
                html.Th(
                    "Confidence", className="text-center", style={"width": "100px"}
                ),
            ]
        )
    )

    rows = []
    for _, row in df.iterrows():
        if row["CONFIDENCE"] == 0:
            row_class = "table-warning"
            conf_badge = dbc.Badge("Manual", color="warning")
        elif row["CONFIDENCE"] >= 80:
            row_class = ""
            conf_badge = dbc.Badge(f"{row['CONFIDENCE']}%", color="success")
        else:
            row_class = ""
            conf_badge = dbc.Badge(f"{row['CONFIDENCE']}%", color="info")

        amount_display = f"${row['AMOUNT']:.2f}"
        category_display = "Quorum" if row["IS_QUORUM"] else row["SUBCATEGORY"]

        rows.append(
            html.Tr(
                [
                    html.Td(str(row["DATE"]).split()[0]),
                    html.Td(row["DESCRIPTION"][:50]),
                    html.Td(html.Strong(amount_display), className="text-end"),
                    html.Td(category_display),
                    html.Td(conf_badge, className="text-center"),
                ],
                className=row_class,
            )
        )

    body = html.Tbody(rows)

    return dbc.Table(
        [header, body],
        striped=True,
        hover=True,
        responsive=True,
        size="sm",
        className="mb-0",
    )


@callback(
    [
        Output("import-complete-modal", "is_open"),
        Output("import-result-body", "children"),
    ],
    [Input("import-btn", "n_clicks")],
    [State("processed-data-store", "data")],
    prevent_initial_call=True,
)
def import_to_database(n_clicks, stored_data):
    """Import transactions to database"""
    if not n_clicks or not stored_data:
        raise PreventUpdate

    try:
        df = pd.DataFrame(stored_data["data"])
        new_mask = pd.Series(stored_data["new_mask"])

        new_df = df[new_mask]

        if len(new_df) == 0:
            result = dbc.Alert("No new transactions to import", color="warning")
            return True, result

        importer = TransactionImporter()

        importer.categorized_data = new_df
        new_df = importer.fetch_exchange_rates(new_df)
        new_df = importer.prepare_import(new_df)

        inserted, skipped, errors = importer.import_to_database(new_df)

        result = [
            html.H5("🎉 Import Successful!", className="text-success"),
            html.Hr(),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.P(
                                [html.Strong("Imported: "), f"{inserted} transactions"]
                            )
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [html.P([html.Strong("Skipped: "), f"{skipped} (duplicates)"])],
                        width=6,
                    ),
                ]
            ),
        ]

        if errors:
            result.append(
                dbc.Alert(
                    [
                        html.Strong(f"⚠️ {len(errors)} errors occurred"),
                        html.Ul(
                            [
                                html.Li(f"{e['transaction']}: {e['error']}")
                                for e in errors[:5]
                            ]
                        ),
                    ],
                    color="warning",
                )
            )
        else:
            result.append(
                dbc.Alert("All transactions imported successfully! ✅", color="success")
            )

        return True, result

    except Exception as e:
        error_result = dbc.Alert(
            [html.H5("❌ Import Failed", className="alert-heading"), html.P(str(e))],
            color="danger",
        )
        return True, error_result


@callback(
    [
        Output("upload-csv", "contents"),
        Output("import-complete-modal", "is_open", allow_duplicate=True),
    ],
    [Input("import-another", "n_clicks")],
    prevent_initial_call=True,
)
def reset_for_another_import(n_clicks):
    """Reset the page for another import"""
    if not n_clicks:
        raise PreventUpdate
    return None, False
