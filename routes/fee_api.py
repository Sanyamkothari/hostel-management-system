"""
API routes for the fee management system
"""
from flask import Blueprint, jsonify, request
from utils.fee_utils import update_overdue_fees, get_student_fee_summary
from db_utils import get_db_connection
from datetime import date

fee_api_bp = Blueprint('fee_api', __name__, url_prefix='/api/fees')

@fee_api_bp.route('/update_overdue', methods=['POST'])
def update_overdue_fees_api():
    """API endpoint to manually trigger overdue fee updates."""
    try:
        updated_count = update_overdue_fees()
        return jsonify({
            'success': True,
            'message': f'Updated {updated_count} fees to overdue status',
            'updated_count': updated_count
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error updating overdue fees: {str(e)}'
        }), 500

@fee_api_bp.route('/student/<int:student_id>/summary', methods=['GET'])
def get_fee_summary(student_id):
    """API endpoint to get a student's fee summary."""
    try:
        fee_data = get_student_fee_summary(student_id)
        return jsonify({
            'success': True,
            'data': {
                'summary': fee_data['summary'],
                'fee_count': len(fee_data['fees'])
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error retrieving fee summary: {str(e)}'
        }), 500

@fee_api_bp.route('/mark_paid/<int:fee_id>', methods=['POST'])
def mark_fee_paid(fee_id):
    """API endpoint to mark a fee as paid."""
    conn = get_db_connection()
    try:
        # Get current fee data
        fee = conn.execute('SELECT * FROM fees WHERE id = ?', (fee_id,)).fetchone()
        if not fee:
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Fee not found'
            }), 404
            
        # Update fee status
        today = date.today().isoformat()
        conn.execute(
            'UPDATE fees SET status = ?, paid_date = ? WHERE id = ?', 
            ('Paid', today, fee_id)
        )
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Fee marked as paid',
            'data': {
                'fee_id': fee_id,
                'paid_date': today,
                'status': 'Paid'
            }
        })
    except Exception as e:
        conn.rollback()
        return jsonify({
            'success': False,
            'message': f'Error marking fee as paid: {str(e)}'
        }), 500
    finally:
        conn.close()
