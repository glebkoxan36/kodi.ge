{% extends "admin/admin.html" %}

{% block content %}
<!-- ========================================== -->
<!-- Price Management Section -->
<!-- ========================================== -->
<div class="row g-3">
    <div class="col-lg-12">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">Service Price Management</h5>
            </div>
            <div class="card-body">
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                                {{ message }}
                                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                            </div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}
                
                <form method="POST">
                    <!-- CSRF Token -->
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                    
                    <div class="row">
                        <!-- Apple Services -->
                        <div class="col-md-6">
                            <h4 class="mb-3 border-bottom pb-2">Apple Services</h4>
                            {% for service in apple_services %}
                            <div class="form-section mb-3">
                                <label class="form-label fw-bold text-capitalize">{{ service|replace('_', ' ') }}</label>
                                <div class="input-group input-group-price">
                                    <span class="input-group-text">₾</span>
                                    <input type="number" step="0.01" min="0" max="99.99" 
                                           class="form-control" 
                                           name="{{ service }}" 
                                           value="{{ current_prices[service] | default(0) }}" 
                                           required>
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                        
                        <!-- Android Services -->
                        <div class="col-md-6">
                            <h4 class="mb-3 border-bottom pb-2">Android Services</h4>
                            {% for service in android_services %}
                            <div class="form-section mb-3">
                                <label class="form-label fw-bold text-capitalize">{{ service|replace('_', ' ') }}</label>
                                <div class="input-group input-group-price">
                                    <span class="input-group-text">₾</span>
                                    <input type="number" step="0.01" min="0" max="99.99" 
                                           class="form-control" 
                                           name="{{ service }}" 
                                           value="{{ current_prices[service] | default(0) }}" 
                                           required>
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                    
                    <button type="submit" class="btn btn-success w-100 mt-4">
                        <i class="bi bi-save me-1"></i> Update All Prices
                    </button>
                </form>
            </div>
        </div>
    </div>
    
    <div class="col-lg-12">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">Price Change History</h5>
            </div>
            <div class="card-body price-history">
                {% if price_history %}
                    {% for item in price_history %}
                    <div class="history-item mb-3 p-3 border rounded">
                        <div class="d-flex justify-content-between mb-2">
                            <div class="fw-bold">{{ item.changed_at }}</div>
                            <div class="text-muted">Changed by: {{ item.changed_by }}</div>
                        </div>
                        
                        <div class="row">
                            <div class="col-md-6">
                                <h6>Apple Services</h6>
                                <ul class="list-group list-group-flush">
                                    {% for service in apple_services %}
                                    {% if service in item.prices %}
                                    <li class="list-group-item d-flex justify-content-between">
                                        <span>{{ service|replace('_', ' ') }}:</span>
                                        <span>₾{{ "%.2f"|format(item.prices[service]) }}</span>
                                    </li>
                                    {% endif %}
                                    {% endfor %}
                                </ul>
                            </div>
                            
                            <div class="col-md-6">
                                <h6>Android Services</h6>
                                <ul class="list-group list-group-flush">
                                    {% for service in android_services %}
                                    {% if service in item.prices %}
                                    <li class="list-group-item d-flex justify-content-between">
                                        <span>{{ service|replace('_', ' ') }}:</span>
                                        <span>₾{{ "%.2f"|format(item.prices[service]) }}</span>
                                    </li>
                                    {% endif %}
                                    {% endfor %}
                                </ul>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="text-center text-muted py-3">
                        No price history available
                    </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>
{% endblock %}
