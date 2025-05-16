import os
import datetime
import json
import email.utils
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from typing import List, Dict, Any


class PDFGenerator:
    def __init__(self):
        self.output_dir = "reports"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        self.styles = getSampleStyleSheet()
        # Create custom styles using built-in fonts
        self.styles.add(
            ParagraphStyle(
                name="CustomTitle",
                parent=self.styles["Heading1"],
                fontSize=16,
                spaceAfter=30,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="CustomBody",
                parent=self.styles["Normal"],
                fontSize=10,
                spaceAfter=12,
            )
        )

    def parse_date(self, date_str):
        """Parse date string in RFC 2822 format."""
        try:
            # Try parsing as RFC 2822 format
            parsed_date = email.utils.parsedate_to_datetime(date_str)
            return parsed_date
        except (TypeError, ValueError):
            try:
                # Fallback to ISO format
                return datetime.datetime.fromisoformat(date_str)
            except (TypeError, ValueError):
                # Return epoch if parsing fails
                return datetime.datetime(1970, 1, 1)

    def extract_deadline(self, analysis_str):
        """Extract deadline from analysis string."""
        if not isinstance(analysis_str, str):
            return ""

        try:
            # Parse the JSON response
            analysis_data = json.loads(analysis_str)

            # The deadline is directly in the root of the JSON
            if isinstance(analysis_data, dict):
                deadline = analysis_data.get("deadline", "")
                # If deadline is "No deadline", return empty string
                return "" if deadline == "No deadline" else deadline

            return ""
        except json.JSONDecodeError:
            return ""

    def format_analysis(self, analysis_str):
        """Format analysis string without deadline information."""
        if not isinstance(analysis_str, str):
            return str(analysis_str)

        try:
            # Parse the JSON response
            analysis_data = json.loads(analysis_str)
            formatted_text = []

            if isinstance(analysis_data, dict):
                # Add summary
                if "summary" in analysis_data:
                    formatted_text.append(f"Summary: {analysis_data['summary']}")

                # Add impact
                if "impact" in analysis_data:
                    formatted_text.append(f"Impact: {analysis_data['impact']}")

                # Add actions
                if "actions" in analysis_data:
                    actions = analysis_data["actions"]
                    if isinstance(actions, list):
                        formatted_text.append("Recommended Actions:")
                        for action in actions:
                            formatted_text.append(f"• {action}")
                    else:
                        formatted_text.append(f"Actions: {actions}")

            return "\n".join(formatted_text) if formatted_text else analysis_str
        except json.JSONDecodeError:
            return analysis_str

    def generate_report(
        self, entries: List[Dict[str, Any]], output_filename: str = None
    ) -> str:
        """Generate a PDF report of all entries."""
        if not output_filename:
            output_filename = (
                f"report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )

        output_path = os.path.join(self.output_dir, output_filename)

        # Create the PDF document with margins
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            leftMargin=50,
            rightMargin=50,
            topMargin=50,
            bottomMargin=50,
        )
        styles = getSampleStyleSheet()
        elements = []

        # Add title with custom style
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # Center alignment
        )
        elements.append(Paragraph("Hermes Feed Analysis Report", title_style))
        elements.append(
            Paragraph(
                f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                styles["Normal"],
            )
        )
        elements.append(Spacer(1, 20))

        # Add feed summary section
        elements.append(Paragraph("Feed Summary", styles["Heading2"]))
        elements.append(Spacer(1, 10))

        # Count entries per feed
        feed_counts = {}
        for entry in entries:
            feed_name = entry.get("feed_name", "Unknown Feed")
            feed_counts[feed_name] = feed_counts.get(feed_name, 0) + 1

        # Create feed summary table
        feed_summary_data = [["Feed Name", "Number of Entries"]]
        for feed_name, count in sorted(feed_counts.items()):
            feed_summary_data.append([feed_name, str(count)])

        # Calculate feed summary table widths
        page_width = letter[0] - 100  # Account for margins
        feed_summary_widths = [
            page_width * 0.7,
            page_width * 0.3,
        ]  # 70% for name, 30% for count

        # Create feed summary table
        feed_summary_table = Table(
            feed_summary_data, colWidths=feed_summary_widths, repeatRows=1
        )
        feed_summary_table.setStyle(
            TableStyle(
                [
                    # Header styling
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("TOPPADDING", (0, 0), (-1, 0), 12),
                    # Body styling
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                    ("ALIGN", (0, 1), (0, -1), "LEFT"),  # Left align feed names
                    ("ALIGN", (1, 1), (1, -1), "CENTER"),  # Center align counts
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                    ("TOPPADDING", (0, 1), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                    # Grid styling
                    ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#BDC3C7")),
                    ("LINEBELOW", (0, 0), (-1, 0), 2, colors.HexColor("#2C3E50")),
                ]
            )
        )
        elements.append(feed_summary_table)
        elements.append(Spacer(1, 30))

        # Add main entries section title
        elements.append(Paragraph("Detailed Entries", styles["Heading2"]))
        elements.append(Spacer(1, 10))

        # Create table data with headers
        table_data = [["Title", "Published", "Deadline", "Analysis", "Link"]]

        # Add entries to table with better formatting
        for entry in entries:
            try:
                analysis = entry.get("analysis", {})
                if isinstance(analysis, str):
                    analysis = json.loads(analysis)

                # Format the analysis text
                analysis_text = []
                if analysis.get("summary"):
                    analysis_text.append(f"Summary: {analysis.get('summary')}")
                if analysis.get("impact"):
                    analysis_text.append(f"Impact: {analysis.get('impact')}")
                if analysis.get("actions"):
                    actions = analysis.get("actions", [])
                    if isinstance(actions, list):
                        analysis_text.append("Actions:")
                        for action in actions:
                            analysis_text.append(f"• {action}")

                # Get deadline
                deadline = analysis.get("deadline", "No deadline")
                if deadline == "No deadline":
                    deadline = ""

                # Create table row with formatted content
                table_data.append(
                    [
                        Paragraph(entry.get("title", ""), styles["Normal"]),
                        Paragraph(entry.get("published", ""), styles["Normal"]),
                        Paragraph(deadline, styles["Normal"]),
                        Paragraph("\n".join(analysis_text), styles["Normal"]),
                        Paragraph(
                            f'<link href="{entry.get("link", "")}">{entry.get("link", "")}</link>',
                            styles["Normal"],
                        ),
                    ]
                )
            except json.JSONDecodeError:
                continue

        # Calculate column widths based on page width
        page_width = letter[0] - 100  # Account for margins
        col_widths = [
            page_width * 0.25,  # Title
            page_width * 0.15,  # Published
            page_width * 0.15,  # Deadline
            page_width * 0.30,  # Analysis
            page_width * 0.15,  # Link
        ]

        # Create table with calculated widths
        table = Table(table_data, colWidths=col_widths, repeatRows=1)

        # Enhanced table style
        table.setStyle(
            TableStyle(
                [
                    # Header styling
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("TOPPADDING", (0, 0), (-1, 0), 12),
                    # Body styling
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                    ("ALIGN", (0, 1), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                    ("TOPPADDING", (0, 1), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                    # Grid styling
                    ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#BDC3C7")),
                    ("LINEBELOW", (0, 0), (-1, 0), 2, colors.HexColor("#2C3E50")),
                    # Column specific styling
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("WORDWRAP", (0, 0), (-1, -1), True),
                ]
            )
        )

        elements.append(table)

        # Build the PDF
        doc.build(elements)
        return output_path
