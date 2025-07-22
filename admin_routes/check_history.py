from flask import render_template, request, flash, redirect, url_for, current_app
from . import admin_bp
from .auth_decorators import admin_required
from db import checks_collection
from price import get_current_prices

@admin_bp.route('/history')
@admin_required
def check_history():
    try:
        page = int(request.args.get('page', 1))
        per_page = 50
        imei_query = request.args.get('imei', '')
        
        query = {}
        if imei_query:
            query['imei'] = {'$regex': f'^{imei_query}'}
        
        total_checks = checks_collection.count_documents(query) if checks_collection else 0
        
        checks = []
        if checks_collection:
            checks = list(
                checks_collection.find(query)
                .sort('timestamp', -1)
                .skip((page - 1) * per_page)
                .limit(per_page)
            )
        
        for check in checks:
            check['timestamp'] = check['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            if check.get('paid'):
                check['amount'] = f"${check.get('amount', 0):.2f}"
            else:
                check['amount'] = 'Free'
            check['_id'] = str(check['_id'])
        
        return render_template(
            'admin/admin.html',
            checks=checks,
            total_checks=total_checks,
            imei_query=imei_query,
            page=page,
            per_page=per_page,
            active_section='check_history'
        )
    except Exception as e:
        current_app.logger.error(f"Check history error: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_dashboard'))
