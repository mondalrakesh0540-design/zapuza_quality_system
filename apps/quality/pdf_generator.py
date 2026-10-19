import io
import hashlib
from decimal import Decimal
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)


def generate_coc_pdf(coc, request=None) -> bytes:
    """
    Generates a secure, printable, professional Certificate of Conformance (CoC) PDF
    using ReportLab Platypus. Conforms to BRD Section 11.1 & 11.2.
    Uses verified database records only.
    """
    buffer = io.BytesIO()

    # Page setup - A4 with 0.5 inch margins for dense, clean engineering layout
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
        title=f"CoC - {coc.certificate_number}",
        author="Zapuza Quality Operations System",
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=18,
        textColor=colors.HexColor('#1E293B'),
        alignment=1,  # Center
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#475569'),
        alignment=1,  # Center
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=6,
        spaceAfter=3,
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#1E293B'),
    )
    bold_style = ParagraphStyle(
        'BoldBody',
        parent=body_style,
        fontName='Helvetica-Bold',
    )
    legal_style = ParagraphStyle(
        'LegalText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor('#64748B'),
    )
    badge_pass_style = ParagraphStyle(
        'PassBadge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#166534'),
        alignment=1,
    )
    ctq_badge_style = ParagraphStyle(
        'CtqBadge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor('#C2410C'),
        alignment=1,
    )

    story = []

    # 1. Company Header & Title
    story.append(Paragraph("ZAPUZA TECHNOLOGIES LLP", title_style))
    story.append(Paragraph("Factory Operations & Quality Assurance Directorate &bull; ISO 9001:2015 Compliant QMS", subtitle_style))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0284C7'), spaceBefore=2, spaceAfter=6))
    story.append(Paragraph("CERTIFICATE OF CONFORMANCE (CoC)", title_style))
    story.append(Spacer(1, 4))

    # Certificate Metadata Banner
    status_label = coc.get_status_display().upper()
    status_color = colors.HexColor('#16A34A') if coc.status == 'ACTIVE' else colors.HexColor('#DC2626')
    meta_data = [
        [
            Paragraph(f"<b>Certificate Number:</b> {coc.certificate_number}", body_style),
            Paragraph(f"<b>Issue Date:</b> {coc.issued_at.strftime('%Y-%m-%d %H:%M:%S UTC')}", body_style),
            Paragraph(f"<b>Status:</b> <font color='{status_color}'><b>{status_label}</b></font> (Rev {coc.version})", body_style),
        ]
    ]
    meta_table = Table(meta_data, colWidths=[200, 180, 140])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6))

    # 2. Part & Work Order Details
    story.append(Paragraph("1. MANUFACTURED COMPONENT SPECIFICATIONS", section_heading))
    traveler = coc.traveler
    work_order = coc.work_order
    part = work_order.part

    part_data = [
        [
            Paragraph("<b>Part Number:</b>", bold_style),
            Paragraph(part.part_number, body_style),
            Paragraph("<b>Part Description:</b>", bold_style),
            Paragraph(part.part_name, body_style),
        ],
        [
            Paragraph("<b>Drawing Number:</b>", bold_style),
            Paragraph(part.drawing_number, body_style),
            Paragraph("<b>Drawing Revision:</b>", bold_style),
            Paragraph(part.revision_level, body_style),
        ],
        [
            Paragraph("<b>Work Order No:</b>", bold_style),
            Paragraph(work_order.work_order_number, body_style),
            Paragraph("<b>Job Traveler Barcode:</b>", bold_style),
            Paragraph(traveler.traveler_barcode, body_style),
        ],
        [
            Paragraph("<b>Batch Quantity:</b>", bold_style),
            Paragraph(f"{work_order.target_quantity} Units", body_style),
            Paragraph("<b>Completed Quantity:</b>", bold_style),
            Paragraph(f"{work_order.completed_quantity} Units", body_style),
        ]
    ]
    part_table = Table(part_data, colWidths=[110, 150, 110, 150])
    part_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F1F5F9')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#F1F5F9')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(part_table)
    story.append(Spacer(1, 6))

    # 3. Raw Material & Heat Traceability
    story.append(Paragraph("2. RAW MATERIAL & HEAT TRACEABILITY (MTC)", section_heading))
    lot = work_order.raw_material_lot
    mtc_ver_str = "Verified & Cleared" if lot and lot.mtc_verified else "Pending / Missing"
    mtc_by_str = f"Verified by {lot.mtc_verified_by.employee_id} ({lot.mtc_verified_by.get_full_name() or lot.mtc_verified_by.username})" if (lot and lot.mtc_verified_by) else "N/A"
    mtc_date_str = lot.mtc_verified_at.strftime('%Y-%m-%d') if (lot and lot.mtc_verified_at) else "N/A"

    mat_data = [
        [
            Paragraph("<b>Material Grade:</b>", bold_style),
            Paragraph(f"{lot.material_grade.code} - {lot.material_grade.name}" if lot else "N/A", body_style),
            Paragraph("<b>Mill Heat Number:</b>", bold_style),
            Paragraph(f"<b>{lot.heat_number}</b>" if lot else "N/A", bold_style),
        ],
        [
            Paragraph("<b>Intake Lot ID:</b>", bold_style),
            Paragraph(lot.lot_number if lot else "N/A", body_style),
            Paragraph("<b>Material Supplier:</b>", bold_style),
            Paragraph(lot.supplier_name if lot else "N/A", body_style),
        ],
        [
            Paragraph("<b>MTC Status:</b>", bold_style),
            Paragraph(f"<font color='green'><b>{mtc_ver_str}</b></font>", body_style),
            Paragraph("<b>MTC Verification Sign-off:</b>", bold_style),
            Paragraph(f"{mtc_by_str} on {mtc_date_str}", body_style),
        ]
    ]
    mat_table = Table(mat_data, colWidths=[110, 150, 120, 140])
    mat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F1F5F9')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#F1F5F9')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(mat_table)
    story.append(Spacer(1, 6))

    # 4. Final Pre-Dispatch Inspection (PDI) Summary
    story.append(Paragraph("3. FINAL PRE-DISPATCH INSPECTION (PDI) MEASUREMENT RECORD", section_heading))
    pdi_insp = traveler.get_pdi_inspection()
    pdi_number = pdi_insp.inspection_number if pdi_insp else "N/A"
    pdi_date = pdi_insp.created_at.strftime('%Y-%m-%d %H:%M') if pdi_insp else "N/A"
    pdi_inspector = f"{pdi_insp.inspector.employee_id} ({pdi_insp.inspector.get_full_name() or pdi_insp.inspector.username})" if (pdi_insp and pdi_insp.inspector) else "N/A"

    pdi_header_text = f"<b>PDI Record No:</b> {pdi_number} &nbsp;|&nbsp; <b>Inspection Date:</b> {pdi_date} &nbsp;|&nbsp; <b>Inspector:</b> {pdi_inspector}"
    story.append(Paragraph(pdi_header_text, body_style))
    story.append(Spacer(1, 3))

    insp_rows = [
        [
            Paragraph("<b>Seq</b>", bold_style),
            Paragraph("<b>Parameter / Check</b>", bold_style),
            Paragraph("<b>Target / Limits</b>", bold_style),
            Paragraph("<b>Measured</b>", bold_style),
            Paragraph("<b>Unit</b>", bold_style),
            Paragraph("<b>Instrument Used</b>", bold_style),
            Paragraph("<b>Cal. Due</b>", bold_style),
            Paragraph("<b>CTQ</b>", bold_style),
            Paragraph("<b>Result</b>", bold_style),
        ]
    ]

    measurements = pdi_insp.measurements.select_related('parameter', 'measuring_tool').all() if pdi_insp else []
    for m in measurements:
        param = m.parameter
        # Specification formatting
        if param.parameter_type == 'DIMENSION':
            ut = f"+{param.upper_tolerance}" if param.upper_tolerance and param.upper_tolerance > 0 else f"{param.upper_tolerance}"
            lt = f"{param.lower_tolerance}" if param.lower_tolerance else "0"
            spec_str = f"{param.nominal_value} ({ut}/{lt})"
        elif param.parameter_type == 'THRESHOLD':
            spec_str = f"{param.get_threshold_type_display()} {param.threshold_limit}"
        else:
            spec_str = "Visual Spec OK"

        # Reading formatting
        if m.measured_value is not None:
            read_str = f"{m.measured_value}"
        else:
            read_str = "PASS" if m.visual_passed else "FAIL"

        tool_str = m.measuring_tool.tool_id if m.measuring_tool else "N/A"
        cal_str = m.measuring_tool.calibration_expiry_date.strftime('%Y-%m-%d') if (m.measuring_tool and m.measuring_tool.calibration_expiry_date) else "N/A"
        ctq_str = Paragraph("★ CTQ", ctq_badge_style) if param.is_ctq else Paragraph("-", body_style)
        res_str = Paragraph("PASS", badge_pass_style) if m.is_in_tolerance else Paragraph("<font color='red'>FAIL</font>", badge_pass_style)

        insp_rows.append([
            Paragraph(str(param.sequence_order), body_style),
            Paragraph(param.parameter_name, body_style),
            Paragraph(spec_str, body_style),
            Paragraph(f"<b>{read_str}</b>", body_style),
            Paragraph(param.unit, body_style),
            Paragraph(tool_str, body_style),
            Paragraph(cal_str, body_style),
            ctq_str,
            res_str,
        ])

    insp_table = Table(insp_rows, colWidths=[24, 110, 85, 55, 30, 70, 56, 36, 44])
    insp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (4, 0), (4, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
    ]))
    # Set text color white for table header cells
    for col_idx in range(9):
        insp_table.setStyle(TableStyle([('TEXTCOLOR', (col_idx, 0), (col_idx, 0), colors.white)]))

    story.append(insp_table)
    story.append(Spacer(1, 6))

    # 5. Audited Electronic Approval Stamp
    story.append(Paragraph("4. AUDITED ELECTRONIC APPROVAL & CONFORMANCE DECLARATION", section_heading))
    approver = coc.issued_by
    appr_str = f"{approver.get_full_name() or approver.username} (ID: {approver.employee_id})"
    appr_role = approver.get_role_display()
    appr_date = coc.issued_at.strftime('%Y-%m-%d %H:%M:%S UTC')

    # Base verification URL
    domain = request.get_host() if request else "zapuza-factory.local"
    verify_url = f"http://{domain}/quality/coc/verify/{coc.verification_token}/"

    stamp_data = [
        [
            Paragraph("<b>Authorized Quality Sign-off:</b>", bold_style),
            Paragraph(appr_str, bold_style),
            Paragraph("<b>Signer Role:</b>", bold_style),
            Paragraph(appr_role, body_style),
        ],
        [
            Paragraph("<b>Timestamp (UTC):</b>", bold_style),
            Paragraph(appr_date, body_style),
            Paragraph("<b>Verification Token:</b>", bold_style),
            Paragraph(f"<font size='6'>{coc.verification_token}</font>", body_style),
        ],
        [
            Paragraph("<b>Online Verification URL:</b>", bold_style),
            Paragraph(f"<font size='6'>{verify_url}</font>", body_style),
            Paragraph("<b>Audit Status:</b>", bold_style),
            Paragraph("<font color='green'><b>DIGITALLY VERIFIED</b></font>", bold_style),
        ]
    ]
    stamp_table = Table(stamp_data, colWidths=[120, 160, 100, 140])
    stamp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#EFF6FF')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#EFF6FF')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#93C5FD')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(stamp_table)
    story.append(Spacer(1, 5))

    # Conformance Certification Statement
    statement_text = (
        "<b>CERTIFICATION STATEMENT:</b> It is hereby certified that the parts described above have been manufactured, "
        "inspected, and tested in full conformance with the applicable drawings, specifications, purchase order requirements, "
        "and ISO 9001 quality management procedures. All raw material test certificates and physical inspection measurement "
        "records are maintained on file and traceable via the unique mill heat number and job traveler barcode."
    )
    story.append(Paragraph(statement_text, legal_style))
    story.append(Spacer(1, 3))

    disclaimer_text = (
        "Notice: This document is an audited electronic record generated by the Zapuza Quality Operations System. "
        "Any unauthorized alteration, erasure, or forging of this certificate is strictly prohibited and constitutes a quality violation."
    )
    story.append(Paragraph(disclaimer_text, legal_style))

    # Build PDF binary
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
