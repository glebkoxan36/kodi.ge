document.addEventListener('DOMContentLoaded', function() {
    const sidebarHTML = `
        <div class="sidebar">
            <div class="user-profile-section" onclick="{% if currentUser %}goToDashboard(){% else %}goToLogin(){% endif %}">
                <div class="user-avatar-container">
                    <div class="user-avatar" {% if currentUser %}style="background-color: {{ currentUser.avatar_color }}"{% endif %}>
                        {% if currentUser %}
                            {% if currentUser.is_impersonation %}
                                <i class="fas fa-user-secret"></i>
                            {% elif currentUser.is_admin %}
                                ADMIN
                            {% else %}
                                {{ currentUser.first_name|first }}{{ currentUser.last_name|first }}
                            {% endif %}
                        {% else %}
                            <i class="fas fa-user"></i>
                        {% endif %}
                    </div>
                </div>
                <div class="user-name">
                    {% if currentUser %}
                        {% if currentUser.is_impersonation %}
                            {{ currentUser.first_name }} {{ currentUser.last_name }}
                            <div class="user-admin-username">
                                (Admin: {{ currentUser.admin_username }})
                            </div>
                        {% elif currentUser.is_admin %}
                            ადმინისტრატორი
                            <div class="user-admin-username">({{ currentUser.admin_username }})</div>
                        {% else %}
                            {{ currentUser.first_name }} {{ currentUser.last_name }}
                            <div class="user-balance">ბალანსი: {{ '%.2f' % currentUser.balance }}₾</div>
                        {% endif %}
                    {% else %}
                        ლოგინი/რეგისტრაცია
                    {% endif %}
                </div>
            </div>
            
            <ul class="nav flex-column">
                <li class="nav-item">
                    <a class="nav-link active" href="#">
                        <i class="fas fa-home"></i>
                        <span>მთავარი</span>
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="#" data-bs-toggle="collapse" data-bs-target="#appleSubmenu">
                        <i class="fas fa-mobile-alt"></i>
                        <span>შემოწმება Apple</span>
                        <i class="fas fa-chevron-down float-end"></i>
                    </a>
                    <div class="collapse" id="appleSubmenu">
                        <div class="submenu">
                            <a class="nav-link" href="/applecheck?type=free">
                                <i class="fas fa-check-circle"></i>
                                <span>უფასო შემოწმება</span>
                            </a>
                            <a class="nav-link" href="/applecheck?type=fmi">
                                <i class="fas fa-shopping-cart"></i>
                                <span>პლატანი შემოწმება</span>
                            </a>
                            <a class="nav-link" href="/applecheck?type=premium">
                                <i class="fas fa-crown"></i>
                                <span>პრემიუმ შემოწმება</span>
                            </a>
                        </div>
                    </div>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="/androidcheck">
                        <i class="fab fa-android"></i>
                        <span>შემოწმება Android</span>
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link disabled" href="#">
                        <i class="fas fa-unlock-alt"></i>
                        <span>ტელეფონის განბლოკვა</span>
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="/compare">
                        <i class="fas fa-exchange-alt"></i>
                        <span>ტელეფონების შედარება</span>
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="/knowledge-base">
                        <i class="fas fa-book"></i>
                        <span>ცოდნის ბაზა</span>
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="/contacts">
                        <i class="fas fa-address-card"></i>
                        <span>კონტაქტი</span>
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="#">
                        <i class="fas fa-shield-alt"></i>
                        <span>კონფიდენციალურობის პოლიტიკა</span>
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="#">
                        <i class="fas fa-undo"></i>
                        <span>დაბრუნების პოლიტიკა</span>
                    </a>
                </li>
                {% if currentUser and currentUser.is_admin %}
                <li class="nav-item">
                    <a class="nav-link" href="/admin/dashboard">
                        <i class="fas fa-cog"></i>
                        <span>ადმინ პანელი</span>
                    </a>
                </li>
                {% endif %}
            </ul>
        </div>
    `;

    // Вставляем сайдбар в контейнер
    const sidebarContainer = document.getElementById('sidebar-container');
    if (sidebarContainer) {
        sidebarContainer.innerHTML = sidebarHTML;
    }

    // Инициализация Bootstrap компонентов
    const collapseTriggers = document.querySelectorAll('[data-bs-toggle="collapse"]');
    collapseTriggers.forEach(trigger => {
        trigger.addEventListener('click', function() {
            const target = document.querySelector(this.dataset.bsTarget);
            if (target) {
                new bootstrap.Collapse(target, {
                    toggle: true
                });
            }
        });
    });
});
