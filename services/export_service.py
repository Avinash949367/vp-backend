from typing import Dict, Any, List
from datetime import datetime, timedelta
from models import Trip, Activity, Expense
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import io
import calendar as cal

class ExportService:
    def __init__(self):
        self.styles = getSampleStyleSheet()

    def generate_trip_pdf(self, trip: Trip, activities: List[Activity], expenses: List[Expense]) -> bytes:
        """Generate a PDF report for a trip"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        story.append(Paragraph(f"Trip Report: {trip.title}", title_style))
        story.append(Spacer(1, 12))

        # Trip details
        story.append(Paragraph(f"<b>Destination:</b> {trip.destination}", self.styles['Normal']))
        story.append(Paragraph(f"<b>Dates:</b> {trip.start_date.strftime('%B %d, %Y')} - {trip.end_date.strftime('%B %d, %Y')}", self.styles['Normal']))
        story.append(Paragraph(f"<b>Budget:</b> ${trip.budget:.2f}", self.styles['Normal']))
        story.append(Spacer(1, 20))

        # Activities section
        if activities:
            story.append(Paragraph("Activities", self.styles['Heading2']))
            story.append(Spacer(1, 12))

            activity_data = [['Date', 'Time', 'Activity', 'Location', 'Cost']]
            for activity in sorted(activities, key=lambda x: (x.day, x.time)):
                activity_data.append([
                    f"Day {activity.day}",
                    activity.time,
                    activity.title,
                    activity.location,
                    f"${activity.cost:.2f}" if activity.cost else "N/A"
                ])

            activity_table = Table(activity_data)
            activity_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(activity_table)
            story.append(Spacer(1, 20))

        # Expenses section
        if expenses:
            story.append(Paragraph("Expenses", self.styles['Heading2']))
            story.append(Spacer(1, 12))

            expense_data = [['Date', 'Category', 'Description', 'Amount']]
            total_expenses = 0
            for expense in sorted(expenses, key=lambda x: x.date):
                expense_data.append([
                    expense.date.strftime('%m/%d/%Y'),
                    expense.category.title(),
                    expense.title,
                    f"${expense.amount:.2f}"
                ])
                total_expenses += expense.amount

            expense_table = Table(expense_data)
            expense_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(expense_table)

            # Total expenses
            story.append(Spacer(1, 12))
            story.append(Paragraph(f"<b>Total Expenses: ${total_expenses:.2f}</b>", self.styles['Normal']))
            story.append(Paragraph(f"<b>Remaining Budget: ${trip.budget - total_expenses:.2f}</b>", self.styles['Normal']))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def generate_calendar_ics(self, trip: Trip, activities: List[Activity]) -> str:
        """Generate an ICS calendar file for trip activities"""
        ics_content = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//TravelMate//Trip Calendar//EN",
            f"X-WR-CALNAME:{trip.title}",
            f"X-WR-CALDESC:Trip activities for {trip.destination}"
        ]

        for activity in activities:
            # Calculate the actual date for the activity
            activity_date = trip.start_date + timedelta(days=activity.day - 1)

            # Create start and end times
            start_time = datetime.strptime(activity.time, "%H:%M").time()
            start_datetime = datetime.combine(activity_date, start_time)

            # Assume 1 hour duration if not specified
            end_datetime = start_datetime + timedelta(hours=1)

            ics_content.extend([
                "BEGIN:VEVENT",
                f"UID:{activity.id}@travelmate",
                f"DTSTART:{start_datetime.strftime('%Y%m%dT%H%M%S')}",
                f"DTEND:{end_datetime.strftime('%Y%m%dT%H%M%S')}",
                f"SUMMARY:{activity.title}",
                f"LOCATION:{activity.location}",
                f"DESCRIPTION:{activity.notes or ''}",
                "END:VEVENT"
            ])

        ics_content.append("END:VCALENDAR")
        return "\n".join(ics_content)

    def export_trip_data(self, trip: Trip, activities: List[Activity], expenses: List[Expense], format: str = "json") -> str:
        """Export trip data in various formats"""
        data = {
            "trip": {
                "id": str(trip.id),
                "title": trip.title,
                "destination": trip.destination,
                "start_date": trip.start_date.isoformat(),
                "end_date": trip.end_date.isoformat(),
                "budget": trip.budget,
                "notes": trip.notes
            },
            "activities": [
                {
                    "id": str(activity.id),
                    "title": activity.title,
                    "time": activity.time,
                    "location": activity.location,
                    "activity_type": activity.activity_type,
                    "notes": activity.notes,
                    "cost": activity.cost,
                    "day": activity.day
                } for activity in activities
            ],
            "expenses": [
                {
                    "id": str(expense.id),
                    "title": expense.title,
                    "amount": expense.amount,
                    "category": expense.category,
                    "date": expense.date.isoformat(),
                    "notes": expense.notes
                } for expense in expenses
            ]
        }

        if format == "json":
            return json.dumps(data, indent=2)
        else:
            return json.dumps(data)

export_service = ExportService()
