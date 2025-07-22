from flask import render_template, request, flash, redirect, url_for, session
from . import admin_bp
from .auth_decorators import admin_required
from .audit_log import log_audit_event
from db import prices_collection
from price import get_current_prices, DEFAULT_PRICES
from datetime import datetime

@admin_bp.route('/price', methods=['GET', 'POST'])
@admin_required
def price_management():
    try:
        if request.method == 'POST':
            try:
                new_prices = {}
                for service in DEFAULT_PRICES.keys():
                    price_value = float(request.form.get(service, 0))
                    new_prices[service] = int(price_value * 100)
                
                current_doc = prices_collection.find_one({'type': 'current'})
                current_prices = current_doc['prices'] if current_doc else {}
                
                prices_collection.insert_one({
                    'type': 'history',
                    'prices': current_prices,
                    'changed_at': datetime.utcnow(),
                    'changed_by': session.get('admin_username', 'unknown')
                })
                
                prices_collection.update_one(
                    {'type': 'current'},
                    {'$set': {
                        'prices': new_prices,
                        'updated_at': datetime.utcnow()
                    }},
                    upsert=True
                )
                
                log_audit_event(
                    action='price_change',
                    details={'new_prices': new_prices},
                    user_id=session.get('admin_id'),
                    username=session.get('admin_username')
                )
                
                flash('Prices updated successfully!', 'success')
                return redirect(url_for('admin.price_management'))
            except Exception as e:
                flash(f'Error updating prices: {str(e)}', 'danger')
        
        current_prices = get_current_prices()
        formatted_prices = {service: price / 100 for service, price in current_prices.items()}
        
        price_history = list(prices_collection.find({'type': 'history'})
            .sort('changed_at', -1)
            .limit(5))
        
        for item in price_history:
            item['changed_at'] = item['changed_at'].strftime('%Y-%m-%d %H:%M')
            item['prices'] = {service: price / 100 for service, price in item['prices'].items()}
        
        apple_services = [
            'fmi', 'blacklist', 'sim_lock', 
            'activation', 'carrier', 'mdm'
        ]
        
        android_services = [
            'samsung_v1', 'samsung_v2', 'samsung_knox',
            'xiaomi', 'google_pixel', 'huawei_v1',
            'huawei_v2', 'motorola', 'oppo', 'frp',
            'sim_lock_android'
        ]
        
        return render_template(
            'admin/admin.html',
            current_prices=formatted_prices,
            price_history=price_history,
            apple_services=apple_services,
            android_services=android_services,
            active_section='price_management'
        )
    except Exception as e:
        current_app.logger.error(f"Price management error: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_dashboard'))
